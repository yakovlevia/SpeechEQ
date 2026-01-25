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
    hum_removal: bool = False  # Новый флаг
    deesser: bool = False
    eq: bool = False
    normalization: bool = False
    
    # ===== DSP PARAMS =====
    noise_reduction_level: float = 0.5
    hum_frequency: float = 50.0  # 50 или 60 Гц
    hum_removal_strength: float = 0.8
    deesser_strength: float = 0.5
    eq_profile: str = "speech_clarity"  # "flat", "speech_clarity", "broadcast"
    normalization_target: float = -16.0  # Целевой уровень LUFS
    
    # ===== ML FLAGS =====
    ml_enhance: bool = False
    ml_denoise: bool = False
    
    # ===== ML PARAMS =====
    ml_model_name: str = "base"
    ml_strength: float = 0.7
    
    # ===== EXTENSIBLE =====
    extra: Dict[str, Any] = field(default_factory=dict)