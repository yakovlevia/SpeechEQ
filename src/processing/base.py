# src/processing/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator
import numpy as np


@dataclass(frozen=True)
class StreamInfo:
    sample_rate: int
    num_channels: int


@dataclass(frozen=True)
class ProcessingSettings:
    dehum_notch: bool = True


class AsyncProcessingSession(ABC):
    @abstractmethod
    async def process_chunk(self, chunk: np.ndarray) -> np.ndarray:
        pass

    async def close(self) -> None:
        pass


class AsyncProcessingEngine(ABC):
    def __init__(self, settings: ProcessingSettings):
        self.settings = settings

    @abstractmethod
    async def open_session(self, stream_info: StreamInfo) -> AsyncProcessingSession:
        pass

    async def process_stream(
        self,
        chunks: AsyncIterator[np.ndarray],
        stream_info: StreamInfo,
    ) -> AsyncIterator[np.ndarray]:
        session = await self.open_session(stream_info)
        try:
            async for chunk in chunks:
                if chunk is None or chunk.size == 0:
                    continue
                yield await session.process_chunk(chunk)
        finally:
            await session.close()
