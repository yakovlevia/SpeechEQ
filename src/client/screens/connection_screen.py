"""
Логика экрана подключения к серверу с поддержкой gRPC.
"""

import asyncio
import logging
from typing import Optional, Any, Tuple
from PySide6.QtCore import QSettings, Signal, QObject, QCoreApplication, QTimer
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class ConnectionWorker(QObject):
    """Рабочий класс для управления подключением к серверу в отдельном потоке."""

    connection_status = Signal(str, bool)
    server_version = Signal(str)
    error_occurred = Signal(str)
    connection_lost = Signal()
    user_disconnected = Signal()
    mode_changed = Signal(bool)
    connection_started = Signal()
    connection_finished = Signal()
    disconnect_started = Signal()
    disconnect_finished = Signal()

    def __init__(self, connection_manager: Any) -> None:
        """
        Инициализирует рабочий поток подключения.

        Args:
            connection_manager: Менеджер gRPC соединений.

        Raises:
            Exception: При ошибках инициализации.
        """
        super().__init__()
        self.connection_manager = connection_manager
        self._running: bool = False
        self._check_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_connecting: bool = False
        self._is_disconnecting: bool = False
        self._is_user_disconnect: bool = False

    def setup_asyncio(self) -> None:
        """Настраивает и запускает цикл asyncio в текущем потоке."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"Ошибка инициализации asyncio: {e}")
        finally:
            self._cleanup_loop()

    def _cleanup_loop(self) -> None:
        """Очищает ресурсы цикла asyncio."""
        if self._loop and self._loop.is_running():
            pending = asyncio.all_tasks(self._loop)
            if pending:
                for task in pending:
                    task.cancel()
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self._loop.stop()
            self._loop.close()

    def stop(self) -> None:
        """Останавливает рабочий поток."""
        self._running = False
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def check_remote_connection(self, host: str, port: int) -> None:
        """
        Проверяет подключение к удалённому серверу.

        Args:
            host: Адрес сервера.
            port: Порт сервера.

        Raises:
            RuntimeError: Если asyncio цикл не инициализирован.
        """
        if self._is_connecting:
            return
        if not self._loop or not self._loop.is_running():
            self._emit_error_safe("Ошибка инициализации asyncio")
            return
        asyncio.run_coroutine_threadsafe(
            self._check_remote_connection_async(host, port), self._loop
        )

    def _emit_error_safe(self, error_msg: str) -> None:
        """
        Безопасно отправляет сигнал об ошибке.

        Args:
            error_msg: Текст сообщения об ошибке.
        """
        try:
            self.error_occurred.emit(error_msg)
        except Exception:
            pass

    async def _check_remote_connection_async(self, host: str, port: int) -> None:
        """
        Асинхронно проверяет подключение к серверу.

        Args:
            host: Адрес сервера.
            port: Порт сервера.

        Raises:
            ConnectionError: При ошибке подключения к серверу.
            Exception: При других ошибках во время подключения.
        """
        self._is_connecting = True
        self.connection_started.emit()

        try:
            self.connection_status.emit("Подключение...", False)
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(
                None, self.connection_manager.connect_to_server, host, port
            )

            if success:
                self.connection_status.emit("Подключено к серверу", True)
                self.server_version.emit("SpeechEQ Server (gRPC) v1.0.0")
                self._start_connection_check_async()
                self.mode_changed.emit(False)
            else:
                self.connection_status.emit("Сервер недоступен", False)
                self._emit_error_safe(f"Не удалось подключиться к {host}:{port}")
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            self.connection_status.emit("Ошибка подключения", False)
            self._emit_error_safe(str(e))
        finally:
            self._is_connecting = False
            self.connection_finished.emit()

    def disconnect_from_server(self) -> None:
        """Отключается от сервера."""
        if self._is_disconnecting:
            return
        if not self._loop or not self._loop.is_running():
            self._emit_error_safe("AsyncIO не запущен")
            return
        self._is_user_disconnect = True
        asyncio.run_coroutine_threadsafe(self._disconnect_from_server_async(), self._loop)

    async def _disconnect_from_server_async(self) -> None:
        """
        Асинхронно отключается от сервера.

        Raises:
            Exception: При ошибках во время отключения.
        """
        self._is_disconnecting = True
        self.disconnect_started.emit()

        try:
            self.connection_status.emit("Отключение...", False)
            await self.connection_manager.disconnect_from_server()
            self._stop_connection_check()
            self.connection_status.emit("Не подключено", False)
            self.server_version.emit("")
            self.user_disconnected.emit()
        except Exception as e:
            logger.error(f"Ошибка при отключении: {e}")
            self._emit_error_safe(f"Ошибка при отключении: {e}")
        finally:
            self._is_disconnecting = False
            self._is_user_disconnect = False
            self.disconnect_finished.emit()

    def _start_connection_check_async(self) -> None:
        """Запускает фоновую проверку состояния соединения."""
        self._stop_connection_check()

        async def check_loop() -> None:
            self._running = True
            while self._running:
                await asyncio.sleep(5)
                if not self.connection_manager.is_connected():
                    self.connection_status.emit("Потеряно соединение с сервером", False)
                    self.server_version.emit("")
                    if not self._is_user_disconnect:
                        self.connection_lost.emit()
                    break

        self._check_task = asyncio.create_task(check_loop())

    def _stop_connection_check(self) -> None:
        """Останавливает фоновую проверку соединения."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            self._check_task = None

    def is_connecting(self) -> bool:
        """Возвращает True, если идёт подключение."""
        return self._is_connecting

    def is_disconnecting(self) -> bool:
        """Возвращает True, если идёт отключение."""
        return self._is_disconnecting


