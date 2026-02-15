#!/usr/bin/env python3
"""
Логика экрана подключения к серверу
"""
import asyncio
import socket
from PySide6.QtCore import QSettings, Signal, QObject, Qt
from PySide6.QtWidgets import QMessageBox


class ConnectionWorker(QObject):
    """Рабочий класс для асинхронных операций подключения"""
    
    connection_status = Signal(str, bool)
    server_version = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        self._running = False
        self._local_server_process = None
    
    async def check_remote_connection(self, host: str, port: int):
        """Проверка подключения к удалённому серверу"""
        try:
            # Здесь будет реальная проверка через gRPC
            # Пока имитируем проверку
            await asyncio.sleep(1)
            
            # Проверка доступности порта
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                self.connection_status.emit("Подключено к серверу", True)
                self.server_version.emit("SpeechEQ Server v1.0.0")
            else:
                self.connection_status.emit("Сервер недоступен", False)
                self.error_occurred.emit(f"Не удалось подключиться к {host}:{port}")
                
        except Exception as e:
            self.connection_status.emit("Ошибка подключения", False)
            self.error_occurred.emit(str(e))
    
    async def start_local_server(self, port: int = 8080):
        """Запуск локального сервера"""
        try:
            self.connection_status.emit("Запуск локального сервера...", False)
            
            # Здесь будет реальный запуск серверного процесса
            # Пока имитируем запуск
            await asyncio.sleep(2)
            
            self.connection_status.emit("Локальный сервер запущен", True)
            self.server_version.emit("SpeechEQ Server v1.0.0 (локальный)")
            
        except Exception as e:
            self.connection_status.emit("Ошибка запуска", False)
            self.error_occurred.emit(f"Ошибка запуска сервера: {e}")
    
    async def stop_local_server(self):
        """Остановка локального сервера"""
        try:
            self.connection_status.emit("Остановка сервера...", False)
            
            # Здесь будет реальная остановка сервера
            await asyncio.sleep(1)
            
            self.connection_status.emit("Сервер остановлен", False)
            
        except Exception as e:
            self.error_occurred.emit(f"Ошибка остановки сервера: {e}")


class ConnectionScreenLogic:
    """Класс для логики экрана подключения"""
    
    def __init__(self, ui, parent, worker):
        self.ui = ui
        self.parent = parent
        self.worker = worker
        
        # Загрузка сохранённых настроек
        self.load_settings()
        
        # Подключение сигналов
        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.server_version.connect(self.update_server_version)
        self.worker.error_occurred.connect(self.show_error)
        
        # Подключение кнопок
        self.ui.modeComboBox.currentIndexChanged.connect(self.on_mode_changed)
        self.ui.startLocalBtn.clicked.connect(self.on_start_local_clicked)
        self.ui.connectBtn.clicked.connect(self.on_connect_clicked)
        
        # Инициализация состояния
        self.update_mode_visibility()
        self.is_connected = False
        self.is_local_running = False
    
    def load_settings(self):
        """Загрузка сохранённых настроек"""
        saved_settings = QSettings("SpeechEQ", "Connection")
        
        # Режим работы
        mode = saved_settings.value("mode", 0, type=int)
        self.ui.modeComboBox.setCurrentIndex(mode)
        
        # Параметры удалённого сервера
        host = saved_settings.value("remote_host", "localhost")
        port = saved_settings.value("remote_port", 8080, type=int)
        
        self.ui.hostLineEdit.setText(host)
        self.ui.remotePortSpinBox.setValue(port)
    
    def save_settings(self):
        """Сохранение настроек"""
        saved_settings = QSettings("SpeechEQ", "Connection")
        
        saved_settings.setValue("mode", self.ui.modeComboBox.currentIndex())
        saved_settings.setValue("remote_host", self.ui.hostLineEdit.text())
        saved_settings.setValue("remote_port", self.ui.remotePortSpinBox.value())
    
    def on_mode_changed(self, index):
        """Обработчик изменения режима работы"""
        self.update_mode_visibility()
        self.save_settings()
    
    def update_mode_visibility(self):
        """Обновление видимости виджетов в зависимости от режима"""
        is_local = (self.ui.modeComboBox.currentIndex() == 0)
        
        self.ui.localModeWidget.setVisible(is_local)
        self.ui.remoteModeWidget.setVisible(not is_local)
    
    def update_connection_status(self, status: str, connected: bool):
        """Обновление статуса подключения"""
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
            else:
                self.ui.connectBtn.setText("Подключиться")
    
    def update_server_version(self, version: str):
        """Обновление информации о версии сервера"""
        self.ui.serverVersionLabel.setText(version)
    
    def show_error(self, error_msg: str):
        """Отображение ошибки"""
        self.ui.errorLabel.setText(f"Ошибка: {error_msg}")
        QMessageBox.warning(self.ui.centralwidget, "Ошибка подключения", error_msg)
    
    def on_start_local_clicked(self):
        """Обработчик кнопки запуска/остановки локального сервера"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if self.is_local_running:
                loop.run_until_complete(self.worker.stop_local_server())
            else:
                loop.run_until_complete(self.worker.start_local_server())
        finally:
            loop.close()
    
    def on_connect_clicked(self):
        """Обработчик кнопки подключения/отключения"""
        if self.is_connected:
            self.update_connection_status("Отключено", False)
            self.ui.serverVersionLabel.setText("")
        else:
            host = self.ui.hostLineEdit.text()
            port = self.ui.remotePortSpinBox.value()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(
                    self.worker.check_remote_connection(host, port)
                )
            finally:
                loop.close()

        self.save_settings()
