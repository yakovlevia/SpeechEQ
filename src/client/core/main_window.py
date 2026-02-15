"""
Главное окно приложения
"""
import asyncio
import logging
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMainWindow, QMessageBox

from client.ui.ui_mainwindow import Ui_MainWindow

from client.screens.main_screen import MainScreenLogic
from client.screens.connection_screen import ConnectionScreenLogic, ConnectionWorker
from client.screens.processing_screen import ProcessingScreenLogic
from client.screens.progress_screen import ProgressScreenLogic


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
        self.connection_worker = ConnectionWorker()
        self.connection_worker.moveToThread(self.thread())
        self.init_screen_logic()
        self.setup_navigation()
        self.connect_signals()
        self.restore_paused_tasks()
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
            default_settings=self.default_settings
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
            
            # Показываем уведомление об ошибке
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

    def closeEvent(self, event):
        """Обработка закрытия окна"""
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

        if hasattr(self, 'processing_worker'):
            self.processing_worker.stop()
        
        logger.info("Завершение работы приложения")
        event.accept()