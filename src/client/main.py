"""
Основная точка входа в приложение
"""
import sys
import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

from client.core.main_window import MainWindow
from client.processing_manager import ProcessingManager
from client.workers.processing_worker import ProcessingWorker
from processing.core.processing_logic import AudioProcessingLogic
from processing.core.settings import ProcessingSettings
from processing.dsp import (
    NoiseReductionDSP,
    HumRemovalDSP,
    DeEsserDSP,
    SpeechEQDSP,
    LoudnessNormalizationDSP
)
from processing.handlers.local import LocalAudioHandler

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
    Создает цепочку DSP-методов для улучшения речи.
    """
    logger.info("Инициализация пайплайна обработки аудио")
    
    # Создание цепочки DSP-методов
    dsp_methods = [
        HumRemovalDSP(),           # Удаление гула 50/60 Гц
        NoiseReductionDSP(),        # Шумоподавление
        DeEsserDSP(),               # Де-эссер (удаление шипящих)
        SpeechEQDSP(),              # Эквализация под речь
        LoudnessNormalizationDSP(), # Нормализация громкости
    ]
    
    # Логика обработки с DSP-методами
    processing_logic = AudioProcessingLogic(
        dsp_methods=dsp_methods,
        ml_methods=[]  # ML-методы пока не используются
    )
    
    # Создание обработчика
    audio_handler = LocalAudioHandler(processing_logic=processing_logic)
    
    logger.info(f"Пайплайн инициализирован: {[method.__class__.__name__ for method in dsp_methods]}")
    
    return audio_handler, processing_logic


def get_default_settings() -> ProcessingSettings:
    """
    Создание настроек обработки по умолчанию.
    
    Returns:
        ProcessingSettings: Настройки со значениями по умолчанию
    """
    settings = ProcessingSettings()
    
    # DSP настройки (все включены по умолчанию)
    settings.hum_removal = True
    settings.hum_frequency = 50.0  # 50 Гц для Европы/России
    settings.hum_removal_strength = 0.8
    
    settings.noise_reduction = True
    settings.noise_reduction_level = 0.7
    
    settings.deesser = True
    settings.deesser_strength = 0.6
    
    settings.eq = True
    settings.eq_profile = "speech_clarity"
    
    settings.normalization = True
    settings.normalization_target = -16.0  # LUFS
    
    return settings


class Application(QApplication):
    """
    Главный класс приложения с интеграцией asyncio.
    """
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Инициализация пайплайна обработки
        self.audio_handler, self.processing_logic = setup_processing_pipeline()
        
        # Настройки по умолчанию
        self.default_settings = get_default_settings()
        
        # Создание менеджера обработки
        self.processing_manager = ProcessingManager()
        
        # Создание главного окна
        self.main_window = MainWindow(
            audio_handler=self.audio_handler,
            processing_manager=self.processing_manager,
            default_settings=self.default_settings
        )
        
        # ИНИЦИАЛИЗАЦИЯ РАБОЧЕГО ПОТОКА
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.processing_manager)
        self.processing_worker.moveToThread(self.processing_thread)
        
        # Подключение сигналов рабочего потока к главному окну
        self.processing_worker.progress_updated.connect(
            self.main_window.on_progress_updated
        )
        self.processing_worker.task_finished.connect(
            self.main_window.on_task_finished
        )
        self.processing_worker.task_started.connect(
            self.main_window.on_task_started
        )
        
        # Установка рабочего потока в главном окне
        self.main_window.set_processing_worker(self.processing_worker)
        
        # Подключение сигналов потока
        self.processing_thread.started.connect(self.processing_worker.setup_asyncio)
        self.processing_thread.finished.connect(self.processing_worker.deleteLater)
        
        # Запуск потока
        self.processing_thread.start()
        
        logger.info("Приложение инициализировано, рабочий поток запущен")
    
    def exec(self):
        """Запуск приложения"""
        # Показ главного окна
        self.main_window.show()
        
        # Запуск главного цикла Qt
        return super().exec()
    
    def shutdown(self):
        """Корректное завершение работы"""
        logger.info("Завершение работы приложения...")
        
        # Остановка рабочего потока
        if hasattr(self, 'processing_worker'):
            logger.info("Остановка рабочего потока...")
            self.processing_worker.stop()
        
        # Остановка менеджера обработки
        if hasattr(self, 'processing_manager'):
            # Создаем временный event loop для остановки
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Запускаем остановку с таймаутом
                loop.run_until_complete(
                    asyncio.wait_for(
                        self.processing_manager.stop_processing(),
                        timeout=5.0
                    )
                )
            except asyncio.TimeoutError:
                logger.warning("Таймаут при остановке обработки")
            except Exception as e:
                logger.error(f"Ошибка при остановке обработки: {e}")
            finally:
                # Отменяем все оставшиеся задачи
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Даём время на отмену
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                
                loop.close()
        
        # Остановка рабочего потока
        if hasattr(self, 'processing_thread') and self.processing_thread.isRunning():
            logger.info("Ожидание завершения рабочего потока...")
            self.processing_thread.quit()
            
            # Даём потоку время на завершение (5 секунд)
            if not self.processing_thread.wait(5000):
                logger.warning("Рабочий поток не завершился, принудительное завершение")
                self.processing_thread.terminate()
                self.processing_thread.wait()
        
        logger.info("Приложение завершено")


def main():
    """
    Основная функция приложения.
    
    Returns:
        int: Код возврата приложения.
    """
    logger.info("=" * 60)
    logger.info("Запуск SpeechEQ v1.0")
    logger.info("=" * 60)
    
    # Создание приложения
    app = Application(sys.argv)
    
    # Запуск главного цикла
    result = app.exec()
    
    # Корректное завершение
    app.shutdown()
    
    return result


if __name__ == "__main__":
    sys.exit(main())