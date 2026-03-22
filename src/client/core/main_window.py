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

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Основной класс главного окна"""

    def __init__(self, audio_handler, processing_manager, default_settings):
        super().__init__()
        self.audio_handler = audio_handler
        self.processing_manager = processing_manager
        self.default_settings = default_settings
        self.processing_worker = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("SpeechEQ v1.0")
        
        # Минимальный размер окна
        self.min_width = 1600
        self.min_height = 1200
        self.setMinimumSize(QSize(self.min_width, self.min_height))
        self.resize(QSize(1600, 1200))
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
        self.restore_paused_tasks()
        self.setup_table_columns()
        self.setup_title_alignment()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        logger.info("Главное окно инициализировано")

    def init_screen_logic(self):
        """Инициализация логики экранов"""
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
        """Настройка навигации по кнопкам"""
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
        """Подключение сигналов между экранами и менеджером"""
        self.processing_screen.tasks_added.connect(self.on_tasks_added)
        self.processing_screen.processing_started.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.progressScreen)
        )
        self.progress_screen.cancel_selected_requested.connect(self.on_cancel_selected)
        self.progress_screen.pause_selected_requested.connect(self.on_pause_selected)
        self.progress_screen.resume_selected_requested.connect(self.on_resume_selected)

    def set_processing_worker(self, worker):
        """Установка рабочего потока обработки"""
        self.processing_worker = worker
        self.processing_worker.progress_updated.connect(self.on_progress_updated)
        self.processing_worker.task_finished.connect(self.on_task_finished)
        self.processing_worker.task_started.connect(self.on_task_started)
        self.processing_screen.set_processing_worker(worker)
        logger.info("Рабочий поток подключен к главному окну")

    def setup_table_columns(self):
        """Настройка растяжения колонок таблицы на экране прогресса"""
        header = self.ui.taskTable.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        header.setMinimumSectionSize(80)
        self.ui.taskTable.setAlternatingRowColors(True)
        header.setSectionsMovable(False)
        self.ui.taskTable.horizontalHeader().setStretchLastSection(False)
    
    def setup_title_alignment(self):
        """Настройка выравнивания заголовка на экране прогресса"""
        self.ui.titleLeftSpacer.changeSize(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.ui.titleRightSpacer.changeSize(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

    def restore_paused_tasks(self):
        """Восстановление состояния приостановленных задач"""
        settings = QSettings("SpeechEQ", "Session")
        paused_tasks = settings.value("paused_tasks", [])

        if paused_tasks:
            logger.info(f"Восстановление {len(paused_tasks)} приостановленных задач")
            for task_path in paused_tasks:
                self.processing_manager.pause_task(task_path)
                self.progress_screen.paused_tasks.add(task_path)

    def on_progress_updated(self, path: str, current: int, total: int):
        """
        Обновление прогресса из рабочего потока.
        """
        if hasattr(self, 'progress_screen'):
            self.progress_screen.update_task_status(
                path, "обработка", total, current
            )

    def on_task_finished(self, path: str, success: bool, message: str):
        """
        Обработка завершения задачи из рабочего потока.
        """
        if hasattr(self, 'progress_screen'):
            status = "готово" if success else "ошибка"
            self.progress_screen.update_task_status(path, status)
            
            if not success and message != "Отменено пользователем":
                self.progress_screen.show_error(f"Ошибка: {message}")

    def on_task_started(self, path: str):
        """
        Обработка начала задачи из рабочего потока.
        """
        if hasattr(self, 'progress_screen'):
            self.progress_screen.update_task_status(path, "обработка")

    def on_tasks_added(self, tasks):
        """Обработка добавления задач"""
        logger.info(f"Добавлено {len(tasks)} задач в очередь")

        for task in tasks:
            self.processing_manager.add_video_task(task)
            logger.debug(f"Добавлена задача: {task.input_path}")
        
        self.progress_screen.add_tasks(tasks)

    def on_pause_selected(self, task_paths):
        """Приостановка выбранных задач"""
        logger.info(f"Приостановка {len(task_paths)} задач")

        async def pause_tasks():
            for path in task_paths:
                success = self.processing_manager.pause_task(path)
                if success:
                    logger.info(f"Задача приостановлена: {path}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(pause_tasks())
        finally:
            loop.close()
    
    def on_resume_selected(self, task_paths):
        """Возобновление выбранных задач"""
        logger.info(f"Возобновление {len(task_paths)} задач")
        
        async def resume_tasks():
            for path in task_paths:
                task_data = self.progress_screen.tasks.get(path)
                if task_data and task_data['status'] == 'отменено':
                    logger.warning(f"Попытка возобновить отменённую задачу: {path}")
                    continue
                    
                success = self.processing_manager.resume_task(path)
                if success:
                    logger.info(f"Задача возобновлена: {path}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(resume_tasks())
        finally:
            loop.close()
    
    def on_cancel_selected(self, task_paths):
        """Отмена выбранных задач"""
        logger.info(f"Отмена {len(task_paths)} задач")
        
        async def cancel():
            for path in task_paths:
                self.processing_manager.cancel_task(path)
                await self.processing_manager.video_processor.cancel_processing_by_path(path)
                self.progress_screen.update_task_status(path, "отменено")
                logger.info(f"Задача отменена: {path}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cancel())
        finally:
            loop.close()

    def resizeEvent(self, event):
        """Обработка изменения размера окна - запрещаем уменьшение меньше минимального"""
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

        if hasattr(self, 'ui') and hasattr(self.ui, 'taskTable'):
            self.update_table_columns_size()
    
    def update_table_columns_size(self):
        """Обновление размеров колонок при изменении размера окна"""
        if self.width() < self.min_width:
            return
        
        total_width = self.ui.taskTable.width()

        file_width = max(500, int(total_width * 0.60))
        duration_width = max(120, int(total_width * 0.15))
        format_width = max(100, int(total_width * 0.10))
        status_width = max(140, int(total_width * 0.15))

        self.ui.taskTable.setColumnWidth(0, file_width)
        self.ui.taskTable.setColumnWidth(1, duration_width)
        self.ui.taskTable.setColumnWidth(2, format_width)
        self.ui.taskTable.setColumnWidth(3, status_width)

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        logger.info("Закрытие главного окна")

        paused_tasks = self.processing_manager.get_paused_tasks()
        if paused_tasks:
            settings = QSettings("SpeechEQ", "Session")
            settings.setValue("paused_tasks", paused_tasks)
            logger.info(f"Сохранено {len(paused_tasks)} приостановленных задач")

        stats = self.processing_manager.get_queue_stats()
        if stats["active_tasks"] > 0 or stats["queue_size"] > 0:
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Активных задач: {stats['active_tasks']}\n"
                f"Задач в очереди: {stats['queue_size']}\n"
                f"Приостановлено: {stats['paused_tasks']}\n\n"
                "Завершить работу приложения? Все активные задачи будут остановлены.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

        if hasattr(self, 'connection_manager') and not self.connection_manager.is_local():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.connection_manager.disconnect_from_server())
            except Exception as e:
                logger.error(f"Ошибка при отключении от сервера: {e}")
            finally:
                loop.close()

        if hasattr(self, 'processing_worker'):
            logger.info("Остановка рабочего потока обработки...")
            self.processing_worker.stop()

        if hasattr(self, 'connection_worker'):
            logger.info("Остановка потока подключения...")
            self.connection_worker.stop()
        
        if hasattr(self, 'connection_thread') and self.connection_thread.isRunning():
            logger.info("Ожидание завершения потока подключения...")
            self.connection_thread.quit()
            if not self.connection_thread.wait(3000):
                logger.warning("Поток подключения не завершился, принудительное завершение")
                self.connection_thread.terminate()
                self.connection_thread.wait()
        
        logger.info("Завершение работы приложения")
        event.accept()