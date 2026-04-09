import numpy as np
from typing import List

from processing.core.base import AudioProcessingMethod
from processing.core.settings import ProcessingSettings


class AudioProcessingLogic:
    """
    Центральная логика обработки аудио.

    Поддерживает:
    - DSP методы
    - ML методы

    Методы выполняются в заданном порядке.
    """

    def __init__(
        self,
        processing_methods: List[AudioProcessingMethod],
    ):
        self.processing_methods = processing_methods

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings,
    ) -> np.ndarray:
        """
        Обрабатывает один сегмент аудио.

        Parameters
        ----------
        audio : np.ndarray
            float32 массив [-1, 1]
        sample_rate : int
            частота дискретизации
        settings : ProcessingSettings
        """

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        audio = np.clip(audio, -1.0, 1.0)

        for method in self.processing_methods:

            if method.is_enabled(settings):
                audio = method.process(
                    audio,
                    sample_rate,
                    settings,
                )

        return audio