# src/processing/methods/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
import numpy as np


class AudioMethod(ABC):
    """
    Интерфейс для DSP/ML методов.

    Формат данных:
      - np.ndarray dtype float32
      - shape: (n_samples,) или (n_samples, n_channels)
    """

    @abstractmethod
    def reset(self, sample_rate: int, num_channels: int) -> None:
        """Сброс состояния перед новым файлом/потоком."""
        raise NotImplementedError

    @abstractmethod
    def process(self, chunk: np.ndarray) -> np.ndarray:
        """Обработка одного чанка. Должен сохранять streaming-состояние внутри."""
        raise NotImplementedError
