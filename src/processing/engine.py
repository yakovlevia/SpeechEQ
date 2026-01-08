# src/processing/engine.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Iterator

import numpy as np


@dataclass(frozen=True)
class StreamInfo:
    sample_rate: int
    num_channels: int


class ProcessingSession(ABC):
    """
    Сессия обработки одного потока (одного файла).
    Содержит state (фильтры/ML состояние).
    """

    @abstractmethod
    def process_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """
        chunk: np.ndarray float32, shape (N,) или (N,C)
        return: np.ndarray float32
        """
        raise NotImplementedError

    def close(self) -> None:
        """Опционально (например для server с grpc-stream)."""
        return


class ProcessingEngine(ABC):
    """
    Абстрактный движок. Для каждого файла/потока создаётся session.
    LocalEngine и будущий GrpcEngine должны реализовать этот интерфейс.
    """

    @abstractmethod
    def open_session(self, stream_info: StreamInfo) -> ProcessingSession:
        raise NotImplementedError

    def process_stream(
        self,
        chunks: Iterable[np.ndarray],
        stream_info: StreamInfo,
    ) -> Iterator[np.ndarray]:
        """
        Удобный streaming helper: открывает session и гонит итератор чанков.
        """
        session = self.open_session(stream_info)
        try:
            for chunk in chunks:
                if chunk is None:
                    continue
                if getattr(chunk, "size", 0) == 0:
                    continue
                y = session.process_chunk(chunk)
                yield y
        finally:
            session.close()
