# processing/dsp/deesser.py
import numpy as np
from scipy import signal
from .base import DSPMethod
from processing.core.settings import ProcessingSettings


class DeEsserDSP(DSPMethod):
    """
    Де-эссер для подавления сибилянтов (шипящих звуков).
    
    Применяет динамическую обработку в области высоких частот
    (4-8 кГц) для плавного снижения амплитуды сибилянтов.
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return settings.deesser
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Подавляет сибилянты в речевом сигнале.
        
        Args:
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
        
        Returns:
            np.ndarray: Аудио сигнал с уменьшенными сибилянтами.
        """
        strength = settings.deesser_strength
        
        nyquist = sample_rate / 2
        lowcut = 4000 / nyquist
        highcut = 8000 / nyquist
        
        # Полосовой фильтр для выделения сибилянтов
        b, a = signal.butter(4, [lowcut, highcut], btype='band')
        sibilants = signal.filtfilt(b, a, audio)
        
        # Детектор огибающей
        envelope = np.abs(signal.hilbert(sibilants))
        
        # Сглаживание огибающей
        smooth_env = np.convolve(envelope, np.ones(100)/100, mode='same')
        
        # Порог срабатывания
        threshold = np.percentile(smooth_env, 90)
        
        # Создаем маску подавления
        mask = np.ones_like(audio)
        above_threshold = smooth_env > threshold
        
        if np.any(above_threshold):
            # Вычисляем коэффициент подавления
            excess = (smooth_env[above_threshold] - threshold) / threshold
            gain_reduction = 1.0 - strength * np.tanh(excess * 3.0)
            
            # Применяем плавное подавление
            mask[above_threshold] = gain_reduction
            
            # Сглаживаем маску для избежания артефактов
            mask = np.convolve(mask, np.ones(50)/50, mode='same')
        
        # Применяем подавление только к высокочастотной составляющей
        high_freq = signal.filtfilt(b, a, audio)
        low_freq = audio - high_freq
        processed = low_freq + high_freq * mask
        
        return processed