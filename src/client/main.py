#!/usr/bin/env python3
"""
Основная точка входа в приложение
"""
import sys
from PySide6.QtWidgets import QApplication
from core.main_window import MainWindow


def main():
    """Основная функция приложения"""
    # Создание приложения
    app = QApplication(sys.argv)
    
    # Создание главного окна
    window = MainWindow()
    
    # Показать окно
    window.show()
    
    # Запуск основного цикла
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())