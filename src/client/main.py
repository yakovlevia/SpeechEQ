#!/usr/bin/env python3
"""
Основная точка входа в приложение
"""
import sys
from PySide6.QtWidgets import QApplication
from core.main_window import MainWindow


def main():
    """Основная функция приложения"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())