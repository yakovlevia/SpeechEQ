# processing/core/settings.py
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ProcessingSettings:
    """
    Единые настройки обработки (DSP + ML)
    """

    # ===== DSP FLAGS =====
    noise_reduction: bool = False
    normalization: bool = False
    deesser: bool = False
    eq: bool = False

    # ===== DSP PARAMS =====
    noise_reduction_level: float = 0.5
    normalization_target: float = 0.95
    deesser_strength: float = 0.5
    eq_profile: str = "flat"

    # ===== ML FLAGS =====
    ml_enhance: bool = False
    ml_denoise: bool = False

    # ===== ML PARAMS =====
    ml_model_name: str = "base"
    ml_strength: float = 0.7

    # ===== EXTENSIBLE =====
    extra: Dict[str, Any] = field(default_factory=dict)
