"""
Главное окно приложения
"""
import asyncio
import logging
from PySide6.QtCore import QSettings, QThread, QSize
from PySide6.QtWidgets import QMainWindow, QMessageBox, QHeaderView, QSizePolicy

from client.ui.ui_mainwindow import Ui_MainWindow
from client.screens.main_screen import MainScreenLogic
from client.screens.connection_screen import ConnectionScreenLogic, ConnectionWorker
from client.screens.processing_screen import ProcessingScreenLogic
from client.screens.progress_screen import ProgressScreenLogic
from client.grpc_client import GRPCConnectionManager
from client.video_queue import TaskStatus

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения, управляющее навигацией между экранами и обработкой задач."""

    def __init__(self, audio_handler, processing_manager, default_settings):
        """
        Инициализация главного окна.

        :param audio_handler: Обработчик аудио для локальной обработки
        :param processing_manager: Менеджер очереди задач обработки
        :param default_settings: Настройки по умолчанию для обработки
        """
        super().__init__()
        self.audio_handler = audio_handler
        self.processing_manager = processing_manager
        self.default_settings = default_settings
        self.processing_worker = None
        self.processing_thread = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("SpeechEQ v1.0")

        self.min_width = 1600
        self.min_height = 900
        self.setMinimumSize(QSize(self.min_width, self.min_height))
        self.resize(QSize(1600, 900))
        self.setMaximumSize(QSize(16777215, 16777215))

        self.connection_manager = GRPCConnectionManager()
        self.connection_manager.set_local_handler(audio_handler)

        self.connection_thread = QThread()
        self.connection_worker = ConnectionWorker(self.connection_manager)
        self.connection_worker.moveToThread(self.connection_thread)

        self.connection_thread.started.connect(self.connection_worker.setup_asyncio)
        self.connection_thread.finished.connect(self.connection_worker.deleteLater)
        self.connection_thread.start()

        self.init_screen_logic()
        self.setup_navigation()
        self.connect_signals()
        self.setup_table_columns()
        self.setup_title_alignment()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        logger.info("Главное окно инициализировано")

    def set_processing_worker(self, worker, thread):
        """
        Установка рабочего потока обработки задач.

        Подключает сигналы воркера к слотам экрана прогресса.

        :param worker: Экземпляр ProcessingWorker для обработки задач
        :param thread: QThread, в котором выполняется воркер
        """
        self.processing_worker = worker
        self.processing_thread = thread

        self.processing_worker.task_added.connect(self.progress_screen.add_task)
        self.processing_worker.task_status_changed.connect(self.progress_screen.update_task_status)
        self.processing_worker.task_progress.connect(self.progress_screen.update_task_progress)
        self.processing_worker.task_duration.connect(self.progress_screen.update_task_duration)
        self.processing_worker.task_finished.connect(self.on_task_finished)
        self.processing_worker.task_started.connect(self.on_task_started)
        self.processing_worker.progress_updated.connect(self.on_progress_updated)
        self.processing_worker.queue_stats_updated.connect(self.on_queue_stats_updated)

        if hasattr(self, 'processing_screen'):
            self.processing_screen.set_processing_worker(worker)

        logger.info("MainWindow: установлен рабочий поток")

    def init_screen_logic(self):
        """Инициализация логики всех экранов приложения."""
        self.main_screen = MainScreenLogic(self.ui, self)
        self.connection_screen = ConnectionScreenLogic(
            self.ui,
            self,
            self.connection_worker
        )
        self.processing_screen = ProcessingScreenLogic(
            self.ui,
            self,
            audio_handler=self.audio_handler,
            default_settings=self.default_settings,
            connection_manager=self.connection_manager
        )
        self.progress_screen = ProgressScreenLogic(
            self.ui,
            self,
            processing_manager=self.processing_manager
        )

    def setup_navigation(self):
        """Настройка навигации между экранами через кнопки бокового меню."""
        self.ui.mainScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.mainScreen)
        )
        self.ui.connectionScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.connectionScreen)
        )
        self.ui.processingScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.processingScreen)
        )
        self.ui.progressScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.progressScreen)
        )

    def connect_signals(self):
        """Подключение сигналов между компонентами приложения."""
        self.processing_screen.tasks_added.connect(self.on_tasks_added)
        self.processing_screen.processing_started.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.progressScreen)
        )
        self.progress_screen.pause_selected_requested.connect(self.on_pause_selected)
        self.progress_screen.resume_selected_requested.connect(self.on_resume_selected)
        self.progress_screen.cancel_selected_requested.connect(self.on_cancel_selected)
        self.progress_screen.clear_finished_requested.connect(self.on_clear_finished)

    def setup_table_columns(self):
        """Настройка заголовков и режимов растягивания колонок таблицы задач."""
        header = self.ui.taskTable.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

    def setup_title_alignment(self):
        """Настройка выравнивания заголовка окна через спейсеры."""
        self.ui.titleLeftSpacer.changeSize(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.ui.titleRightSpacer.changeSize(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

    def on_tasks_added(self, tasks):
        """
        Обработчик добавления новых задач в очередь.

        :param tasks: Список добавленных задач
        """
        logger.info(f"Добавлено {len(tasks)} задач в очередь")
        if hasattr(self, 'processing_worker'):
            self.processing_worker.add_tasks(tasks)

    def on_task_started(self, task_id: str):
        """
        Обработчик начала выполнения задачи.

        :param task_id: Идентификатор начатой задачи
        """
        logger.info(f"Задача {task_id} начата")

    def on_progress_updated(self, task_id: str, current: int, total: int):
        """
        Обработчик обновления прогресса задачи.

        :param task_id: Идентификатор задачи
        :param current: Текущее значение прогресса
        :param total: Общее значение для завершения
        """
        pass

    def on_task_finished(self, task_id: str, success: bool, message: str):
        """
        Обработчик завершения задачи.

        :param task_id: Идентификатор завершённой задачи
        :param success: Флаг успешного завершения
        :param message: Сообщение о результате выполнения
        """
        logger.info(f"Задача {task_id} завершена: success={success}, message={message}")

        if not success and message != "Отменено пользователем":
            self.progress_screen.show_error(f"Ошибка: {message}")

    def on_queue_stats_updated(self, stats: dict):
        """
        Обработчик обновления статистики очереди задач.

        :param stats: Словарь со статистикой очереди
        """
        pass

    def on_pause_selected(self, task_ids: list):
        """
        Обработчик приостановки выбранных задач.

        :param task_ids: Список идентификаторов задач для приостановки
        """
        logger.info(f"Приостановка {len(task_ids)} задач")

        if hasattr(self, 'processing_worker'):
            for task_id in task_ids:
                self.processing_worker.pause_task(task_id)

    def on_resume_selected(self, task_ids: list):
        """
        Обработчик возобновления выбранных задач.

        :param task_ids: Список идентификаторов задач для возобновления
        """
        logger.info(f"Возобновление {len(task_ids)} задач")

        if hasattr(self, 'processing_worker'):
            for task_id in task_ids:
                self.processing_worker.resume_task(task_id)

    def on_cancel_selected(self, task_ids: list):
        """
        Обработчик отмены выбранных задач.

        :param task_ids: Список идентификаторов задач для отмены
        """
        logger.info(f"Отмена {len(task_ids)} задач")

        if hasattr(self, 'processing_worker'):
            self.processing_worker.cancel_tasks(task_ids)

    def on_clear_finished(self):
        """Обработчик очистки завершённых задач из очереди и менеджера."""
        logger.info("Очистка завершённых задач")

        async def clear_tasks():
            return await self.processing_manager.clear_finished_tasks()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            removed_count = loop.run_until_complete(clear_tasks())
            loop.close()
            logger.info(f"Из менеджера удалено {removed_count} задач")
        except Exception as e:
            logger.error(f"Ошибка при очистке задач из менеджера: {e}")

        ProcessingScreenLogic.clear_used_output_paths()

    def resizeEvent(self, event):
        """
        Переопределение события изменения размера окна.

        Обеспечивает минимальные размеры окна приложения.

        :param event: Событие изменения размера
        """
        new_width = event.size().width()
        new_height = event.size().height()

        if new_width < self.min_width or new_height < self.min_height:
            correct_width = max(new_width, self.min_width)
            correct_height = max(new_height, self.min_height)

            if correct_width != new_width or correct_height != new_height:
                self.blockSignals(True)
                self.resize(correct_width, correct_height)
                self.blockSignals(False)
                return

        super().resizeEvent(event)

    def closeEvent(self, event):
        """
        Переопределение события закрытия окна.

        Сохраняет состояние приостановленных задач, корректно завершает
        подключения и потоки перед закрытием приложения.

        :param event: Событие закрытия окна
        """
        logger.info("Закрытие главного окна")

        async def save_paused_tasks():
            tasks = await self.processing_manager.get_all_tasks()
            paused_task_ids = [t.task_id for t in tasks if t.get_status_sync() == TaskStatus.PAUSED]
            if paused_task_ids:
                settings = QSettings("SpeechEQ", "Session")
                settings.setValue("paused_tasks", paused_task_ids)
                logger.info(f"Сохранено {len(paused_task_ids)} приостановленных задач")

        async def get_stats():
            return await self.processing_manager.get_queue_stats()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(save_paused_tasks())
            loop.close()
        except Exception as e:
            logger.error(f"Ошибка при сохранении приостановленных задач: {e}")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            stats = loop.run_until_complete(get_stats())
            loop.close()
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            stats = {}

        if stats.get("active_tasks", 0) > 0 or stats.get("queue_size", 0) > 0:
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Активных задач: {stats.get('active_tasks', 0)}\n"
                f"Задач в очереди: {stats.get('queue_size', 0)}\n"
                f"Приостановлено: {stats.get('paused_tasks', 0)}\n\n"
                "Завершить работу приложения? Все активные задачи будут остановлены.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

        if hasattr(self, 'connection_manager') and not self.connection_manager.is_local():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.connection_manager.disconnect_from_server())
                loop.close()
            except Exception as e:
                logger.error(f"Ошибка при отключении от сервера: {e}")

        if hasattr(self, 'connection_worker'):
            logger.info("Остановка потока подключения...")
            self.connection_worker.stop()

        if hasattr(self, 'connection_thread') and self.connection_thread.isRunning():
            self.connection_thread.quit()
            if not self.connection_thread.wait(3000):
                logger.warning("Поток подключения не завершился, принудительное завершение")
                self.connection_thread.terminate()
                self.connection_thread.wait()

        logger.info("Завершение работы приложения")
        event.accept()