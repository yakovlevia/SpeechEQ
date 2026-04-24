"""
Логика главного экрана
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox


class MainScreenLogic:
    """Управляет отображением информационных диалогов на главном экране."""

    def __init__(self, ui: Any, parent: Any) -> None:
        """
        Инициализирует логику главного экрана.

        Args:
            ui: Объект UI главного окна.
            parent: Родительский объект.

        Raises:
            AttributeError: Если у UI объекта отсутствуют ожидаемые кнопки.
        """
        self.ui = ui
        self.parent = parent
        self.ui.aboutProjectBtn.clicked.connect(self.show_about)
        self.ui.instructionBtn.clicked.connect(self.show_instruction)
        self.ui.licenseBtn.clicked.connect(self.show_license)

        # Загрузка логотипа
        self._load_logo()

    def _load_logo(self) -> None:
        current_dir = Path(__file__).parent
        client_dir = current_dir.parent
        logo_path = client_dir / "ui" / "resources" / "logo.png"

        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                max_size = self.ui.logoImageLabel.maximumSize()
                scaled_pixmap = pixmap.scaled(
                    max_size.width(), max_size.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.ui.logoImageLabel.setPixmap(scaled_pixmap)
                self.ui.logoImageLabel.setScaledContents(False)
        else:
            print(f"Логотип не найден: {logo_path}")

    def show_about(self) -> None:
        """Отображает подробную информацию о проекте SpeechEQ."""
        QMessageBox.about(
            self.ui.centralwidget,
            "О проекте SpeechEQ",
            "<h3>SpeechEQ — Эквалайзер речи в видеозаписях</h3>"
            "<p><b>Версия 1.0 (2026)</b><br>"
            "Выпускная квалификационная работа студента группы БПИ221<br>"
            "НИУ ВШЭ, факультет компьютерных наук</p>"

            "<p><b>Назначение</b><br>"
            "Программа предназначена для автоматического повышения разборчивости и качества речи "
            "в видеозаписях лекций, вебинаров, совещаний и других образовательных/деловых материалов. "
            "Обработка выполняется локально (или на собственном сервере) без передачи данных в облако, "
            "что гарантирует полную конфиденциальность.</p>"

            "<p><b>Технологии обработки</b><br>"
            "• <b>Нейросетевые модели</b> для подавления нестационарных шумов и реверберации:<br>"
            " — MetricGAN+ (дообучена на русской речи)<br>"
            " — FRCRN_SE_16K<br>"
            " — MossFormerGAN_SE_16K<br>"
            "• <b>DSP-методы</b>: шумоподавление, удаление гула 50/60 Гц, де-эссер, "
            "речевой эквалайзер, нормализация громкости по стандарту EBU R128 (LUFS).<br>"
            "• <b>Пакетная обработка</b> видео с сохранением исходного видеоряда (ремультиплексирование).</p>"

            "<p><b>Архитектура</b><br>"
            "Клиент-серверная система на базе gRPC. Поддерживаются два режима работы:<br>"
            "— <b>Локальный режим</b>: обработка на том же компьютере (без сети);<br>"
            "— <b>Удалённый сервер</b>: ресурсоёмкие вычисления на выделенном узле.</p>"

            "<p><b>Разработка</b><br>"
            "Язык: Python 3.10<br>"
            "GUI: PySide6 (Qt)<br>"
            "ML: PyTorch, SpeechBrain<br>"
            "Медиа: FFmpeg<br>"
            "Сетевое взаимодействие: gRPC, Protocol Buffers<br>"
            "Лицензия: MIT</p>"

            "<p>© 2026 Яковлев И.А., НИУ ВШЭ<br>"
            "Исходный код: <a href='https://github.com/yakovlevia/SpeechEQ'>github.com/yakovlevia/SpeechEQ</a></p>"
        )

    def show_instruction(self) -> None:
        """Отображает подробную инструкцию по использованию приложения."""
        QMessageBox.information(
            self.ui.centralwidget,
            "Инструкция по работе с SpeechEQ",
            "<h3>Как пользоваться приложением</h3>"

            "<p><b>1. Выбор режима работы (экран «Подключение»)</b><br>"
            "• <b>Локальный режим</b> — запустите локальный сервер (кнопка «Запустить локальный режим»).<br>"
            "• <b>Удалённый сервер</b> — укажите адрес и порт сервера, нажмите «Подключиться».</p>"

            "<p><b>2. Настройка обработки (экран «Обработка»)</b><br>"
            "<b>DSP-методы</b> (все можно включать/отключать):<br>"
            " ✓ Шумоподавление — интенсивность (1–10).<br>"
            " ✓ Удаление гула 50/60 Гц — выбор частоты.<br>"
            " ✓ Де-эссер — подавление шипящих звуков (1–10).<br>"
            " ✓ Эквализация под речь — улучшение разборчивости.<br>"
            " ✓ Автоматическая нормализация громкости — целевой уровень LUFS (по умолчанию –16).<br>"
            "<b>ML-методы</b> (выбор модели):<br>"
            " • Не использовать ML-модели<br>"
            " • FRCRN_SE_16K<br>"
            " • MossFormerGAN_SE_16K<br>"
            " • MetricGAN+ (дообучена на русской речи)<br>"
            "Обратите внимание: ML-модели требуют больше ресурсов, особенно на CPU без CUDA.</p>"

            "<p><b>3. Выбор источников</b><br>"
            "• Кнопки «Выбрать файлы...» (можно несколько) или «Выбрать папку...».<br>"
            "• Поддерживаемые форматы: MP4, MOV, MKV.<br>"
            "• Укажите папку для сохранения обработанных файлов.<br>"
            "• При необходимости включите «Сохранять в тот же файл (перезапись)» (осторожно!).</p>"

            "<p><b>4. Запуск обработки</b><br>"
            "Нажмите «Начать обработку». Приложение автоматически переключится на экран «Прогресс».</p>"

            "<p><b>5. Управление очередью (экран «Прогресс»)</b><br>"
            "• Таблица задач: статус, прогресс по сегментам, длительность.<br>"
            "• Кнопки: «Приостановить выбранные», «Возобновить выбранные», «Отменить выбранные».<br>"
            "• «Очистить готовые» — удалить завершённые задачи.<br>"
            "• «Открыть лог» — просмотреть журнал событий.</p>"

            "<p><b>Советы</b><br>"
            "✓ Для ускорения ML-обработки используйте компьютер с видеокартой NVIDIA (CUDA).<br>"
            "✓ Пакетная обработка папок позволяет автоматически улучшить все видео в каталоге.<br>"
            "✓ При выборе режима «Удалённый сервер» обработка выполняется на мощном сервере, "
            "а клиент только управляет задачами.</p>"
        )

    def show_license(self) -> None:
        """Отображает текст лицензии MIT (актуальный для 2026 года)."""
        QMessageBox.about(
            self.ui.centralwidget,
            "Лицензия MIT",
            "<h3>MIT License</h3>"
            "<p>Copyright (c) 2026 Яковлев И.А.</p>"
            "<p>Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the \"Software\"), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies "
            "of the Software, and to permit persons to whom the Software is furnished to do so, "
            "subject to the following conditions:</p>"
            "<p>The above copyright notice and this permission notice shall be included in all "
            "copies or substantial portions of the Software.</p>"
            "<p>THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, "
            "INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR "
            "PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE "
            "FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, "
            "ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.</p>"
            "<p><b>Используемые компоненты</b><br>"
            "• PySide6 (LGPLv3)<br>"
            "• PyTorch (BSD-style)<br>"
            "• SpeechBrain (Apache 2.0)<br>"
            "• FFmpeg (GPLv3/LGPL)<br>"
            "• gRPC (Apache 2.0)<br>"
            "• NumPy, SciPy, noisereduce, pyloudnorm (BSD/MIT)</p>"
        )