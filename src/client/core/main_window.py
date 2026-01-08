#!/usr/bin/env python3
"""
Главное окно приложения
"""
from PySide6.QtWidgets import QMainWindow

# Импорт UI
from ui.ui_mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    """Основной класс главного окна"""
    
    def __init__(self):
        super().__init__()
        
        # Настройка UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Установка заголовка окна
        self.setWindowTitle("Audio Processing Application")
        
        # Настройка навигации (только переключение экранов)
        self.setup_navigation()
        
    def setup_navigation(self):
        """Настройка навигации по кнопкам"""
        
        # Навигация по кнопкам внизу
        self.ui.mainScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.mainScreen)
        )
        self.ui.processingScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.processingScreen)
        )
        self.ui.progressScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.progressScreen)
        )
        self.ui.emptyScreenBtn.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.emptyScreen)
        )