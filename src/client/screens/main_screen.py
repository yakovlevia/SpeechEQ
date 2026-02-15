#!/usr/bin/env python3
"""
Логика главного экрана
"""
from PySide6.QtWidgets import QMessageBox


class MainScreenLogic:
    """Класс для логики главного экрана"""
    
    def __init__(self, ui, parent):
        self.ui = ui
        self.parent = parent
        self.ui.aboutProjectBtn.clicked.connect(self.show_about)
        self.ui.instructionBtn.clicked.connect(self.show_instruction)
        self.ui.licenseBtn.clicked.connect(self.show_license)
    
    def show_about(self):
        """Показать информацию о проекте"""
        QMessageBox.about(
            self.ui.centralwidget,
            "О проекте",
            "<h3>SpeechEQ v1.0</h3>"
            "<p>Профессиональная обработка и улучшение аудио в видеофайлах.</p>"
            "<p><b>Возможности:</b><br>"
            "• Шумоподавление<br>"
            "• Удаление гула 50/60 Гц<br>"
            "• Де-эссер<br>"
            "• Эквализация под речь<br>"
            "• Автоматическая нормализация громкости<br>"
            "• Нейросетевое улучшение речи</p>"
            "<p>© 2024 SpeechEQ Team</p>"
        )
    
    def show_instruction(self):
        """Показать инструкцию"""
        QMessageBox.information(
            self.ui.centralwidget,
            "Инструкция",
            "<h3>Как пользоваться приложением</h3>"
            "<p><b>1. Подключение</b><br>"
            "Выберите режим работы: локальный (на этом компьютере) или удалённый сервер.</p>"
            "<p><b>2. Настройка обработки</b><br>"
            "Включите нужные методы улучшения аудио и настройте параметры.</p>"
            "<p><b>3. Выбор файлов</b><br>"
            "Выберите видеофайлы или папку с видео для обработки.</p>"
            "<p><b>4. Запуск обработки</b><br>"
            "Нажмите 'Начать обработку' и следите за прогрессом.</p>"
            "<p><b>5. Результаты</b><br>"
            "Обработанные файлы сохраняются в указанную папку с суффиксом _speecheq</p>"
        )
    
    def show_license(self):
        """Показать лицензию"""
        QMessageBox.about(
            self.ui.centralwidget,
            "Лицензия",
            "<h3>MIT License</h3>"
            "<p>Copyright (c) 2024 SpeechEQ</p>"
            "<p>Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files, to deal in the Software "
            "without restriction, including without limitation the rights to use, copy, modify, "
            "merge, publish, distribute, sublicense, and/or sell copies of the Software...</p>"
        )