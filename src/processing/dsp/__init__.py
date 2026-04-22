# processing/dsp/__init__.py
from src.processing.core.base import AudioProcessingMethod
from src.processing.dsp.noise_reduction import NoiseReductionDSP
from src.processing.dsp.loudness_normalization import LoudnessNormalizationDSP
from src.processing.dsp.hum_removal import HumRemovalDSP
from src.processing.dsp.deesser import DeEsserDSP
from src.processing.dsp.speech_eq import SpeechEQDSP

__all__ = [
    'AudioProcessingMethod',
    'NoiseReductionDSP',
    'LoudnessNormalizationDSP',
    'HumRemovalDSP',
    'DeEsserDSP',
    'SpeechEQDSP',
]