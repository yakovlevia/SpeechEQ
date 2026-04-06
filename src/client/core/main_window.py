"""
Главное окно приложения SpeechEQ.

Управляет навигацией между экранами, подключением к серверу
и координацией обработки видео-задач.
"""
import asyncio
import logging
from typing import Optional, Any, Dict, List

from PySide6.QtCore import QThread, QSize, Signal, QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox, QHeaderView, QSizePolicy
from PySide6.QtGui import QCloseEvent, QResizeEvent

from client.ui.ui_mainwindow import Ui_MainWindow
from client.screens.main_screen import MainScreenLogic
from client.screens.connection_screen import ConnectionScreenLogic, ConnectionWorker
from client.screens.processing_screen import ProcessingScreenLogic
from client.screens.progress_screen import ProgressScreenLogic
from client.grpc_client import GRPCConnectionManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения SpeechEQ.

    Координирует работу всех экранов, управляет потоками обработки
    и обеспечивает обработку событий соединения/отключения от сервера.
    """

    connection_lost = Signal()

    def __init__(
        self,
        audio_handler: Any,
        processing_manager: Any,
        default_settings: Any
    ) -> None:
        """Инициализация главного окна.

        Args:
            audio_handler: Обработчик аудио для локального режима.
            processing_manager: Менеджер очереди задач.
            default_settings: Настройки обработки по умолчанию.
        """
        super().__init__()
        self.audio_handler = audio_handler
        self.processing_manager = processing_manager
        self.default_settings = default_settings
        
        self.processing_worker: Optional[Any] = None
        self.processing_thread: Optional[QThread] = None
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.stackedWidget.setCurrentWidget(self.ui.mainScreen)
        self.setWindowTitle("SpeechEQ v1.0")
        
        self._connection_lost_handled: bool = False
        self.min_width: int = 1600
        self.min_height: int = 900
        self.setMinimumSize(QSize(self.min_width, self.min_height))
        self.resize(QSize(1600, 900))

        # Инициализация менеджера соединения
        self.connection_manager = GRPCConnectionManager()
        self.connection_manager.set_local_handler(audio_handler)
        self.connection_manager.set_connection_lost_callback(self._on_connection_lost)
        self.connection_lost.connect(self._handle_connection_lost)

        # Настройка потока для асинхронных операций соединения
        self.connection_thread = QThread()
        self.connection_worker = ConnectionWorker(self.connection_manager)
        self.connection_worker.moveToThread(self.connection_thread)
        self.connection_thread.started.connect(self.connection_worker.setup_asyncio)
        self.connection_thread.finished.connect(self.connection_worker.deleteLater)
        self.connection_thread.start()

        self._init_screens()
        self._setup_navigation()
        self._connect_signals()
        self._setup_table()
        self._setup_layout()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _on_connection_lost(self) -> None:
        """Обработчик сигнала потери соединения с сервером."""
        logger.warning("Соединение с сервером потеряно")
        self.connection_lost.emit()

    def _handle_connection_lost(self) -> None:
        """Обрабатывает потерю соединения: помечает удалённые задачи как ошибочные."""
        if self._connection_lost_handled:
            return
        self._connection_lost_handled = True

        try:
            if self.processing_worker and getattr(self.processing_worker, "_loop", None):
                future = asyncio.run_coroutine_threadsafe(
                    self._fail_remote_tasks_async(),
                    self.processing_worker._loop
                )
                future.result(timeout=5.0)
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self.processing_manager.fail_remote_tasks("Потеря соединения с сервером")
                    )
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"Ошибка при обработке потери соединения: {e}")

        if hasattr(self, "progress_screen"):
            self.progress_screen.update_progress_display()
            self.progress_screen.show_error("Соединение потеряно. Удалённые задачи остановлены.")

        QTimer.singleShot(3000, self._reset_connection_lost_flag)

    async def _fail_remote_tasks_async(self) -> None:
        """Асинхронно помечает удалённые задачи как ошибочные."""
        await self.processing_manager.fail_remote_tasks("Потеря соединения с сервером")

    def _reset_connection_lost_flag(self) -> None:
        """Сбрасывает флаг обработки потери соединения."""
        self._connection_lost_handled = False

    def set_processing_worker(self, worker: Any, thread: QThread) -> None:
        """Подключает сигналы рабочего потока обработки к интерфейсу.

        Args:
            worker: Экземпляр ProcessingWorker.
            thread: Поток, в котором выполняется worker.
        """
        self.processing_worker = worker
        self.processing_thread = thread

        if hasattr(self, "progress_screen"):
            worker.task_added.connect(self.progress_screen.add_task)
            worker.task_status_changed.connect(self.progress_screen.update_task_status)
            worker.task_progress.connect(self.progress_screen.update_task_progress)
            worker.task_duration.connect(self.progress_screen.update_task_duration)
            worker.task_finished.connect(self.on_task_finished)
            worker.task_started.connect(self.on_task_started)
            worker.progress_updated.connect(self.on_progress_updated)
            worker.queue_stats_updated.connect(self.on_queue_stats_updated)

        if hasattr(self, "processing_screen"):
            self.processing_screen.set_processing_worker(worker)

        if hasattr(self, "connection_screen"):
            self.connection_screen.cancel_all_tasks_requested.connect(self.on_cancel_all_tasks)

        logger.info("Рабочий поток обработки подключён")

    def restart_processing(self) -> None:
        """Запрашивает перезапуск обработки очереди задач."""
        if self.processing_worker:
            self.processing_worker.restart_processing()
            logger.info("Запрошен перезапуск обработки")

    def on_cancel_all_tasks(self) -> None:
        """Обрабатывает запрос на отмену всех задач."""
        logger.info("Запрошена отмена всех задач")
        if self.processing_worker:
            self.processing_worker.cancel_all_tasks()

    def _init_screens(self) -> None:
        """Инициализирует логику всех экранов приложения."""
        self.main_screen = MainScreenLogic(self.ui, self)
        self.connection_screen = ConnectionScreenLogic(
            self.ui, self, self.connection_worker
        )
        self.connection_screen.set_processing_manager(self.processing_manager)
        self.connection_screen.set_connection_manager(self.connection_manager)

        self.processing_screen = ProcessingScreenLogic(
            self.ui,
            self,
            audio_handler=self.audio_handler,
            default_settings=self.default_settings,
            connection_manager=self.connection_manager,
        )
        self.progress_screen = ProgressScreenLogic(
            self.ui, self, processing_manager=self.processing_manager
        )

    def _setup_navigation(self) -> None:
        """Настраивает переключение между экранами."""
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

    def _connect_signals(self) -> None:
        """Подключает сигналы между экранами и обработчиками."""
        self.processing_screen.tasks_added.connect(self.on_tasks_added)
        self.processing_screen.processing_started.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.progressScreen)
        )
        self.progress_screen.pause_selected_requested.connect(self.on_pause_selected)
        self.progress_screen.resume_selected_requested.connect(self.on_resume_selected)
        self.progress_screen.cancel_selected_requested.connect(self.on_cancel_selected)
        self.progress_screen.clear_finished_requested.connect(self.on_clear_finished)

    def _setup_table(self) -> None:
        """Настраивает таблицу задач: растягивание колонок."""
        header = self.ui.taskTable.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

    def _setup_layout(self) -> None:
        """Настраивает отступы заголовков экранов."""
        self.ui.titleLeftSpacer.changeSize(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.ui.titleRightSpacer.changeSize(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

    def on_tasks_added(self, tasks: List[Any]) -> None:
        """Добавляет задачи в очередь обработки.

        Args:
            tasks: Список задач AudioCleanupTask.
        """
        if self.processing_worker:
            self.processing_worker.add_tasks(tasks)
        self.restart_processing()

    def on_task_started(self, task_id: str) -> None:
        """Обработчик начала выполнения задачи.

        Args:
            task_id: Идентификатор задачи.
        """
        logger.debug(f"Задача {task_id[:12]}... начата")

    def on_progress_updated(self, task_id: str, current: int, total: int) -> None:
        """Обработчик обновления прогресса задачи.

        Args:
            task_id: Идентификатор задачи.
            current: Обработано сегментов.
            total: Всего сегментов.
        """
        pass  # Прогресс обновляется напрямую в progress_screen

    def on_queue_stats_updated(self, stats: Dict[str, Any]) -> None:
        """Обработчик обновления статистики очереди.

        Args:
            stats: Словарь со статистикой.
        """
        pass  # Статистика обновляется напрямую в progress_screen

    def on_task_finished(self, task_id: str, success: bool, message: str) -> None:
        """Обработчик завершения задачи.

        Показывает ошибку только для непредвиденных сбоев.

        Args:
            task_id: Идентификатор задачи.
            success: Флаг успешного завершения.
            message: Сообщение о результате.
        """
        if not success and message not in (
            "Отменено пользователем",
            "Отменено при отключении от сервера",
        ):
            if hasattr(self, "progress_screen"):
                self.progress_screen.show_error(f"Ошибка: {message}")

    def on_pause_selected(self, task_ids: List[str]) -> None:
        """Приостанавливает выбранные задачи.

        Args:
            task_ids: Список идентификаторов задач.
        """
        if self.processing_worker:
            for tid in task_ids:
                self.processing_worker.pause_task(tid)

    def on_resume_selected(self, task_ids: List[str]) -> None:
        """Возобновляет выбранные задачи.

        Args:
            task_ids: Список идентификаторов задач.
        """
        if self.processing_worker:
            for tid in task_ids:
                self.processing_worker.resume_task(tid)

    def on_cancel_selected(self, task_ids: List[str]) -> None:
        """Отменяет выбранные задачи.

        Args:
            task_ids: Список идентификаторов задач.
        """
        if self.processing_worker:
            self.processing_worker.cancel_tasks(task_ids)

    def on_clear_finished(self) -> None:
        """Очищает завершённые задачи и освобождает пути вывода."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.processing_manager.clear_finished_tasks())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка очистки задач: {e}")

        ProcessingScreenLogic.clear_used_output_paths()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Обрабатывает изменение размера окна, соблюдая минимальные габариты.

        Args:
            event: Событие изменения размера.
        """
        if event.size().width() < self.min_width or event.size().height() < self.min_height:
            self.blockSignals(True)
            try:
                self.resize(
                    max(event.size().width(), self.min_width),
                    max(event.size().height(), self.min_height),
                )
            finally:
                self.blockSignals(False)
            return
        super().resizeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Обрабатывает закрытие окна с подтверждением при активных задачах.

        Args:
            event: Событие закрытия.
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                stats = loop.run_until_complete(self.processing_manager.get_queue_stats())
            finally:
                loop.close()

            active_tasks = stats.get("active_tasks", 0) + stats.get("queue_size", 0)
            if active_tasks > 0:
                reply = QMessageBox.question(
                    self,
                    "Подтверждение закрытия",
                    f"Активных задач: {active_tasks}.\nВсе задачи будут остановлены.\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    event.ignore()
                    return
        except Exception as e:
            logger.error(f"Ошибка при проверке задач: {e}")

        logger.info("Закрытие приложения...")
        self.connection_manager.set_shutting_down(True)

        # Остановка рабочих компонентов
        if self.processing_worker:
            self.processing_worker.stop()
        if self.connection_worker:
            self.connection_worker.stop()

        # Корректное завершение потоков
        self._stop_thread(self.connection_thread, timeout=3000)
        self._stop_thread(self.processing_thread, timeout=5000)

        logger.info("Приложение закрыто")
        event.accept()

    def _stop_thread(self, thread: Optional[QThread], timeout: int) -> None:
        """Безопасно останавливает поток с таймаутом.

        Args:
            thread: Поток для остановки.
            timeout: Максимальное время ожидания в миллисекундах.
        """
        if thread and thread.isRunning():
            thread.quit()
            if not thread.wait(timeout):
                thread.terminate()
            thread.wait()