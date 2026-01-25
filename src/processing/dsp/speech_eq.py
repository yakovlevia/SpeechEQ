# processing/dsp/speech_eq.py
import numpy as np
from scipy import signal
from .base import DSPMethod
from processing.core.settings import ProcessingSettings


class SpeechEQDSP(DSPMethod):
    """
    Речевой эквалайзер для улучшения разборчивости речи.
    
    Применяет характерную кривую EQ для подчеркивания
    важных для разборчивости частот (2-5 кГц).
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return settings.eq
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Улучшает разборчивость речи с помощью эквализации.
        
        Args:
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
        
        Returns:
            np.ndarray: Аудио сигнал с улучшенной разборчивостью.
        """
        eq_profile = settings.eq_profile
        
        if eq_profile == "speech_clarity":
            bands = [
                (80, -3, 1.0),    # Ослабление низких басов
                (200, 2, 1.5),    # Подъем нижних средних
                (2500, 4, 2.0),   # Подъем важных для разборчивости частот
                (5000, 3, 2.0),   # Подъем верхних средних
                (8000, -2, 1.0),  # Ослабление резких высоких
            ]
        elif eq_profile == "broadcast":
            # Стандартная вещательная кривая
            bands = [
                (100, -4, 1.0),
                (400, 2, 1.5),
                (3000, 3, 2.0),
                (6000, 1, 1.5),
                (10000, -1, 1.0),
            ]
        else:
            bands = []
        
        processed = audio.copy()
        
        for freq, gain, Q in bands:
            if freq < sample_rate / 2:
                # Создаем пиковый фильтр
                b, a = signal.iirpeak(freq, Q, sample_rate)
                # Применяем усиление/ослабление
                if gain > 0:
                    # Усиление
                    processed = processed + gain * 0.1 * signal.filtfilt(b, a, processed)
                else:
                    # Ослабление
                    processed = signal.filtfilt(b, a, processed)
        
        return processed