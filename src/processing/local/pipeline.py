# src/processing/local/pipeline.py
from __future__ import annotations

from typing import Sequence
import numpy as np

from processing.methods.base import AudioMethod


class LocalPipeline:
    """
    Пайплайн DSP/ML методов (stateful), работает чанками.
    Один pipeline = один поток/файл.
    """

    def __init__(self, methods: Sequence[AudioMethod]):
        self.methods = list(methods)
        self._initialized = False

    def reset(self, sample_rate: int, num_channels: int) -> None:
        for m in self.methods:
            m.reset(sample_rate=sample_rate, num_channels=num_channels)
        self._initialized = True

    def process_chunk(self, chunk: np.ndarray) -> np.ndarray:
        if not self._initialized:
            raise RuntimeError("Pipeline not initialized. Call reset() before processing.")

        x = chunk
        if x.dtype != np.float32:
            x = x.astype(np.float32, copy=False)

        for m in self.methods:
            x = m.process(x)
            if x.dtype != np.float32:
                x = x.astype(np.float32, copy=False)

        return x
