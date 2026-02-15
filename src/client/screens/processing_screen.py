#!/usr/bin/env python3
"""
Логика экрана обработки и выбора источников
"""
import os
import logging
from pathlib import Path
from PySide6.QtCore import QSettings, Signal, QObject
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from client.video_queue import AudioCleanupTask
from processing.core.settings import ProcessingSettings

logger = logging.getLogger(__name__)


class ProcessingScreenLogic(QObject):
    """Класс для логики экрана обработки"""

    tasks_added = Signal(list)
    processing_started = Signal()

    def __init__(self, ui, parent, audio_handler, default_settings):
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.audio_handler = audio_handler
        self.default_settings = default_settings
        self.processing_worker = None
        self.selected_files = []
        self.load_settings()
        self.connect_signals()
        self.setup_drag_drop()
    
    def set_processing_worker(self, worker):
        """Установка рабочего потока обработки"""
        self.processing_worker = worker
    
    def connect_signals(self):
        """Подключение сигналов кнопок"""
        # DSP методы
        self.ui.noiseReductionCheck.toggled.connect(self.on_setting_changed)
        self.ui.noiseReductionSlider.valueChanged.connect(self.on_setting_changed)
        self.ui.humRemovalCheck.toggled.connect(self.on_setting_changed)
        self.ui.humFrequencyCombo.currentIndexChanged.connect(self.on_setting_changed)
        self.ui.deEsserCheck.toggled.connect(self.on_setting_changed)
        self.ui.deEsserSlider.valueChanged.connect(self.on_setting_changed)
        self.ui.eqCheck.toggled.connect(self.on_setting_changed)

        # ML методы
        self.ui.mlModelCombo.currentIndexChanged.connect(self.on_setting_changed)

        # Общие настройки
        self.ui.normalizationCheck.toggled.connect(self.on_setting_changed)
        self.ui.lufsSpinBox.valueChanged.connect(self.on_setting_changed)

        # Выбор источников
        self.ui.selectFilesBtn.clicked.connect(self.on_select_files)
        self.ui.selectFolderBtn.clicked.connect(self.on_select_folder)
        self.ui.browseOutputBtn.clicked.connect(self.on_browse_output)

        # Управление очередью
        self.ui.startProcessingBtn.clicked.connect(self.on_start_processing)
        self.ui.clearQueueBtn.clicked.connect(self.on_clear_queue)

        # Удаление элементов из списка
        self.ui.fileListWidget.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def setup_drag_drop(self):
        """Настройка drag & drop"""
        self.ui.fileListWidget.setAcceptDrops(True)
        self.ui.fileListWidget.dragEnterEvent = self.drag_enter_event
        self.ui.fileListWidget.dropEvent = self.drop_event
    
    def drag_enter_event(self, event: QDragEnterEvent):
        """Обработка входа перетаскивания"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def drop_event(self, event: QDropEvent):
        """Обработка сброса файлов"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if self.is_supported_format(file_path):
                files.append(file_path)
        
        self.add_files(files)
    
    def is_supported_format(self, file_path: str) -> bool:
        """Проверка поддержки формата файла"""
        supported_formats = ['.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv']
        ext = Path(file_path).suffix.lower()
        return ext in supported_formats
    
    def load_settings(self):
        """Загрузка сохранённых настроек"""
        saved_settings = QSettings("SpeechEQ", "Processing")

        self.ui.noiseReductionCheck.setChecked(
            saved_settings.value("noise_reduction", self.default_settings.noise_reduction, type=bool)
        )
        self.ui.noiseReductionSlider.setValue(
            saved_settings.value("noise_reduction_level", int(self.default_settings.noise_reduction_level * 10), type=int)
        )
        self.ui.humRemovalCheck.setChecked(
            saved_settings.value("hum_removal", self.default_settings.hum_removal, type=bool)
        )
        self.ui.humFrequencyCombo.setCurrentIndex(
            0 if saved_settings.value("hum_frequency", 50, type=int) == 50 else 1
        )
        self.ui.deEsserCheck.setChecked(
            saved_settings.value("deesser", self.default_settings.deesser, type=bool)
        )
        self.ui.deEsserSlider.setValue(
            saved_settings.value("deesser_strength", int(self.default_settings.deesser_strength * 10), type=int)
        )
        self.ui.eqCheck.setChecked(
            saved_settings.value("eq", self.default_settings.eq, type=bool)
        )
        self.ui.mlModelCombo.setCurrentIndex(
            saved_settings.value("ml_model", 0, type=int)
        )
        self.ui.normalizationCheck.setChecked(
            saved_settings.value("normalization", self.default_settings.normalization, type=bool)
        )
        self.ui.lufsSpinBox.setValue(
            saved_settings.value("lufs_target", int(self.default_settings.normalization_target), type=int)
        )

        output_folder = saved_settings.value("output_folder", "")
        if output_folder:
            self.ui.outputFolderLineEdit.setText(output_folder)

        self.ui.overwriteCheck.setChecked(
            saved_settings.value("overwrite", False, type=bool)
        )
    
    def save_settings(self):
        """Сохранение настроек"""
        saved_settings = QSettings("SpeechEQ", "Processing")
        saved_settings.setValue("noise_reduction", self.ui.noiseReductionCheck.isChecked())
        saved_settings.setValue("noise_reduction_level", self.ui.noiseReductionSlider.value())
        saved_settings.setValue("hum_removal", self.ui.humRemovalCheck.isChecked())
        saved_settings.setValue("hum_frequency", 50 if self.ui.humFrequencyCombo.currentIndex() == 0 else 60)
        saved_settings.setValue("deesser", self.ui.deEsserCheck.isChecked())
        saved_settings.setValue("deesser_strength", self.ui.deEsserSlider.value())
        saved_settings.setValue("eq", self.ui.eqCheck.isChecked())
        saved_settings.setValue("ml_model", self.ui.mlModelCombo.currentIndex())
        saved_settings.setValue("normalization", self.ui.normalizationCheck.isChecked())
        saved_settings.setValue("lufs_target", self.ui.lufsSpinBox.value())
        saved_settings.setValue("output_folder", self.ui.outputFolderLineEdit.text())
        saved_settings.setValue("overwrite", self.ui.overwriteCheck.isChecked())
    
    def on_setting_changed(self):
        """Обработчик изменения настроек"""
        self.save_settings()
    
    def on_select_files(self):
        """Обработчик выбора файлов"""
        files, _ = QFileDialog.getOpenFileNames(
            self.ui.centralwidget,
            "Выберите видеофайлы",
            "",
            "Видео файлы (*.mp4 *.mov *.mkv *.avi *.flv *.wmv);;Все файлы (*.*)"
        )
        
        if files:
            self.add_files(files)
    
    def on_select_folder(self):
        """Обработчик выбора папки"""
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
        """Добавление файлов в список"""
        added = 0
        for file in files:
            if file not in self.selected_files:
                self.selected_files.append(file)
                self.ui.fileListWidget.addItem(os.path.basename(file))
                added += 1
        
        self.ui.fileListWidget.setToolTip(f"Всего файлов: {len(self.selected_files)}")
        
        if added > 0:
            QMessageBox.information(
                self.ui.centralwidget,
                "Файлы добавлены",
                f"Добавлено {added} файлов в очередь"
            )
    
    def on_browse_output(self):
        """Обработчик выбора папки вывода"""
        folder = QFileDialog.getExistingDirectory(
            self.ui.centralwidget,
            "Выберите папку для сохранения результатов"
        )
        
        if folder:
            self.ui.outputFolderLineEdit.setText(folder)
            self.save_settings()
    
    def on_item_double_clicked(self, item):
        """Обработчик двойного клика по элементу списка"""
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
        """Очистка списка файлов"""
        if self.selected_files:
            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Очистка очереди",
                f"Очистить список из {len(self.selected_files)} файлов?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.ui.fileListWidget.clear()
                self.selected_files.clear()
    
    def get_processing_settings(self) -> ProcessingSettings:
        """Получение настроек обработки из UI"""
        settings = ProcessingSettings()
        
        # DSP настройки
        settings.noise_reduction = self.ui.noiseReductionCheck.isChecked()
        settings.noise_reduction_level = self.ui.noiseReductionSlider.value() / 10.0
        
        settings.hum_removal = self.ui.humRemovalCheck.isChecked()
        settings.hum_frequency = 50.0 if self.ui.humFrequencyCombo.currentIndex() == 0 else 60.0
        settings.hum_removal_strength = 0.8
        
        settings.deesser = self.ui.deEsserCheck.isChecked()
        settings.deesser_strength = self.ui.deEsserSlider.value() / 10.0
        
        settings.eq = self.ui.eqCheck.isChecked()
        settings.eq_profile = "speech_clarity"
        
        # Общие настройки
        settings.normalization = self.ui.normalizationCheck.isChecked()
        settings.normalization_target = float(self.ui.lufsSpinBox.value())
        
        # ML настройки (пока заглушка)
        ml_model = self.ui.mlModelCombo.currentIndex()
        settings.use_ml = ml_model > 0
        settings.ml_model = ["none", "v1", "v2"][ml_model]
        
        return settings
    
    def create_tasks(self) -> list:
        """Создание задач из выбранных файлов"""
        if not self.selected_files:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Нет файлов",
                "Выберите файлы для обработки"
            )
            return []
        
        output_folder = self.ui.outputFolderLineEdit.text()
        if not output_folder:
            # Папка по умолчанию
            output_folder = str(Path.home() / "Videos" / "SpeechEQ_processed")
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            self.ui.outputFolderLineEdit.setText(output_folder)
        
        settings = self.get_processing_settings()
        tasks = []
        
        for i, input_path in enumerate(self.selected_files):
            input_file = Path(input_path)
            if self.ui.overwriteCheck.isChecked():
                output_name = f"{input_file.stem}_speecheq{input_file.suffix}"
                output_path = str(input_file.parent / output_name)
            else:
                output_name = f"{input_file.stem}_speecheq{input_file.suffix}"
                output_path = str(Path(output_folder) / output_name)

            counter = 1
            while Path(output_path).exists():
                base_name = f"{input_file.stem}_speecheq"
                output_name = f"{base_name}_{counter}{input_file.suffix}"
                output_path = str(Path(output_folder) / output_name)
                counter += 1

            task = AudioCleanupTask(
                priority=i + 1,
                input_path=input_path,
                output_path=output_path,
                handler=self.audio_handler,
                handler_settings=settings
            )
            tasks.append(task)
        return tasks
    
    def on_start_processing(self):
        """Обработчик кнопки начала обработки"""
        tasks = self.create_tasks()
        
        if tasks:
            self.tasks_added.emit(tasks)
            if self.processing_worker:
                self.processing_worker.process_tasks(tasks)
                logger.info(f"Запущена обработка {len(tasks)} задач в рабочем потоке")

            QMessageBox.information(
                self.ui.centralwidget,
                "Обработка запущена",
                f"Запущена обработка {len(tasks)} файлов.\n"
                f"Следите за прогрессом на экране 'Прогресс'"
            )