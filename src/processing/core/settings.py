# processing/core/settings.py
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ProcessingSettings:
    """
    Единые настройки обработки аудио (DSP + ML).
    
    Параметры разделены на:
    - FLAGS: включение/выключение методов (управляются чекбоксами в UI)
    - ADJUSTABLE PARAMS: параметры с UI-контролами (слайдеры, spinbox, combo)
    - FIXED PARAMS: параметры без UI-контролов (значения по умолчанию)
    """

    # ========== DSP FLAGS (UI: checkboxes) ==========
    noise_reduction: bool = True
    hum_removal: bool = True
    deesser: bool = True
    eq: bool = True
    normalization: bool = True
    
    # ========== DSP ADJUSTABLE PARAMS (UI: sliders, combos, spinboxes) ==========
    
    # Noise Reduction (UI: slider 1-10 → 0.1-1.0)
    noise_reduction_level: float = 0.7
    
    # Hum Removal (UI: combo 50Hz/60Hz)
    hum_frequency: float = 50.0  # 50.0 или 60.0
    
    # De-Esser (UI: slider 1-10 → 0.1-1.0)
    deesser_strength: float = 0.6
    
    # Normalization (UI: spinbox -30 to -10)
    normalization_target: float = -16.0  # LUFS
    
    # ========== DSP FIXED PARAMS (no UI controls) ==========
    
    # Hum Removal - добротность фильтра (фиксированная)
    hum_removal_strength: float = 0.8  # используется для расчета количества гармоник
    
    # EQ - профиль эквализации (фиксированный)
    eq_profile: str = "speech_clarity"  # "speech_clarity" | "broadcast" | "flat"
    
    # De-Esser - временные параметры (фиксированные)
    deesser_attack_time: float = 0.005   # 5 мс
    deesser_release_time: float = 0.050  # 50 мс
    
    # ========== ML FLAGS ==========
    ml_model: bool = False
    
    # ========== ML PARAMS ==========
    
    ml_model_name: str = ""  # "" | "metricgan_plus" | "FRCRN_SE_16K" | "MossFormerGAN_SE_16K"
    
    # ML Strength (фиксированный, можно добавить slider позже)
    ml_strength: float = 0.3
    
    # ========== EXTENSIBLE ==========
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация значений после инициализации."""
        # Clamp noise_reduction_level
        self.noise_reduction_level = max(0.0, min(1.0, self.noise_reduction_level))
        
        # Validate hum_frequency
        if self.hum_frequency not in (50.0, 60.0):
            self.hum_frequency = 50.0
        
        # Clamp deesser_strength
        self.deesser_strength = max(0.0, min(1.0, self.deesser_strength))
        
        # Clamp normalization_target
        self.normalization_target = max(-30.0, min(-10.0, self.normalization_target))
        
        # Validate ml_model_name
        if self.ml_model_name not in (
            "",
            "metricgan_plus",
            "FRCRN_SE_16K",
            "MossFormerGAN_SE_16K",
        ):
            self.ml_model_name = ""

        
        # Sync ml_model flag with ml_model_name
        self.ml_model = bool(self.ml_model_name)
