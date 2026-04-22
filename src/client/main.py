"""
Основная точка входа в приложение SpeechEQ.

Инициализирует пайплайн обработки аудио, создаёт главное окно,
настраивает рабочий поток для обработки задач и запускает
главный цикл приложения.
"""
import sys
import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

from src.client.core.main_window import MainWindow
from src.client.processing_manager import ProcessingManager
from src.client.workers.processing_worker import ProcessingWorker
from src.processing.core.processing_logic import AudioProcessingLogic
from src.processing.core.settings import ProcessingSettings
from src.processing.dsp import (
    NoiseReductionDSP,
    HumRemovalDSP,
    DeEsserDSP,
    SpeechEQDSP,
    LoudnessNormalizationDSP
)
from src.processing.ml import (
    FRCRNSE16KMethod,
    MossFormerGANSE16KMethod,
    MetricGANPlusMethod,
)
from src.processing.handlers.local import LocalAudioHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('speecheq_debug.log')
    ]
)
logger = logging.getLogger(__name__)


def setup_processing_pipeline():
    """
    Настройка пайплайна обработки аудио.

    Создаёт цепочку методов для улучшения речи в следующем порядке:
    1. FRCRN / MossFormerGAN / MetricGAN+ (ML) — основное улучшение и очистка речи
    2. NoiseReductionDSP — опциональная мягкая доочистка остаточного шума
    3. HumRemovalDSP — точечное удаление сетевого гула 50/60 Гц и гармоник
    4. DeEsserDSP — подавление сибилянтов (шипящих звуков)
    5. SpeechEQDSP — эквализация под речевой диапазон (финальный тембр)
    6. LoudnessNormalizationDSP — нормализация громкости (LUFS) и true-peak лимитинг

    ML-модель должна идти первой, так как она обучена на сыром сигнале.
    DSP-методы после неё лишь доводят звук и не создают артефактов.

    Returns:
        tuple: (audio_handler, processing_logic) — обработчик и логика обработки
    """
    logger.info("Инициализация пайплайна обработки аудио")

    processing_methods = [
        FRCRNSE16KMethod(preload=True),           # ML улучшение речи
        MossFormerGANSE16KMethod(preload=True),   # ML улучшение речи
        MetricGANPlusMethod(preload=True),        # ML улучшение речи
        NoiseReductionDSP(),                      # Шумоподавление
        HumRemovalDSP(),                          # Удаление гула 50/60 Гц
        DeEsserDSP(),                             # Подавление шипящих звуков
        SpeechEQDSP(),                            # Эквализация под речевой диапазон
        LoudnessNormalizationDSP(),               # Нормализация громкости
    ]


    processing_logic = AudioProcessingLogic(
        processing_methods=processing_methods
    )

    audio_handler = LocalAudioHandler(processing_logic=processing_logic)

    logger.info(f"Пайплайн инициализирован: {[method.__class__.__name__ for method in processing_methods]}")

    return audio_handler, processing_logic


def get_default_settings() -> ProcessingSettings:
    """
    Создаёт настройки обработки по умолчанию.

    Returns:
        ProcessingSettings: Настройки со значениями по умолчанию
    """
    settings = ProcessingSettings()

    settings.hum_removal = True
    settings.hum_frequency = 50.0
    settings.hum_removal_strength = 0.8

    settings.noise_reduction = True
    settings.noise_reduction_level = 0.7

    settings.deesser = True
    settings.deesser_strength = 0.6

    settings.eq = True
    settings.eq_profile = "speech_clarity"

    settings.normalization = True
    settings.normalization_target = -16.0

    settings.ml_model = False

    return settings


class Application(QApplication):
    """
    Главный класс приложения с интеграцией asyncio.

    Управляет инициализацией всех компонентов, созданием главного окна,
    запуском рабочего потока и корректным завершением работы.

    Attributes:
        audio_handler (LocalAudioHandler): Обработчик аудио для локального режима
        processing_logic (AudioProcessingLogic): Логика обработки аудио
        default_settings (ProcessingSettings): Настройки обработки по умолчанию
        processing_manager (ProcessingManager): Менеджер обработки задач
        processing_thread (QThread): Поток для выполнения обработки
        processing_worker (ProcessingWorker): Рабочий объект в отдельном потоке
        main_window (MainWindow): Главное окно приложения
    """

    def __init__(self, argv):
        """
        Инициализирует приложение и все его компоненты.

        Args:
            argv (list): Аргументы командной строки
        """
        super().__init__(argv)

        self.audio_handler, self.processing_logic = setup_processing_pipeline()

        self.default_settings = get_default_settings()

        self.processing_manager = ProcessingManager()

        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.processing_manager)
        self.processing_worker.moveToThread(self.processing_thread)

        self.main_window = MainWindow(
            audio_handler=self.audio_handler,
            processing_manager=self.processing_manager,
            default_settings=self.default_settings
        )

        self.main_window.set_processing_worker(self.processing_worker, self.processing_thread)

        self.processing_worker.progress_updated.connect(
            self.main_window.on_progress_updated
        )
        self.processing_worker.task_finished.connect(
            self.main_window.on_task_finished
        )
        self.processing_worker.task_started.connect(
            self.main_window.on_task_started
        )

        self.processing_thread.started.connect(self.processing_worker.setup_asyncio)
        self.processing_thread.finished.connect(self.processing_worker.deleteLater)

        self.processing_thread.start()

        logger.info("Приложение инициализировано, рабочий поток запущен")

    def exec(self):
        """
        Запускает главный цикл приложения.

        Returns:
            int: Код возврата приложения
        """
        self.main_window.show()
        return super().exec()

    def shutdown(self):
        """Выполняет корректное завершение работы приложения."""
        logger.info("Завершение работы приложения...")

        if hasattr(self, 'processing_worker'):
            logger.info("Остановка рабочего потока...")
            self.processing_worker.stop()
        
        import time
        time.sleep(0.5)

        if hasattr(self, 'processing_manager'):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def shutdown_manager():
                    try:
                        await asyncio.wait_for(
                            self.processing_manager.stop_processing(),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Таймаут при остановке обработки")
                
                loop.run_until_complete(shutdown_manager())
                
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    if not task.done():
                        task.cancel()
                
                if pending:
                    try:
                        loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending, return_exceptions=True),
                                timeout=2.0
                            )
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Таймаут при отмене оставшихся задач")
                        
            except Exception as e:
                logger.error(f"Ошибка при остановке обработки: {e}")
            finally:
                loop.close()

        if hasattr(self, 'processing_thread') and self.processing_thread.isRunning():
            logger.info("Ожидание завершения рабочего потока...")
            self.processing_thread.quit()
            if not self.processing_thread.wait(5000):
                logger.warning("Рабочий поток не завершился, принудительное завершение")
                self.processing_thread.terminate()
                self.processing_thread.wait()

        logger.info("Приложение завершено")


def main():
    """
    Основная функция приложения.

    Returns:
        int: Код возврата приложения
    """
    logger.info("=" * 60)
    logger.info("Запуск SpeechEQ v1.0")
    logger.info("=" * 60)

    app = Application(sys.argv)

    result = app.exec()

    app.shutdown()

    return result


if __name__ == "__main__":
    sys.exit(main())