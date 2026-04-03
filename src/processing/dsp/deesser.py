import numpy as np
from scipy import signal
from .base import DSPMethod
from processing.core.settings import ProcessingSettings


class DeEsserDSP(DSPMethod):
    """
    Де-эссер для подавления сибилянтов (шипящих звуков).
    
    Применяет частотно-зависимую динамическую компрессию в диапазоне
    сибилянтов (5-10 кГц) с адаптивным порогом и плавной обработкой.
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        """
        Определяет, включён ли де-эссер в настройках.

        Args:
            settings: Настройки обработки.

        Returns:
            bool: True если де-эссер включён.
        """
        return settings.deesser
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Подавляет сибилянты в речевом сигнале.

        Args:
            audio (np.ndarray): Входной аудио сигнал (моно, float32, [-1, 1]).
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.

        Returns:
            np.ndarray: Аудио сигнал с уменьшенными сибилянтами.
        """
        if len(audio) == 0:
            return audio
        
        strength = np.clip(settings.deesser_strength, 0.0, 1.0)
        
        # === 1. ЧАСТОТНАЯ ФИЛЬТРАЦИЯ ===
        nyquist = sample_rate / 2
        
        if nyquist < 5000:
            return audio
        
        lowcut = min(5000 / nyquist, 0.95)
        highcut = min(10000 / nyquist, 0.99)
        
        sos_band = signal.butter(4, [lowcut, highcut], btype='band', output='sos')
        sibilant_band = signal.sosfiltfilt(sos_band, audio)
        
        # === 2. ДЕТЕКЦИЯ ОГИБАЮЩЕЙ ===
        frame_length = int(0.01 * sample_rate)
        frame_length = max(frame_length, 1)
        
        squared = sibilant_band ** 2
        rms = np.sqrt(self._moving_average(squared, frame_length))
        
        # === 3. АДАПТИВНЫЙ ПОРОГ ===
        if rms.max() < 1e-6:
            return audio
        
        median_rms = np.median(rms)
        std_rms = np.std(rms)
        threshold = median_rms + 2.0 * std_rms
        
        min_threshold = 0.01
        threshold = max(threshold, min_threshold)
        
        # === 4. РАСЧЕТ КОЭФФИЦИЕНТА ПОДАВЛЕНИЯ ===
        gain_reduction = np.ones_like(audio)
        
        above_threshold = rms > threshold
        
        if np.any(above_threshold):
            excess_db = 20 * np.log10(rms[above_threshold] / threshold + 1e-10)
            reduction_db = -strength * np.tanh(excess_db / 10.0) * 12.0
            reduction_linear = 10 ** (reduction_db / 20.0)
            gain_reduction[above_threshold] = reduction_linear
        
        # === 5. СГЛАЖИВАНИЕ С ATTACK/RELEASE ===
        attack_time = settings.deesser_attack_time
        release_time = settings.deesser_release_time
        
        attack_samples = int(attack_time * sample_rate)
        release_samples = int(release_time * sample_rate)
        
        gain_reduction_smooth = self._apply_attack_release(
            gain_reduction, 
            attack_samples, 
            release_samples
        )
        
        # === 6. ПРИМЕНЕНИЕ ОБРАБОТКИ ===
        sos_low = signal.butter(4, lowcut, btype='low', output='sos')
        low_freq = signal.sosfiltfilt(sos_low, audio)
        
        high_freq = audio - low_freq
        processed_high = high_freq * gain_reduction_smooth
        
        processed = low_freq + processed_high
        
        # === 7. НОРМАЛИЗАЦИЯ ===
        max_val = np.abs(processed).max()
        if max_val > 1.0:
            processed = processed / max_val
        
        return processed
    
    def _moving_average(self, data: np.ndarray, window_size: int) -> np.ndarray:
        """
        Вычисляет скользящее среднее с использованием cumsum.

        Args:
            data (np.ndarray): Входные данные.
            window_size (int): Размер окна.

        Returns:
            np.ndarray: Сглаженные данные.
        """
        if window_size <= 1:
            return data
        
        cumsum = np.cumsum(np.insert(data, 0, 0))
        result = (cumsum[window_size:] - cumsum[:-window_size]) / window_size
        
        pad_start = np.mean(data[:window_size])
        pad_end = np.mean(data[-window_size:])
        
        start_pad = np.full(window_size // 2, pad_start)
        end_pad = np.full(len(data) - len(result) - len(start_pad), pad_end)
        
        return np.concatenate([start_pad, result, end_pad])
    
    def _apply_attack_release(
        self, 
        envelope: np.ndarray, 
        attack_samples: int, 
        release_samples: int
    ) -> np.ndarray:
        """
        Применяет attack/release сглаживание к огибающей.

        Args:
            envelope (np.ndarray): Огибающая усиления.
            attack_samples (int): Количество сэмплов для attack.
            release_samples (int): Количество сэмплов для release.

        Returns:
            np.ndarray: Сглаженная огибающая.
        """
        smoothed = np.copy(envelope)
        
        attack_coef = 1.0 - np.exp(-1.0 / max(attack_samples, 1))
        release_coef = 1.0 - np.exp(-1.0 / max(release_samples, 1))
        
        for i in range(1, len(smoothed)):
            diff = envelope[i] - smoothed[i - 1]
            
            if diff < 0:
                smoothed[i] = smoothed[i - 1] + diff * attack_coef
            else:
                smoothed[i] = smoothed[i - 1] + diff * release_coef
        
        return smoothed