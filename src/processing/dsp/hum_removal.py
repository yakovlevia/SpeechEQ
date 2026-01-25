# processing/dsp/hum_removal.py
import numpy as np
from scipy import signal
from .base import DSPMethod
from processing.core.settings import ProcessingSettings


class HumRemovalDSP(DSPMethod):
    """
    Удаление гула 50/60 Гц и его гармоник.
    
    Использует режекторные фильтры для подавления сетевой помехи
    и ее гармоник (100/120 Гц, 150/180 Гц и т.д.).
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return settings.hum_removal
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Удаляет сетевую помеху и ее гармоники.
        
        Args:
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
        
        Returns:
            np.ndarray: Обработанный аудио сигнал без сетевой помехи.
        """
        hum_freq = settings.hum_frequency  # 50 или 60 Гц
        strength = settings.hum_removal_strength
        
        # Определяем гармоники для удаления
        harmonics = [hum_freq, hum_freq * 2, hum_freq * 3]
        
        processed = audio.copy()
        
        for freq in harmonics:
            if freq < sample_rate / 2:  # Проверяем частоту Найквиста
                # Создаем режекторный фильтр
                Q = 30 * strength  # Добротность зависит от силы обработки
                b, a = signal.iirnotch(freq, Q, sample_rate)
                processed = signal.filtfilt(b, a, processed)
        
        return processed