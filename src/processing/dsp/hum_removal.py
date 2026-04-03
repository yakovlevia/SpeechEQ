import numpy as np
from scipy import signal
from .base import DSPMethod
from processing.core.settings import ProcessingSettings
import logging

logger = logging.getLogger(__name__)


class HumRemovalDSP(DSPMethod):
    """
    Удаление сетевого гула 50/60 Гц и его гармоник.
    
    Использует каскад режекторных фильтров для подавления
    основной частоты сетевой помехи и её гармоник до 8-го порядка.
    """
    
    HARMONICS_BY_STRENGTH = {
        'light': 2,
        'medium': 4,
        'strong': 6,
        'aggressive': 8
    }
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        """
        Определяет, включено ли удаление гула в настройках.

        Args:
            settings: Настройки обработки.

        Returns:
            bool: True если удаление гула включено.
        """
        return settings.hum_removal
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Удаляет сетевую помеху и её гармоники.

        Args:
            audio (np.ndarray): Входной аудио сигнал (моно, float32, [-1, 1]).
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.

        Returns:
            np.ndarray: Аудио сигнал без сетевой помехи.
        """
        if len(audio) == 0:
            return audio
        
        hum_freq = settings.hum_frequency
        strength = np.clip(settings.hum_removal_strength, 0.0, 1.0)
        
        # === 1. ОПРЕДЕЛЕНИЕ КОЛИЧЕСТВА ГАРМОНИК ===
        if strength < 0.3:
            num_harmonics = self.HARMONICS_BY_STRENGTH['light']
        elif strength < 0.6:
            num_harmonics = self.HARMONICS_BY_STRENGTH['medium']
        elif strength < 0.8:
            num_harmonics = self.HARMONICS_BY_STRENGTH['strong']
        else:
            num_harmonics = self.HARMONICS_BY_STRENGTH['aggressive']
        
        harmonics = [hum_freq * (i + 1) for i in range(num_harmonics)]
        
        # === 2. НАСТРОЙКА ФИЛЬТРАЦИИ ===
        nyquist = sample_rate / 2
        processed = audio.copy()
        
        if strength < 0.5:
            Q = 40.0
        else:
            Q = 25.0
        
        valid_harmonics = []
        for freq in harmonics:
            if freq < nyquist * 0.95:
                valid_harmonics.append(freq)
            else:
                break
        
        if not valid_harmonics:
            logger.warning(
                f"Sample rate {sample_rate} Гц слишком низкий для удаления гула {hum_freq} Гц"
            )
            return audio
        
        # === 3. ПРИМЕНЕНИЕ ФИЛЬТРОВ ===
        for freq in valid_harmonics:
            try:
                b, a = signal.iirnotch(freq, Q, sample_rate)
                sos = self._ba_to_sos(b, a)
                processed = signal.sosfiltfilt(sos, processed)
            except Exception as e:
                logger.warning(
                    f"Не удалось применить notch-фильтр на {freq} Гц: {e}"
                )
                continue
        
        # === 4. ДОПОЛНИТЕЛЬНАЯ ОБРАБОТКА ДЛЯ ВЫСОКОЙ СИЛЫ ===
        if strength > 0.8:
            processed = self._apply_low_frequency_cleanup(
                processed, 
                sample_rate, 
                hum_freq
            )
        
        # === 5. НОРМАЛИЗАЦИЯ ===
        original_rms = np.sqrt(np.mean(audio ** 2))
        processed_rms = np.sqrt(np.mean(processed ** 2))
        
        if processed_rms > 1e-6:
            processed = processed * (original_rms / processed_rms)
        
        max_val = np.abs(processed).max()
        if max_val > 1.0:
            processed = processed / max_val
        
        return processed
    
    def _ba_to_sos(self, b: np.ndarray, a: np.ndarray) -> np.ndarray:
        """
        Конвертирует коэффициенты b, a в формат SOS.

        Args:
            b (np.ndarray): Числитель передаточной функции.
            a (np.ndarray): Знаменатель передаточной функции.

        Returns:
            np.ndarray: Массив SOS (second-order sections).
        """
        b_norm = b / a[0]
        a_norm = a / a[0]
        
        while len(b_norm) < 3:
            b_norm = np.append(b_norm, 0.0)
        while len(a_norm) < 3:
            a_norm = np.append(a_norm, 0.0)
        
        sos = np.array([[
            b_norm[0], b_norm[1], b_norm[2],
            1.0, a_norm[1], a_norm[2]
        ]])
        
        return sos
    
    def _apply_low_frequency_cleanup(
        self, 
        audio: np.ndarray, 
        sample_rate: int, 
        hum_freq: float
    ) -> np.ndarray:
        """
        Дополнительная очистка низкочастотной области для агрессивного режима.

        Args:
            audio (np.ndarray): Входной сигнал.
            sample_rate (int): Частота дискретизации.
            hum_freq (float): Основная частота гула (50 или 60 Гц).

        Returns:
            np.ndarray: Очищенный сигнал.
        """
        cutoff_freq = hum_freq * 0.8
        nyquist = sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        if normalized_cutoff >= 0.99 or normalized_cutoff <= 0.01:
            return audio
        
        try:
            sos = signal.butter(
                2,
                normalized_cutoff,
                btype='high',
                output='sos'
            )
            
            filtered = signal.sosfiltfilt(sos, audio)
            result = 0.5 * audio + 0.5 * filtered
            
            return result
            
        except Exception as e:
            logger.warning(f"Не удалось применить low-frequency cleanup: {e}")
            return audio