# processing/handlers/server.py
import numpy as np
from .base import AudioHandler
from processing.core.settings import ProcessingSettings


class ServerAudioHandler(AudioHandler):
    """
    Серверная обработка (gRPC)
    """

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        # тут потом будет сериализация и отправка на сервер
        return self.processing_logic.process(
            audio=audio,
            sample_rate=sample_rate,
            settings=settings
        )
