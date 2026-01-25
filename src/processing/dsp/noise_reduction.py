# processing/dsp/noise_reduction.py
import numpy as np
from scipy import signal, fft
from .base import DSPMethod
from processing.core.settings import ProcessingSettings


class NoiseReductionDSP(DSPMethod):
    """
    Продвинутое шумоподавление с использованием спектрального гейтирования.
    Реализует алгоритм спектрального вычитания с адаптивным порогом.
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return settings.noise_reduction
    
    def _estimate_noise_profile(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Оценивает спектральный профиль шума."""
        # Берем первые 100 мс как эталон шума
        noise_samples = int(0.1 * sample_rate)
        if len(audio) > noise_samples:
            noise_segment = audio[:noise_samples]
        else:
            noise_segment = audio
        
        # Вычисляем спектр шума
        spectrum = np.abs(fft.rfft(noise_segment))
        return spectrum
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Применяет спектральное шумоподавление.
        
        Args:
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
        
        Returns:
            np.ndarray: Очищенный аудио сигнал.
        """
        strength = settings.noise_reduction_level
        
        if len(audio) < 1024:
            return audio
        
        # Параметры STFT
        n_fft = 2048
        hop_length = n_fft // 4
        
        # Выполняем STFT
        f, t, Zxx = signal.stft(
            audio, 
            fs=sample_rate, 
            nperseg=n_fft,
            noverlap=n_fft - hop_length
        )
        
        # Амплитуда и фаза
        magnitude = np.abs(Zxx)
        phase = np.angle(Zxx)
        
        # Оцениваем профиль шума (первые несколько кадров)
        noise_frames = min(10, magnitude.shape[1])
        noise_profile = np.median(magnitude[:, :noise_frames], axis=1)
        
        # Применяем спектральное вычитание
        beta = 2.0 * (1 - strength)  # Коэффициент oversubtraction
        magnitude_reduced = np.maximum(
            magnitude - beta * noise_profile[:, np.newaxis], 
            0.01 * magnitude
        )
        
        # Восстанавливаем сигнал
        Zxx_clean = magnitude_reduced * np.exp(1j * phase)
        _, audio_clean = signal.istft(
            Zxx_clean, 
            fs=sample_rate,
            nperseg=n_fft,
            noverlap=n_fft - hop_length
        )
        
        # Обрезаем до исходной длины
        if len(audio_clean) > len(audio):
            audio_clean = audio_clean[:len(audio)]
        elif len(audio_clean) < len(audio):
            audio_clean = np.pad(audio_clean, (0, len(audio) - len(audio_clean)))
        
        return audio_clean