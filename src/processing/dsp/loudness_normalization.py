# processing/dsp/loudness_normalization.py
import numpy as np
from .base import DSPMethod
from processing.core.settings import ProcessingSettings


class LoudnessNormalizationDSP(DSPMethod):
    """
    Нормализация громкости по стандарту EBU R128 (LUFS).
    
    Реализует алгоритм измерения интегральной громкости
    и нормализацию к заданному целевому уровню.
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return settings.normalization
    
    def _calculate_lufs(self, audio: np.ndarray, sample_rate: int) -> float:
        """
        Вычисляет приблизительный уровень LUFS.
        
        Args:
            audio (np.ndarray): Аудио сигнал.
            sample_rate (int): Частота дискретизации.
        
        Returns:
            float: Приблизительный уровень в LUFS.
        """
        rms = np.sqrt(np.mean(audio ** 2))
        if rms == 0:
            return -70
        
        lufs = 20 * np.log10(rms) + 3
        
        return float(lufs)
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Нормализует громкость к целевому уровню LUFS.
        
        Args:
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
        
        Returns:
            np.ndarray: Аудио сигнал с нормализованной громкостью.
        
        Note:
            Использует упрощенную модель LUFS для демонстрации.
            В продакшн-решении следует использовать библиотеку
            вроде pyloudnorm.
        """
        target_lufs = settings.normalization_target
        
        current_lufs = self._calculate_lufs(audio, sample_rate)
        
        gain_db = target_lufs - current_lufs
        gain_linear = 10 ** (gain_db / 20)
        
        processed = audio * gain_linear
        
        threshold = 0.95
        processed = np.where(
            np.abs(processed) > threshold,
            np.sign(processed) * (threshold + (1 - threshold) * 
                np.tanh((np.abs(processed) - threshold) / (1 - threshold))),
            processed
        )
        
        return processed