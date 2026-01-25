# processing/dsp/noise_reduction.py
import numpy as np
from .base import DSPMethod


class NoiseReductionDSP(DSPMethod):

    def is_enabled(self, settings):
        return settings.noise_reduction

    def process(self, audio, sample_rate, settings):
        level = settings.noise_reduction_level  # параметр
        return audio * (1.0 - level * 0.1)
