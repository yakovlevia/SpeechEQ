from abc import ABC, abstractmethod
import numpy as np
from src.processing.core.settings import ProcessingSettings


class AudioProcessingMethod(ABC):

    @abstractmethod
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        pass

    @abstractmethod
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        pass
