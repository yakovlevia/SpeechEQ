"""
Экран выбора файлов и настроек обработки.
"""

import os
import logging
import threading
import asyncio
from pathlib import Path
from typing import List, Optional, Any
from PySide6.QtCore import QSettings, Signal, QObject
from PySide6.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from client.video_queue import AudioCleanupTask
from processing.core.settings import ProcessingSettings
import numpy as np
from client.audio_processor import AudioProcessor
from client.config import AUDIO_CONFIG

logger = logging.getLogger(__name__)


class ProcessingScreenLogic(QObject):
    """Логика экрана настройки обработки и выбора файлов."""

    tasks_added = Signal(list)
    processing_started = Signal()

    _global_priority_counter: int = 0
    _counter_lock: Optional[threading.Lock] = None
    _used_output_paths: set = set()
    _paths_lock: Optional[threading.Lock] = None

    def __init__(
        self,
        ui: Any,
        parent: Any,
        audio_handler: Any,
        default_settings: ProcessingSettings,
        connection_manager: Any = None
    ) -> None:
        """
        Инициализирует логику экрана обработки.

        Args:
            ui: Объект UI главного окна.
            parent: Родительский объект.
            audio_handler: Локальный обработчик аудио.
            default_settings: Настройки обработки по умолчанию.
            connection_manager: Менеджер соединений (опционально).

        Raises:
            Exception: При ошибках инициализации.
        """
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.audio_handler = audio_handler
        self.default_settings = default_settings
        self.connection_manager = connection_manager
        self.processing_worker: Optional[Any] = None
        self.selected_files: List[str] = []

        if ProcessingScreenLogic._counter_lock is None:
            ProcessingScreenLogic._counter_lock = threading.Lock()
        if ProcessingScreenLogic._paths_lock is None:
            ProcessingScreenLogic._paths_lock = threading.Lock()

        self.load_settings()
        self.connect_signals()
        self.setup_drag_drop()

    @classmethod
    def _get_next_priority(cls) -> int:
        """
        Возвращает следующий номер приоритета для задачи.

        Returns:
            int: Следующий номер приоритета.

        Raises:
            RuntimeError: Если блокировка не инициализирована.
        """
        if cls._counter_lock is None:
            raise RuntimeError("Счётчик приоритетов не инициализирован")
        with cls._counter_lock:
            cls._global_priority_counter += 1
            return cls._global_priority_counter

    @classmethod
    def reset_priority_counter(cls) -> None:
        """Сбрасывает счётчик приоритетов."""
        if cls._counter_lock is not None:
            with cls._counter_lock:
                cls._global_priority_counter = 0

    @classmethod
    def clear_used_output_paths(cls) -> None:
        """Очищает список использованных выходных путей."""
        if cls._paths_lock is not None:
            with cls._paths_lock:
                cls._used_output_paths.clear()

    @classmethod
    def remove_output_path(cls, output_path: str) -> None:
        """
        Удаляет путь из списка использованных.

        Args:
            output_path: Путь для удаления.
        """
        if cls._paths_lock is not None:
            with cls._paths_lock:
                if output_path in cls._used_output_paths:
                    cls._used_output_paths.remove(output_path)

    def _get_unique_output_path(self, output_folder: Path, input_file: Path, overwrite: bool) -> str:
        """
        Генерирует уникальный путь для выходного файла.

        Args:
            output_folder: Папка для сохранения.
            input_file: Исходный файл.
            overwrite: Перезаписывать ли существующий файл.

        Returns:
            str: Уникальный путь выходного файла.

        Raises:
            RuntimeError: Если блокировка путей не инициализирована.
        """
        if overwrite:
            return str(input_file)

        if self._paths_lock is None:
            raise RuntimeError("Блокировка путей не инициализирована")

        base_name = f"{input_file.stem}_speecheq"
        suffix = input_file.suffix
        counter = 0

        with self._paths_lock:
            while True:
                output_name = f"{base_name}{suffix}" if counter == 0 else f"{base_name}_{counter}{suffix}"
                output_path = output_folder / output_name
                output_path_str = str(output_path)

                if not output_path.exists() and output_path_str not in self._used_output_paths:
                    self._used_output_paths.add(output_path_str)
                    break
                counter += 1

        return str(output_path)

    def set_processing_worker(self, worker: Any) -> None:
        """
        Устанавливает рабочий поток обработки.

        Args:
            worker: Рабочий объект ProcessingWorker.
        """
        self.processing_worker = worker

    def get_current_handler(self) -> Optional[Any]:
        """
        Возвращает текущий обработчик аудио (локальный или удалённый).

        Returns:
            AudioHandler: Активный обработчик аудио или None.
        """
        if self.connection_manager:
            return self.connection_manager.get_current_handler()
        return self.audio_handler

    def connect_signals(self) -> None:
        """Подключает сигналы UI к методам-обработчикам."""
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

    def setup_drag_drop(self) -> None:
        """Настраивает перетаскивание файлов в список."""
        self.ui.fileListWidget.setAcceptDrops(True)
        self.ui.fileListWidget.dragEnterEvent = self.drag_enter_event
        self.ui.fileListWidget.dropEvent = self.drop_event

    def drag_enter_event(self, event: QDragEnterEvent) -> None:
        """
        Обрабатывает вход курсора с файлами.

        Args:
            event: Событие перетаскивания.

        Raises:
            TypeError: Если event имеет неправильный тип.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drop_event(self, event: QDropEvent) -> None:
        """
        Обрабатывает сброс файлов.

        Args:
            event: Событие сброса.

        Raises:
            TypeError: Если event имеет неправильный тип.
        """
        files = [
            url.toLocalFile() for url in event.mimeData().urls()
            if self.is_supported_format(url.toLocalFile())
        ]
        self.add_files(files)

    def is_supported_format(self, file_path: str) -> bool:
        """
        Проверяет, поддерживается ли формат видеофайла.

        Args:
            file_path: Путь к файлу.

        Returns:
            bool: True если формат поддерживается.
        """
        return Path(file_path).suffix.lower() in ['.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv']

    def load_settings(self) -> None:
        """Загружает сохранённые настройки обработки."""
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

    def save_settings(self) -> None:
        """Сохраняет текущие настройки обработки."""
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

    def on_setting_changed(self) -> None:
        """Обработчик изменения любой настройки."""
        self.save_settings()

    def on_select_files(self) -> None:
        """Открывает диалог выбора видеофайлов."""
        files, _ = QFileDialog.getOpenFileNames(
            self.ui.centralwidget,
            "Выберите видеофайлы",
            "",
            "Видео файлы (*.mp4 *.mov *.mkv *.avi *.flv *.wmv);;Все файлы (*.*)"
        )
        if files:
            self.add_files(files)

    def on_select_folder(self) -> None:
        """Открывает диалог выбора папки с видеофайлами."""
        folder = QFileDialog.getExistingDirectory(
            self.ui.centralwidget,
            "Выберите папку с видео"
        )
        if folder:
            files = [
                str(f) for f in Path(folder).iterdir()
                if f.is_file() and self.is_supported_format(str(f))
            ]
            self.add_files(files)
            QMessageBox.information(
                self.ui.centralwidget,
                "Файлы добавлены",
                f"Найдено и добавлено {len(files)} видеофайлов"
            )

    def add_files(self, files: List[str]) -> None:
        """
        Добавляет файлы в список для обработки.

        Args:
            files: Список путей к файлам.
        """
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

    def clear_file_list(self) -> None:
        """Очищает список выбранных файлов."""
        self.ui.fileListWidget.clear()
        self.selected_files.clear()

    def on_browse_output(self) -> None:
        """Открывает диалог выбора папки для сохранения результатов."""
        folder = QFileDialog.getExistingDirectory(
            self.ui.centralwidget,
            "Выберите папку для сохранения результатов"
        )
        if folder:
            self.ui.outputFolderLineEdit.setText(folder)
            self.save_settings()

    def on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """
        Обрабатывает двойной клик по файлу в списке (удаление).

        Args:
            item: Элемент списка, по которому был двойной клик.
        """
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

    def on_clear_queue(self) -> None:
        """Очищает очередь выбранных файлов."""
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
        """
        Собирает настройки обработки из UI.

        Returns:
            ProcessingSettings: Объект с настройками.
        """
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

        # ---------- ML MODEL ----------
        ml_enabled = self.ui.mlModelCombo.currentIndex() == 1

        settings.ml_model = ml_enabled
        settings.ml_model_name = "metricgan_plus" if ml_enabled else None

        return settings

    def create_tasks(self) -> List[AudioCleanupTask]:
        """
        Создаёт задачи обработки для выбранных файлов.

        Returns:
            list: Список объектов AudioCleanupTask.

        Raises:
            Exception: При ошибках получения длительности видео.
        """
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

        output_folder_path = Path(output_folder)
        overwrite = self.ui.overwriteCheck.isChecked()
        settings = self.get_processing_settings()
        tasks: List[AudioCleanupTask] = []
        current_handler = self.get_current_handler()

        if current_handler is None:
            QMessageBox.critical(
                self.ui.centralwidget,
                "Ошибка",
                "Нет доступного обработчика аудио. Проверьте подключение к серверу или выберите локальный режим."
            )
            return []

        audio_proc = AudioProcessor()

        for input_path in self.selected_files:
            input_file = Path(input_path)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                duration = loop.run_until_complete(audio_proc.get_video_duration_fast(input_path))
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

            output_path = self._get_unique_output_path(output_folder_path, input_file, overwrite)
            priority = self._get_next_priority()

            task = AudioCleanupTask(
                priority=priority,
                input_path=input_path,
                output_path=output_path,
                handler=current_handler,
                handler_settings=settings
            )

            if duration > 0:
                task.duration = duration
                task.duration_formatted = task.format_duration(duration)
                task.total_segments = total_segments

            tasks.append(task)

        return tasks

    def on_start_processing(self) -> None:
        """Обрабатывает нажатие кнопки начала обработки."""
        if not self.selected_files:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Нет файлов",
                "Пожалуйста, выберите видеофайлы для обработки."
            )
            return

        if self.processing_worker is None:
            QMessageBox.critical(
                self.ui.centralwidget,
                "Ошибка",
                "Рабочий поток обработки не инициализирован."
            )
            return

        if hasattr(self.parent, 'connection_screen'):
            mode_selected, mode_message = self.parent.connection_screen.is_mode_selected()
        else:
            mode_selected, mode_message = False, "Не удалось определить выбранный режим. Перезапустите приложение."

        if not mode_selected:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Режим работы не выбран",
                mode_message
            )
            return

        current_mode = self.parent.connection_screen.get_current_mode_name() or "неизвестный"

        if not self.ui.outputFolderLineEdit.text():
            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Папка для сохранения не выбрана",
                "Будут использованы файлы по умолчанию: Документы/SpeechEQ_processed\nПродолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        tasks = self.create_tasks()
        if tasks:
            if hasattr(self.parent, 'restart_processing'):
                self.parent.restart_processing()

            QMessageBox.information(
                self.ui.centralwidget,
                "Обработка запущена",
                f"Запущена обработка {len(tasks)} файлов в {current_mode} режиме.\nСледите за прогрессом на экране 'Прогресс'."
            )

            self.tasks_added.emit(tasks)
            self.clear_file_list()
            self.processing_started.emit()
            logger.info(f"Запущена обработка {len(tasks)} файлов в {current_mode} режиме")