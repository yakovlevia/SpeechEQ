# processing/core/processing_logic.py
import numpy as np
from typing import List
from processing.core.settings import ProcessingSettings
from processing.dsp.base import DSPMethod


class AudioProcessingLogic:

    def __init__(
        self,
        dsp_methods: List[DSPMethod],
        ml_methods: List[str] | None = None # Пока тут пусто
    ):
        self.dsp_methods = dsp_methods
        self.ml_methods = ml_methods or []

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:

        processed = audio

        # ===== DSP PIPELINE =====
        for dsp in self.dsp_methods:
            if dsp.is_enabled(settings):
                processed = dsp.process(processed, sample_rate, settings)

        return processed
