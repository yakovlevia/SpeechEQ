import numpy as np
from scipy import signal
import pyloudnorm as pyln
from processing.core.base import AudioProcessingMethod
from processing.core.settings import ProcessingSettings
import logging

logger = logging.getLogger(__name__)


class LoudnessNormalizationDSP(AudioProcessingMethod):
    """
    Нормализация громкости по стандарту EBU R128 (LUFS).
    
    Использует библиотеку pyloudnorm для измерения интегральной
    громкости согласно ITU-R BS.1770-4 / EBU R128.
    """
    
    def __init__(self):
        """Инициализирует нормализатор громкости."""
        super().__init__()
        self._meter = None
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        """
        Определяет, включена ли нормализация громкости в настройках.

        Args:
            settings: Настройки обработки.

        Returns:
            bool: True если нормализация включена.
        """
        return settings.normalization
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Нормализует громкость к целевому уровню LUFS.

        Args:
            audio (np.ndarray): Входной аудио сигнал (моно, float32, [-1, 1]).
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.

        Returns:
            np.ndarray: Аудио сигнал с нормализованной громкостью.
        """
        if len(audio) == 0:
            return audio
        
        target_lufs = np.clip(settings.normalization_target, -30.0, -10.0)
        
        # === 1. ИЗМЕРЕНИЕ ТЕКУЩЕЙ ГРОМКОСТИ ===
        current_lufs = self._measure_lufs(audio, sample_rate)
        
        if current_lufs < -70.0:
            logger.debug("Сигнал слишком тихий для нормализации (< -70 LUFS)")
            return audio
        
        # === 2. РАСЧЕТ УСИЛЕНИЯ ===
        gain_db = target_lufs - current_lufs
        
        max_gain_db = 20.0
        min_gain_db = -20.0
        gain_db = np.clip(gain_db, min_gain_db, max_gain_db)
        
        gain_linear = 10 ** (gain_db / 20.0)
        
        logger.debug(
            f"Громкость: {current_lufs:.1f} LUFS → {target_lufs:.1f} LUFS "
            f"(усиление: {gain_db:+.1f} дБ)"
        )
        
        # === 3. ПРИМЕНЕНИЕ УСИЛЕНИЯ ===
        processed = audio * gain_linear
        
        # === 4. TRUE PEAK LIMITING ===
        processed = self._apply_true_peak_limiting(processed, sample_rate)
        
        return processed
    
    def _measure_lufs(
        self, 
        audio: np.ndarray, 
        sample_rate: int
    ) -> float:
        """
        Измеряет LUFS с использованием библиотеки pyloudnorm.

        Args:
            audio (np.ndarray): Аудио сигнал.
            sample_rate (int): Частота дискретизации.

        Returns:
            float: Измеренный уровень LUFS.
        """
        if self._meter is None or self._meter.rate != sample_rate:
            self._meter = pyln.Meter(sample_rate)
        
        loudness = self._meter.integrated_loudness(audio)
        
        return float(loudness)
    
    def _apply_true_peak_limiting(
        self, 
        audio: np.ndarray, 
        sample_rate: int,
        target_tp: float = -1.0
    ) -> np.ndarray:
        """
        Применяет True Peak limiting для предотвращения клиппинга.

        Args:
            audio (np.ndarray): Входной сигнал.
            sample_rate (int): Частота дискретизации.
            target_tp (float, optional): Целевой True Peak уровень в dBTP.
                По умолчанию -1.0.

        Returns:
            np.ndarray: Ограниченный сигнал.
        """
        target_peak_linear = 10 ** (target_tp / 20.0)
        
        current_peak = np.abs(audio).max()
        
        if current_peak < target_peak_linear:
            return audio
        
        scale = target_peak_linear / current_peak
        
        scaled = audio * scale * 0.95
        
        threshold = target_peak_linear * 0.8
        
        processed = np.where(
            np.abs(scaled) > threshold,
            np.sign(scaled) * (
                threshold + (target_peak_linear - threshold) * 
                np.tanh((np.abs(scaled) - threshold) / (target_peak_linear - threshold))
            ),
            scaled
        )
        
        final_peak = np.abs(processed).max()
        if final_peak > target_peak_linear:
            processed = np.clip(processed, -target_peak_linear, target_peak_linear)
        
        logger.debug(
            f"True Peak limiting: {20*np.log10(current_peak):.1f} dBTP → "
            f"{20*np.log10(final_peak):.1f} dBTP (target: {target_tp:.1f} dBTP)"
        )
        
        return processed