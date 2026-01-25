# processing/dsp/normalization.py
import numpy as np
from .base import DSPMethod


class NormalizationDSP(DSPMethod):

    def is_enabled(self, settings):
        return settings.normalization

    def process(self, audio, sample_rate, settings):
        target = settings.normalization_target
        peak = np.max(np.abs(audio))
        if peak == 0:
            return audio
        return (audio / peak) * target
