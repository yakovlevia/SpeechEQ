# processing/handlers/base.py
from abc import ABC, abstractmethod
import numpy as np
from src.processing.core.settings import ProcessingSettings


class AudioHandler(ABC):

    def __init__(self, processing_logic):
        self.processing_logic = processing_logic

    @abstractmethod
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        pass