class ConnectionScreenLogic(QObject):
    """Логика экрана подключения к серверу."""

    cancel_all_tasks_requested = Signal()

    def __init__(self, ui: Any, parent: Any, worker: ConnectionWorker) -> None:
        """
        Инициализирует логику экрана подключения.

        Args:
            ui: Объект UI главного окна.
            parent: Родительский объект.
            worker: Рабочий поток подключения.

        Raises:
            Exception: При ошибках инициализации.
        """
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.worker = worker
        self.connection_manager: Optional[Any] = None
        self.is_connected: bool = False
        self.processing_manager: Optional[Any] = None
        self._is_local_mode_active: bool = False
        self._is_remote_selected: bool = False
        self._connection_lost_handled: bool = False

        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.server_version.connect(self.update_server_version)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.connection_lost.connect(self.on_connection_lost)
        self.worker.user_disconnected.connect(self.on_user_disconnected)
        self.worker.mode_changed.connect(self._on_mode_changed_by_worker)
        self.worker.connection_started.connect(self.refresh_ui)
        self.worker.connection_finished.connect(self.refresh_ui)
        self.worker.disconnect_started.connect(self.refresh_ui)
        self.worker.disconnect_finished.connect(self._on_disconnect_finished)

        self.ui.actionBtn.clicked.connect(self.on_action_clicked)
        self.ui.modeComboBox.currentIndexChanged.connect(self.on_mode_changed)

        self.load_settings()
        self.refresh_ui()

    def set_connection_manager(self, manager: Any) -> None:
        """
        Устанавливает менеджер соединений.

        Args:
            manager: Менеджер gRPC соединений.
        """
        self.connection_manager = manager

    def _is_ui_valid(self) -> bool:
        """Проверяет, что UI-элементы существуют."""
        return self.ui is not None and self.parent is not None

    def _is_any_mode_active(self) -> bool:
        """Проверяет, активен ли какой-либо режим работы."""
        return self._is_local_mode_active or (self.is_connected and self._is_remote_selected)

    def refresh_ui(self) -> None:
        """Обновляет состояние UI-элементов экрана."""
        if not self._is_ui_valid():
            return

        try:
            QCoreApplication.processEvents()
            is_remote = self._is_remote_selected
            is_connecting = self.worker.is_connecting()
            is_disconnecting = self.worker.is_disconnecting()
            is_mode_active = self._is_any_mode_active()
            is_busy = is_connecting or is_disconnecting

            self.ui.modeComboBox.setEnabled(not is_mode_active and not is_busy)
            self.ui.remoteModeWidget.setVisible(is_remote)
            self.ui.localModeWidget.setVisible(not is_remote)

            fields_ok = is_remote and not self.is_connected and not is_connecting and not is_disconnecting
            self.ui.hostLineEdit.setEnabled(fields_ok)
            self.ui.remotePortSpinBox.setEnabled(fields_ok)

            btn = self.ui.actionBtn
            if is_remote:
                if self.is_connected:
                    btn.setText("Отключиться")
                    btn.setEnabled(True)
                elif is_connecting:
                    btn.setText("Подключение...")
                    btn.setEnabled(False)
                elif is_disconnecting:
                    btn.setText("Отключение...")
                    btn.setEnabled(False)
                else:
                    btn.setText("Подключиться к серверу")
                    btn.setEnabled(True)
            else:
                if self._is_local_mode_active:
                    btn.setText("Остановить локальный режим")
                    btn.setEnabled(True)
                else:
                    btn.setText("Запустить локальный режим")
                    btn.setEnabled(True)

            status_lbl = self.ui.connectionStatusLabel
            if self._is_local_mode_active:
                self.ui.localModeInfoLabel.setText("Обработка на локальном компьютере без сервера")
                status_lbl.setText("🟢 Локальный режим активен")
                status_lbl.setStyleSheet("color: #22c55e; padding: 5px; font-weight: bold;")
                self.ui.errorLabel.clear()
            elif is_remote and self.is_connected:
                status_lbl.setText(
                    f"🟢 Подключено к серверу ({self.ui.hostLineEdit.text()}:{self.ui.remotePortSpinBox.value()})"
                )
                status_lbl.setStyleSheet("color: #22c55e; padding: 5px; font-weight: bold;")
                self.ui.errorLabel.clear()
            elif is_remote and is_connecting:
                status_lbl.setText("🟡 Подключение...")
                status_lbl.setStyleSheet("color: #f59e0b; padding: 5px; font-weight: bold;")
            elif is_remote and is_disconnecting:
                status_lbl.setText("🟡 Отключение...")
                status_lbl.setStyleSheet("color: #f59e0b; padding: 5px; font-weight: bold;")
            elif is_remote and not self.is_connected:
                status_lbl.setText("⚪ Не подключено. Введите адрес и порт сервера")
                status_lbl.setStyleSheet("color: #64748b; padding: 5px; font-weight: bold;")
            else:
                self.ui.localModeInfoLabel.setText("Обработка на локальном компьютере без сервера")
                status_lbl.setText("⚪ Локальный режим не запущен")
                status_lbl.setStyleSheet("color: #64748b; padding: 5px; font-weight: bold;")
        except Exception as e:
            logger.error(f"Ошибка обновления UI: {e}")

    def on_mode_changed(self, index: int) -> None:
        """
        Обрабатывает изменение выбранного режима в комбобоксе.

        Args:
            index: Индекс выбранного элемента (0 - локальный, 1 - удалённый).
        """
        if self._is_any_mode_active():
            self.ui.modeComboBox.blockSignals(True)
            self.ui.modeComboBox.setCurrentIndex(1 if self._is_remote_selected else 0)
            self.ui.modeComboBox.blockSignals(False)
            return
        self._is_remote_selected = (index == 1)
        self.refresh_ui()

    def _on_mode_changed_by_worker(self, is_local: bool) -> None:
        """
        Обрабатывает изменение режима, инициированное рабочим потоком.

        Args:
            is_local: True если включён локальный режим, False если удалённый.
        """
        if not self._is_ui_valid():
            return

        if is_local:
            self.is_connected = False
            self._is_local_mode_active = True
            self.ui.modeComboBox.blockSignals(True)
            self.ui.modeComboBox.setCurrentIndex(0)
            self.ui.modeComboBox.blockSignals(False)
            self._is_remote_selected = False
        else:
            self._is_local_mode_active = False
            self.is_connected = True
        self.refresh_ui()

    def _on_disconnect_finished(self) -> None:
        """Обрабатывает завершение отключения от сервера."""
        self.is_connected = False
        self.refresh_ui()

    def set_processing_manager(self, pm: Any) -> None:
        """
        Устанавливает менеджер обработки задач.

        Args:
            pm: Менеджер обработки задач.
        """
        self.processing_manager = pm

    def is_mode_selected(self) -> Tuple[bool, str]:
        """
        Проверяет, выбран ли режим работы.

        Returns:
            tuple[bool, str]: (выбран ли режим, сообщение об ошибке если не выбран)
        """
        if self._is_local_mode_active:
            return True, ""
        if self._is_remote_selected:
            if self.is_connected:
                return True, ""
            return False, "Выбран удалённый режим, но соединение с сервером отсутствует или потеряно."
        return False, "Режим работы не выбран.\nПожалуйста, активируйте локальный режим или подключитесь к серверу."

    def get_current_mode_name(self) -> str:
        """Возвращает название текущего активного режима."""
        if self._is_local_mode_active:
            return "локальный"
        if self.is_connected and self._is_remote_selected:
            return "удалённый"
        return ""

    def clear_errors(self) -> None:
        """Очищает сообщение об ошибке."""
        if self._is_ui_valid():
            self.ui.errorLabel.clear()

    def show_error(self, error_msg: str) -> None:
        """
        Отображает сообщение об ошибке.

        Args:
            error_msg: Текст сообщения об ошибке.
        """
        if self._is_ui_valid():
            self.ui.errorLabel.setText(f"Ошибка: {error_msg}")

    def update_connection_status(self, status: str, connected: bool) -> None:
        """
        Обновляет статус подключения.

        Args:
            status: Текстовый статус подключения.
            connected: Флаг подключения.
        """
        if connected:
            self.is_connected = True
            self.clear_errors()
        else:
            if not self.worker.is_connecting() and not self.worker.is_disconnecting():
                self.is_connected = False
                self.refresh_ui()

    def update_server_version(self, version: str) -> None:
        """
        Обновляет информацию о версии сервера.

        Args:
            version: Строка с версией сервера.
        """
        if version:
            logger.info(f"Версия сервера: {version}")

    def on_connection_lost(self) -> None:
        """Обрабатывает потерю соединения с сервером."""
        if self._connection_lost_handled:
            return
        self._connection_lost_handled = True
        logger.warning("Потеря соединения с сервером")

        if self.processing_manager:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self.processing_manager.fail_remote_tasks("Потеря соединения с сервером")
                    )
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Ошибка при пометке задач: {e}")

        self.is_connected = False
        self._is_remote_selected = False
        self._is_local_mode_active = False

        self.ui.modeComboBox.blockSignals(True)
        self.ui.modeComboBox.setCurrentIndex(0)
        self.ui.modeComboBox.blockSignals(False)

        self.refresh_ui()
        self._show_message_box_safe(
            "Потеря соединения",
            "Соединение с сервером потеряно. Все задачи, работавшие через сервер, остановлены.\n"
            "Локальные задачи не затронуты.\nПожалуйста, выберите режим работы заново.",
            QMessageBox.Warning
        )
        QTimer.singleShot(2000, self._reset_connection_lost_flag)

    def on_user_disconnected(self) -> None:
        """Обрабатывает отключение пользователя от сервера."""
        logger.info("Пользователь отключился от сервера")
        self.cancel_all_tasks_requested.emit()
        self.is_connected = False
        self._is_remote_selected = False
        self.ui.modeComboBox.blockSignals(True)
        self.ui.modeComboBox.setCurrentIndex(0)
        self.ui.modeComboBox.blockSignals(False)
        self.refresh_ui()
        self._show_message_box_safe(
            "Отключение от сервера",
            "Вы отключились от сервера. Задачи, использовавшие сервер, были отменены.",
            QMessageBox.Information
        )

    def _reset_connection_lost_flag(self) -> None:
        """Сбрасывает флаг обработки потери соединения."""
        self._connection_lost_handled = False

    def _show_message_box_safe(self, title: str, message: str, icon: int = QMessageBox.Warning) -> None:
        """
        Безопасно показывает диалоговое окно.

        Args:
            title: Заголовок окна.
            message: Текст сообщения.
            icon: Иконка сообщения (по умолчанию Warning).

        Raises:
            Exception: При ошибках создания диалогового окна.
        """
        if not self._is_ui_valid():
            return
        try:
            msg_box = QMessageBox(self.parent)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Icon(icon))
            msg_box.exec()
        except Exception as e:
            logger.error(f"Ошибка показа сообщения: {e}")

    def load_settings(self) -> None:
        """Загружает сохранённые настройки подключения."""
        try:
            s = QSettings("SpeechEQ", "Connection")
            self.ui.hostLineEdit.setText(s.value("remote_host", "localhost"))
            self.ui.remotePortSpinBox.setValue(s.value("remote_port", 50051, type=int))
            mode = s.value("mode", 0, type=int)
            self.ui.modeComboBox.blockSignals(True)
            self.ui.modeComboBox.setCurrentIndex(mode)
            self.ui.modeComboBox.blockSignals(False)
            self._is_remote_selected = (mode == 1)
            self._is_local_mode_active = False
            self.is_connected = False
        except Exception:
            pass

    def save_settings(self) -> None:
        """Сохраняет настройки подключения."""
        try:
            s = QSettings("SpeechEQ", "Connection")
            s.setValue("remote_host", self.ui.hostLineEdit.text())
            s.setValue("remote_port", self.ui.remotePortSpinBox.value())
            s.setValue("mode", self.ui.modeComboBox.currentIndex())
        except Exception:
            pass

    def _check_active_tasks_sync(self) -> bool:
        """
        Синхронно проверяет наличие активных задач.

        Returns:
            bool: True если есть активные задачи, иначе False.
        """
        if not self.processing_manager:
            return False
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            stats = loop.run_until_complete(self.processing_manager.get_queue_stats())
            loop.close()
            return stats.get("active_tasks", 0) > 0
        except Exception:
            return False

    def on_action_clicked(self) -> None:
        """Обрабатывает нажатие главной кнопки действия."""
        if self.worker.is_connecting() or self.worker.is_disconnecting():
            return

        is_remote = self._is_remote_selected
        if is_remote:
            if self.is_connected:
                self.on_disconnect_clicked()
            else:
                self.on_connect_clicked()
        else:
            if not self._is_local_mode_active:
                if self._is_remote_selected:
                    self._is_remote_selected = False
                    self.ui.modeComboBox.blockSignals(True)
                    self.ui.modeComboBox.setCurrentIndex(0)
                    self.ui.modeComboBox.blockSignals(False)

                if self.connection_manager:
                    self.connection_manager.switch_to_local()

                self._is_local_mode_active = True
                self.refresh_ui()
                self._show_message_box_safe(
                    "Локальный режим запущен",
                    "Теперь перейдите на экран 'ОБРАБОТКА'.",
                    QMessageBox.Information
                )
                if self._is_ui_valid():
                    self.parent.ui.stackedWidget.setCurrentWidget(self.parent.ui.processingScreen)
            else:
                self._is_local_mode_active = False
                self.refresh_ui()
                self._show_message_box_safe(
                    "Локальный режим остановлен",
                    "Локальный режим деактивирован.",
                    QMessageBox.Information
                )

    def on_connect_clicked(self) -> None:
        """Обрабатывает нажатие кнопки подключения к серверу."""
        self.worker.check_remote_connection(
            self.ui.hostLineEdit.text(),
            self.ui.remotePortSpinBox.value()
        )
        self.clear_errors()
        self.save_settings()

    def on_disconnect_clicked(self) -> None:
        """Обрабатывает нажатие кнопки отключения от сервера."""
        if not self.is_connected:
            return

        has_active = self._check_active_tasks_sync()
        if has_active:
            reply = QMessageBox.question(
                self.parent,
                "Активные задачи",
                "Есть активные задачи, работающие через сервер. Отключение отменит их выполнение.\nПродолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.processing_manager.cancel_remote_tasks())
                loop.close()
                logger.info("Удалённые задачи отменены перед отключением пользователя")
            except Exception as e:
                logger.error(f"Ошибка при отмене задач перед отключением: {e}")

        self.worker.disconnect_from_server()