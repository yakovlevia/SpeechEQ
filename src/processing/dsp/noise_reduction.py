import numpy as np
import noisereduce as nr
from src.processing.core.base import AudioProcessingMethod
from src.processing.core.settings import ProcessingSettings
import logging

logger = logging.getLogger(__name__)


class NoiseReductionDSP(AudioProcessingMethod):
    """
    Шумоподавление с использованием библиотеки noisereduce.
    
    Использует алгоритм статистического шумоподавления с минимальными
    артефактами.
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        """
        Определяет, включено ли шумоподавление в настройках.

        Args:
            settings: Настройки обработки.

        Returns:
            bool: True если шумоподавление включено.
        """
        return settings.noise_reduction
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Применяет шумоподавление через noisereduce.

        Args:
            audio (np.ndarray): Входной аудио сигнал (моно, float32, [-1, 1]).
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.

        Returns:
            np.ndarray: Очищенный аудио сигнал.
        """
        if len(audio) < 1024:
            return audio
        
        strength = np.clip(settings.noise_reduction_level, 0.0, 1.0)
        
        try:
            reduced = nr.reduce_noise(
                y=audio,
                sr=sample_rate,
                stationary=True,
                prop_decrease=strength,
                freq_mask_smooth_hz=500,
                time_mask_smooth_ms=50
            )
            
            logger.debug(f"noisereduce применен (strength={strength:.2f})")
            return reduced
            
        except Exception as e:
            logger.error(f"Ошибка в noisereduce: {e}, возвращаем исходный сигнал")
            return audio