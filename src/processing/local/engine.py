# src/processing/local/engine.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from processing.engine import ProcessingEngine, ProcessingSession, StreamInfo
from processing.settings import ProcessingSettings, build_methods
from .pipeline import LocalPipeline


@dataclass
class _LocalSession(ProcessingSession):
    pipeline: LocalPipeline

    def process_chunk(self, chunk: np.ndarray) -> np.ndarray:
        return self.pipeline.process_chunk(chunk)

    def close(self) -> None:
        return


class LocalEngine(ProcessingEngine):
    """
    Локальный движок: на каждый поток создаёт pipeline по settings.
    """

    def __init__(self, settings: ProcessingSettings):
        self._settings = settings

    def open_session(self, stream_info: StreamInfo) -> ProcessingSession:
        methods = build_methods(self._settings)  # новые инстансы методов на сессию
        pipeline = LocalPipeline(methods=methods)
        pipeline.reset(sample_rate=stream_info.sample_rate, num_channels=stream_info.num_channels)
        return _LocalSession(pipeline=pipeline)
