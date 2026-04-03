"""
Экран выбора файлов и настроек обработки.
"""
import os
import logging
from pathlib import Path
from PySide6.QtCore import QSettings, Signal, QObject
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from client.video_queue import AudioCleanupTask
from processing.core.settings import ProcessingSettings
import asyncio
import numpy as np
from client.audio_processor import AudioProcessor
from client.config import AUDIO_CONFIG

logger = logging.getLogger(__name__)


class ProcessingScreenLogic(QObject):
    """Логика экрана выбора файлов и настроек."""

    tasks_added = Signal(list)
    processing_started = Signal()

    def __init__(self, ui, parent, audio_handler, default_settings, connection_manager=None):
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.audio_handler = audio_handler
        self.default_settings = default_settings
        self.connection_manager = connection_manager
        self.processing_worker = None
        self.selected_files = []

        self.load_settings()
        self.connect_signals()
        self.setup_drag_drop()

    def set_processing_worker(self, worker):
        self.processing_worker = worker
        logger.info("Установлен рабочий поток обработки")

    def get_current_handler(self):
        """Возвращает текущий обработчик (локальный или удалённый)."""
        if self.connection_manager:
            return self.connection_manager.get_current_handler()
        return self.audio_handler

    def connect_signals(self):
        self.ui.noiseReductionCheck.toggled.connect(self.on_setting_changed)
        self.ui.noiseReductionSlider.valueChanged.connect(self.on_setting_changed)
        self.ui.humRemovalCheck.toggled.connect(self.on_setting_changed)
        self.ui.humFrequencyCombo.currentIndexChanged.connect(self.on_setting_changed)
        self.ui.deEsserCheck.toggled.connect(self.on_setting_changed)
        self.ui.deEsserSlider.valueChanged.connect(self.on_setting_changed)
        self.ui.eqCheck.toggled.connect(self.on_setting_changed)
        self.ui.mlModelCombo.currentIndexChanged.connect(self.on_setting_changed)
        self.ui.normalizationCheck.toggled.connect(self.on_setting_changed)
        self.ui.lufsSpinBox.valueChanged.connect(self.on_setting_changed)

        self.ui.selectFilesBtn.clicked.connect(self.on_select_files)
        self.ui.selectFolderBtn.clicked.connect(self.on_select_folder)
        self.ui.browseOutputBtn.clicked.connect(self.on_browse_output)

        self.ui.startProcessingBtn.clicked.connect(self.on_start_processing)
        self.ui.clearQueueBtn.clicked.connect(self.on_clear_queue)

        self.ui.fileListWidget.itemDoubleClicked.connect(self.on_item_double_clicked)

    def setup_drag_drop(self):
        self.ui.fileListWidget.setAcceptDrops(True)
        self.ui.fileListWidget.dragEnterEvent = self.drag_enter_event
        self.ui.fileListWidget.dropEvent = self.drop_event

    def drag_enter_event(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drop_event(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if self.is_supported_format(file_path):
                files.append(file_path)
        self.add_files(files)

    def is_supported_format(self, file_path: str) -> bool:
        supported = ['.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv']
        return Path(file_path).suffix.lower() in supported

    def load_settings(self):
        saved = QSettings("SpeechEQ", "Processing")

        self.ui.noiseReductionCheck.setChecked(
            saved.value("noise_reduction", self.default_settings.noise_reduction, type=bool)
        )
        self.ui.noiseReductionSlider.setValue(
            saved.value("noise_reduction_level", int(self.default_settings.noise_reduction_level * 10), type=int)
        )
        self.ui.humRemovalCheck.setChecked(
            saved.value("hum_removal", self.default_settings.hum_removal, type=bool)
        )
        self.ui.humFrequencyCombo.setCurrentIndex(
            0 if saved.value("hum_frequency", 50, type=int) == 50 else 1
        )
        self.ui.deEsserCheck.setChecked(
            saved.value("deesser", self.default_settings.deesser, type=bool)
        )
        self.ui.deEsserSlider.setValue(
            saved.value("deesser_strength", int(self.default_settings.deesser_strength * 10), type=int)
        )
        self.ui.eqCheck.setChecked(
            saved.value("eq", self.default_settings.eq, type=bool)
        )
        self.ui.mlModelCombo.setCurrentIndex(
            saved.value("ml_model", 0, type=int)
        )
        self.ui.normalizationCheck.setChecked(
            saved.value("normalization", self.default_settings.normalization, type=bool)
        )
        self.ui.lufsSpinBox.setValue(
            saved.value("lufs_target", int(self.default_settings.normalization_target), type=int)
        )

        output_folder = saved.value("output_folder", "")
        if output_folder:
            self.ui.outputFolderLineEdit.setText(output_folder)

        self.ui.overwriteCheck.setChecked(
            saved.value("overwrite", False, type=bool)
        )

    def save_settings(self):
        saved = QSettings("SpeechEQ", "Processing")
        saved.setValue("noise_reduction", self.ui.noiseReductionCheck.isChecked())
        saved.setValue("noise_reduction_level", self.ui.noiseReductionSlider.value())
        saved.setValue("hum_removal", self.ui.humRemovalCheck.isChecked())
        saved.setValue("hum_frequency", 50 if self.ui.humFrequencyCombo.currentIndex() == 0 else 60)
        saved.setValue("deesser", self.ui.deEsserCheck.isChecked())
        saved.setValue("deesser_strength", self.ui.deEsserSlider.value())
        saved.setValue("eq", self.ui.eqCheck.isChecked())
        saved.setValue("ml_model", self.ui.mlModelCombo.currentIndex())
        saved.setValue("normalization", self.ui.normalizationCheck.isChecked())
        saved.setValue("lufs_target", self.ui.lufsSpinBox.value())
        saved.setValue("output_folder", self.ui.outputFolderLineEdit.text())
        saved.setValue("overwrite", self.ui.overwriteCheck.isChecked())

    def on_setting_changed(self):
        self.save_settings()

    def on_select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self.ui.centralwidget,
            "Выберите видеофайлы",
            "",
            "Видео файлы (*.mp4 *.mov *.mkv *.avi *.flv *.wmv);;Все файлы (*.*)"
        )
        if files:
            self.add_files(files)

    def on_select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self.ui.centralwidget,
            "Выберите папку с видео"
        )
        if folder:
            files = []
            for file in Path(folder).iterdir():
                if file.is_file() and self.is_supported_format(str(file)):
                    files.append(str(file))
            self.add_files(files)
            QMessageBox.information(
                self.ui.centralwidget,
                "Файлы добавлены",
                f"Найдено и добавлено {len(files)} видеофайлов"
            )

    def add_files(self, files: list):
        added = 0
        for file in files:
            if file not in self.selected_files:
                self.selected_files.append(file)
                self.ui.fileListWidget.addItem(os.path.basename(file))
                added += 1

        self.ui.fileListWidget.setToolTip(f"Всего файлов: {len(self.selected_files)}")
        if added > 0:
            logger.debug(f"Добавлено {added} файлов в очередь")
            QMessageBox.information(
                self.ui.centralwidget,
                "Файлы добавлены",
                f"Добавлено {added} файлов в очередь"
            )

    def clear_file_list(self):
        self.ui.fileListWidget.clear()
        self.selected_files.clear()
        logger.info("Список файлов очищен")

    def on_browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self.ui.centralwidget,
            "Выберите папку для сохранения результатов"
        )
        if folder:
            self.ui.outputFolderLineEdit.setText(folder)
            self.save_settings()

    def on_item_double_clicked(self, item):
        index = self.ui.fileListWidget.row(item)
        if 0 <= index < len(self.selected_files):
            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Удаление файла",
                f"Удалить файл '{item.text()}' из списка?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.ui.fileListWidget.takeItem(index)
                self.selected_files.pop(index)

    def on_clear_queue(self):
        if self.selected_files:
            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Очистка очереди",
                f"Очистить список из {len(self.selected_files)} файлов?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.clear_file_list()

    def get_processing_settings(self) -> ProcessingSettings:
        settings = ProcessingSettings()

        settings.noise_reduction = self.ui.noiseReductionCheck.isChecked()
        settings.noise_reduction_level = self.ui.noiseReductionSlider.value() / 10.0

        settings.hum_removal = self.ui.humRemovalCheck.isChecked()
        settings.hum_frequency = 50.0 if self.ui.humFrequencyCombo.currentIndex() == 0 else 60.0
        settings.hum_removal_strength = 0.8

        settings.deesser = self.ui.deEsserCheck.isChecked()
        settings.deesser_strength = self.ui.deEsserSlider.value() / 10.0

        settings.eq = self.ui.eqCheck.isChecked()
        settings.eq_profile = "speech_clarity"

        settings.normalization = self.ui.normalizationCheck.isChecked()
        settings.normalization_target = float(self.ui.lufsSpinBox.value())

        ml_model = self.ui.mlModelCombo.currentIndex()
        settings.ml_model = ml_model > 0
        settings.ml_model_name = ["", "v1", "v2"][ml_model]

        return settings

    def create_tasks(self) -> list:
        if not self.selected_files:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Нет файлов",
                "Выберите файлы для обработки"
            )
            return []

        output_folder = self.ui.outputFolderLineEdit.text()
        if not output_folder:
            output_folder = str(Path.home() / "Videos" / "SpeechEQ_processed")
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            self.ui.outputFolderLineEdit.setText(output_folder)

        settings = self.get_processing_settings()
        tasks = []
        current_handler = self.get_current_handler()
        audio_proc = AudioProcessor()

        for i, input_path in enumerate(self.selected_files):
            input_file = Path(input_path)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                duration = loop.run_until_complete(
                    audio_proc.get_video_duration_fast(input_path)
                )
                loop.close()
            except Exception as e:
                logger.error(f"Ошибка получения длительности {input_path}: {e}")
                duration = 0.0

            total_segments = 0
            if duration > 0:
                seg_dur = AUDIO_CONFIG["segment_duration"]
                overlap = AUDIO_CONFIG["overlap_duration"]
                step = max(seg_dur - overlap, 1)
                total_segments = max(1, int(np.ceil((duration - overlap) / step)))
                logger.debug(f"Видео {input_file.name}: длительность {duration:.1f}s, сегментов {total_segments}")

            if self.ui.overwriteCheck.isChecked():
                output_path = str(input_file)
            else:
                output_name = f"{input_file.stem}_speecheq{input_file.suffix}"
                output_path = str(Path(output_folder) / output_name)
                counter = 1
                while Path(output_path).exists():
                    output_name = f"{input_file.stem}_speecheq_{counter}{input_file.suffix}"
                    output_path = str(Path(output_folder) / output_name)
                    counter += 1

            task = AudioCleanupTask(
                priority=i + 1,
                input_path=input_path,
                output_path=output_path,
                handler=current_handler,
                handler_settings=settings
            )

            if duration > 0:
                task.duration = duration
                task.duration_formatted = task.format_duration(duration)
            if total_segments > 0:
                task.total_segments = total_segments

            tasks.append(task)

        return tasks

    def on_start_processing(self):
        if self.connection_manager and not self.connection_manager.is_local():
            if not self.connection_manager.is_connected():
                QMessageBox.warning(
                    self.ui.centralwidget,
                    "Нет подключения",
                    "Вы выбрали удаленный режим, но нет подключения к серверу.\n"
                    "Подключитесь на экране 'Подключение' или переключитесь в локальный режим."
                )
                return

        tasks = self.create_tasks()
        if tasks:
            self.tasks_added.emit(tasks)
            self.clear_file_list()
            self.processing_started.emit()
            mode = "локальный" if not self.connection_manager or self.connection_manager.is_local() else "удаленный"
            logger.info(f"Запущена обработка {len(tasks)} файлов в {mode} режиме")
            QMessageBox.information(
                self.ui.centralwidget,
                "Обработка запущена",
                f"Запущена обработка {len(tasks)} файлов в {mode} режиме.\n"
                f"Следите за прогрессом на экране 'Прогресс'"
            )