# processing/dsp/__init__.py
from ..core.base import AudioProcessingMethod
from .noise_reduction import NoiseReductionDSP
from .loudness_normalization import LoudnessNormalizationDSP
from .hum_removal import HumRemovalDSP
from .deesser import DeEsserDSP
from .speech_eq import SpeechEQDSP

__all__ = [
    'AudioProcessingMethod',
    'NoiseReductionDSP',
    'LoudnessNormalizationDSP',
    'HumRemovalDSP',
    'DeEsserDSP',
    'SpeechEQDSP',
]