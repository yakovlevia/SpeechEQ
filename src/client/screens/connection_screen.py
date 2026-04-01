"""
Логика экрана подключения к серверу с поддержкой gRPC
"""
import asyncio
import logging
import traceback
from PySide6.QtCore import QSettings, Signal, QObject
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class ConnectionWorker(QObject):
    """Выполняет асинхронные операции подключения к gRPC-серверу в отдельном потоке."""

    connection_status = Signal(str, bool)
    server_version = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, connection_manager):
        """
        Инициализирует рабочий поток для подключения.

        Args:
            connection_manager: Менеджер gRPC-подключения
        """
        super().__init__()
        self.connection_manager = connection_manager
        self._running = False
        self._check_task = None
        self._loop = None
        logger.info("ConnectionWorker инициализирован")

    def setup_asyncio(self):
        """Настраивает и запускает цикл asyncio в текущем потоке."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logger.info("ConnectionWorker: asyncio инициализирован, loop id: %s", id(self._loop))
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"Ошибка инициализации asyncio: {e}\n{traceback.format_exc()}")
        finally:
            logger.info("ConnectionWorker: цикл asyncio завершен")
            self._cleanup_loop()

    def _cleanup_loop(self):
        """Очищает ресурсы цикла asyncio."""
        if self._loop and self._loop.is_running():
            pending = asyncio.all_tasks(self._loop)
            if pending:
                logger.info(f"ConnectionWorker: отмена {len(pending)} задач")
                for task in pending:
                    task.cancel()
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.stop()
            self._loop.close()
            logger.info("ConnectionWorker: цикл asyncio очищен")

    def stop(self):
        """Останавливает рабочий поток и отменяет все задачи."""
        logger.info("ConnectionWorker: остановка...")
        self._running = False
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def check_remote_connection(self, host: str, port: int):
        """
        Инициирует проверку подключения к удалённому серверу.

        Args:
            host: Адрес сервера
            port: Порт сервера
        """
        logger.info(f"ConnectionWorker.check_remote_connection вызван с {host}:{port}")

        if not self._loop:
            logger.error("ConnectionWorker: asyncio не инициализирован")
            self.error_occurred.emit("Ошибка инициализации asyncio")
            return

        if not self._loop.is_running():
            logger.error("ConnectionWorker: цикл asyncio не запущен")
            self.error_occurred.emit("Цикл asyncio не запущен")
            return

        logger.info(f"ConnectionWorker: отправка задачи в цикл asyncio {id(self._loop)}")

        future = asyncio.run_coroutine_threadsafe(
            self._check_remote_connection_async(host, port),
            self._loop
        )
        future.add_done_callback(self._on_connection_future_done)

    def _on_connection_future_done(self, future):
        """Обрабатывает завершение future подключения."""
        try:
            exc = future.exception()
            if exc:
                logger.error(f"Ошибка в future: {exc}")
                self.error_occurred.emit(str(exc))
        except asyncio.CancelledError:
            logger.info("Задача подключения отменена")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в callback: {e}")

    async def _check_remote_connection_async(self, host: str, port: int):
        """
        Асинхронно проверяет подключение к удалённому серверу.

        Args:
            host: Адрес сервера
            port: Порт сервера
        """
        logger.info(f"Начало асинхронного подключения к {host}:{port}")

        try:
            self.connection_status.emit("Подключение...", False)

            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(
                None,
                self.connection_manager.connect_to_server,
                host, port
            )

            logger.info(f"Результат connect_to_server: {success}")

            if success:
                self.connection_status.emit("Подключено к серверу", True)
                self.server_version.emit("SpeechEQ Server (gRPC) v1.0.0")
                logger.info(f"Успешно подключено к {host}:{port}")
                self._start_connection_check_async(host, port)
            else:
                self.connection_status.emit("Сервер недоступен", False)
                error_msg = f"Не удалось подключиться к {host}:{port}"
                self.error_occurred.emit(error_msg)
                logger.error(error_msg)

        except asyncio.CancelledError:
            logger.info("Подключение отменено")
            raise
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}", exc_info=True)
            self.connection_status.emit("Ошибка подключения", False)
            self.error_occurred.emit(str(e))

    def disconnect_from_server(self):
        """Инициирует отключение от сервера."""
        logger.info("ConnectionWorker.disconnect_from_server вызван")

        if not self._loop:
            logger.error("ConnectionWorker: asyncio не инициализирован")
            return

        if not self._loop.is_running():
            logger.error("ConnectionWorker: цикл asyncio не запущен")
            return

        asyncio.run_coroutine_threadsafe(
            self._disconnect_from_server_async(),
            self._loop
        )

    async def _disconnect_from_server_async(self):
        """Асинхронно отключается от сервера."""
        logger.info("Начало асинхронного отключения от сервера")

        try:
            self.connection_status.emit("Отключение...", False)
            await self.connection_manager.disconnect_from_server()
            self._stop_connection_check()
            self.connection_status.emit("Отключено", False)
            self.server_version.emit("")
            logger.info("Отключено от сервера")
        except Exception as e:
            logger.error(f"Ошибка при отключении: {e}\n{traceback.format_exc()}")
            self.error_occurred.emit(f"Ошибка при отключении: {e}")

    def _start_connection_check_async(self, host: str, port: int):
        """
        Запускает периодическую проверку состояния соединения.

        Args:
            host: Адрес сервера
            port: Порт сервера
        """
        self._stop_connection_check()

        async def check_loop():
            logger.info("Запуск цикла проверки соединения")
            self._running = True
            check_count = 0

            while self._running:
                await asyncio.sleep(5)
                check_count += 1
                logger.debug(f"Проверка соединения #{check_count}")

                if not self.connection_manager.is_connected():
                    logger.warning("Потеряно соединение с сервером")
                    self.connection_status.emit("Потеряно соединение с сервером", False)
                    self.server_version.emit("")
                    break

            logger.info("Цикл проверки соединения завершен")

        self._check_task = asyncio.create_task(check_loop())

    def _stop_connection_check(self):
        """Останавливает периодическую проверку соединения."""
        logger.info("Остановка цикла проверки соединения")
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            self._check_task = None


class ConnectionScreenLogic:
    """Управляет UI экрана подключения и взаимодействием с ConnectionWorker."""

    def __init__(self, ui, parent, worker):
        """
        Инициализирует логику экрана подключения.

        Args:
            ui: Объект UI главного окна
            parent: Родительский объект
            worker: Экземпляр ConnectionWorker
        """
        self.ui = ui
        self.parent = parent
        self.worker = worker

        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.server_version.connect(self.update_server_version)
        self.worker.error_occurred.connect(self.show_error)

        self.ui.modeComboBox.currentIndexChanged.connect(self.on_mode_changed)
        self.ui.startLocalBtn.clicked.connect(self.on_start_local_clicked)
        self.ui.connectBtn.clicked.connect(self.on_connect_clicked)

        self.load_settings()
        self.update_mode_visibility()

        self.is_connected = False
        self.is_local_running = False

        logger.info("ConnectionScreenLogic инициализирован")

    def load_settings(self):
        """Загружает сохранённые настройки подключения из QSettings."""
        try:
            saved_settings = QSettings("SpeechEQ", "Connection")

            mode = saved_settings.value("mode", 0, type=int)
            self.ui.modeComboBox.setCurrentIndex(mode)

            host = saved_settings.value("remote_host", "localhost")
            port = saved_settings.value("remote_port", 50051, type=int)

            self.ui.hostLineEdit.setText(host)
            self.ui.remotePortSpinBox.setValue(port)

            logger.info(f"Загружены настройки: mode={mode}, host={host}, port={port}")
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")

    def save_settings(self):
        """Сохраняет текущие настройки подключения в QSettings."""
        try:
            saved_settings = QSettings("SpeechEQ", "Connection")
            saved_settings.setValue("mode", self.ui.modeComboBox.currentIndex())
            saved_settings.setValue("remote_host", self.ui.hostLineEdit.text())
            saved_settings.setValue("remote_port", self.ui.remotePortSpinBox.value())
            logger.debug("Настройки сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")

    def on_mode_changed(self, index):
        """
        Обрабатывает изменение режима работы (локальный/удалённый).

        Args:
            index: Индекс выбранного режима (0 - локальный, 1 - удалённый)
        """
        logger.info(f"Режим изменен на: {index}")
        self.update_mode_visibility()
        self.save_settings()

        if index == 0 and self.is_connected:
            logger.info("Переключение на локальный режим, отключение от сервера")
            self.worker.disconnect_from_server()

    def update_mode_visibility(self):
        """Обновляет видимость виджетов в зависимости от выбранного режима."""
        is_local = (self.ui.modeComboBox.currentIndex() == 0)
        self.ui.localModeWidget.setVisible(is_local)
        self.ui.remoteModeWidget.setVisible(not is_local)

    def update_connection_status(self, status: str, connected: bool):
        """
        Обновляет отображение статуса подключения.

        Args:
            status: Текстовое описание статуса
            connected: Флаг подключения
        """
        logger.info(f"Обновление статуса: '{status}', connected={connected}")

        is_local = (self.ui.modeComboBox.currentIndex() == 0)

        if is_local:
            self.ui.localStatusLabel.setText(f"Статус: {status}")
            self.is_local_running = connected

            if connected:
                self.ui.startLocalBtn.setText("Остановить сервер")
            else:
                self.ui.startLocalBtn.setText("Запустить локальный сервер")
        else:
            self.ui.remoteStatusLabel.setText(f"Статус: {status}")
            self.is_connected = connected

            if connected:
                self.ui.connectBtn.setText("Отключиться")
                self.ui.hostLineEdit.setEnabled(False)
                self.ui.remotePortSpinBox.setEnabled(False)
            else:
                self.ui.connectBtn.setText("Подключиться")
                self.ui.hostLineEdit.setEnabled(True)
                self.ui.remotePortSpinBox.setEnabled(True)

    def update_server_version(self, version: str):
        """
        Обновляет отображение версии сервера.

        Args:
            version: Строка с версией сервера
        """
        self.ui.serverVersionLabel.setText(version)
        logger.info(f"Версия сервера: {version}")

    def show_error(self, error_msg: str):
        """
        Отображает сообщение об ошибке.

        Args:
            error_msg: Текст ошибки
        """
        logger.error(f"Ошибка подключения: {error_msg}")
        self.ui.errorLabel.setText(f"Ошибка: {error_msg}")
        QMessageBox.warning(self.ui.centralwidget, "Ошибка подключения", error_msg)

    def on_start_local_clicked(self):
        """Обрабатывает нажатие кнопки запуска/остановки локального сервера."""
        logger.info("Нажата кнопка локального сервера")

        if self.is_local_running:
            self.update_connection_status("Сервер остановлен", False)
            self.ui.serverVersionLabel.setText("")
        else:
            self.update_connection_status("Локальный сервер запущен", True)
            self.update_server_version("SpeechEQ Server (локальный) v1.0.0")

    def on_connect_clicked(self):
        """Обрабатывает нажатие кнопки подключения/отключения."""
        logger.info("Нажата кнопка подключения")

        if self.is_connected:
            logger.info("Отключение от сервера")
            self.worker.disconnect_from_server()
        else:
            host = self.ui.hostLineEdit.text()
            port = self.ui.remotePortSpinBox.value()
            logger.info(f"Попытка подключения к {host}:{port}")
            self.worker.check_remote_connection(host, port)

        self.save_settings()