# processing/handlers/local.py
import numpy as np
from .base import AudioHandler
from processing.core.settings import ProcessingSettings


class LocalAudioHandler(AudioHandler):
    """
    Локальная обработка (CPU / локальные библиотеки)
    """

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        return self.processing_logic.process(
            audio=audio,
            sample_rate=sample_rate,
            settings=settings
        )
