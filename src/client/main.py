# src/client/main.py
"""
Основная точка входа в приложение
"""
import sys
from PySide6.QtWidgets import QApplication
from core.main_window import MainWindow


def main():
    """
    Основная функция приложения.
    
    Создает QApplication, инициализирует главное окно
    и запускает главный цикл событий.
    
    Returns:
        int: Код возврата приложения.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())