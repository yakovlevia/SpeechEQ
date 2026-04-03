import numpy as np
from scipy import signal
from .base import DSPMethod
from processing.core.settings import ProcessingSettings
import logging

logger = logging.getLogger(__name__)


class SpeechEQDSP(DSPMethod):
    """
    Речевой эквалайзер для улучшения разборчивости.
    
    Оптимизирован для лекций, уроков и образовательного контента.
    Применяет EQ-кривую, основанную на формантных частотах речи
    и области максимальной разборчивости.
    
    Использует каскад biquad фильтров:
    - High-pass для удаления румбла
    - Peaking EQ для коррекции формант
    - Shelving EQ для настройки тональности
    """
    
    def is_enabled(self, settings: ProcessingSettings) -> bool:
        """
        Определяет, включён ли эквалайзер в настройках.

        Args:
            settings: Настройки обработки.

        Returns:
            bool: True если эквалайзер включён.
        """
        return settings.eq
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Улучшает разборчивость речи с помощью эквализации.

        Args:
            audio (np.ndarray): Входной аудио сигнал (моно, float32, [-1, 1]).
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.

        Returns:
            np.ndarray: Аудио сигнал с улучшенной разборчивостью.
        """
        if len(audio) == 0:
            return audio
        
        eq_profile = settings.eq_profile
        
        if eq_profile == "speech_clarity":
            bands = self._get_speech_clarity_bands()
        elif eq_profile == "broadcast":
            bands = self._get_broadcast_bands()
        elif eq_profile == "presence":
            bands = self._get_presence_bands()
        else:
            logger.debug(f"Неизвестный EQ профиль '{eq_profile}', пропускаем")
            return audio
        
        processed = audio.copy()
        nyquist = sample_rate / 2
        
        for band in bands:
            filter_type = band['type']
            freq = band['freq']
            gain_db = band['gain']
            Q = band.get('Q', 1.0)
            
            if freq >= nyquist * 0.95:
                logger.debug(f"Пропускаем полосу {freq} Гц (выше Nyquist)")
                continue
            
            try:
                if filter_type == 'highpass':
                    processed = self._apply_highpass(processed, sample_rate, freq)
                elif filter_type == 'lowshelf':
                    processed = self._apply_lowshelf(processed, sample_rate, freq, gain_db, Q)
                elif filter_type == 'peaking':
                    processed = self._apply_peaking(processed, sample_rate, freq, gain_db, Q)
                elif filter_type == 'highshelf':
                    processed = self._apply_highshelf(processed, sample_rate, freq, gain_db, Q)
                else:
                    logger.warning(f"Неизвестный тип фильтра: {filter_type}")
            except Exception as e:
                logger.warning(f"Ошибка применения фильтра {filter_type} @ {freq} Гц: {e}")
                continue
        
        max_val = np.abs(processed).max()
        if max_val > 1.0:
            processed = processed / max_val
            logger.debug(f"Нормализация после EQ: {20*np.log10(max_val):.1f} dB")
        
        return processed
    
    def _get_speech_clarity_bands(self) -> list:
        """
        Возвращает параметры фильтров для профиля speech_clarity.

        Returns:
            list: Список словарей с параметрами фильтров.
        """
        return [
            {'type': 'highpass', 'freq': 80, 'gain': 0, 'Q': 0.7},
            {'type': 'lowshelf', 'freq': 150, 'gain': -2, 'Q': 0.7},
            {'type': 'peaking', 'freq': 250, 'gain': 2, 'Q': 1.0},
            {'type': 'peaking', 'freq': 800, 'gain': 1.5, 'Q': 1.2},
            {'type': 'peaking', 'freq': 2000, 'gain': 3, 'Q': 1.5},
            {'type': 'peaking', 'freq': 3500, 'gain': 4, 'Q': 2.0},
            {'type': 'peaking', 'freq': 5000, 'gain': 2, 'Q': 1.5},
            {'type': 'highshelf', 'freq': 8000, 'gain': -2, 'Q': 0.7},
        ]
    
    def _get_broadcast_bands(self) -> list:
        """
        Возвращает параметры фильтров для вещательного профиля.

        Returns:
            list: Список словарей с параметрами фильтров.
        """
        return [
            {'type': 'highpass', 'freq': 100, 'gain': 0, 'Q': 0.7},
            {'type': 'lowshelf', 'freq': 200, 'gain': -3, 'Q': 0.7},
            {'type': 'peaking', 'freq': 500, 'gain': 1, 'Q': 1.0},
            {'type': 'peaking', 'freq': 1500, 'gain': 2, 'Q': 1.2},
            {'type': 'peaking', 'freq': 3000, 'gain': 3, 'Q': 1.5},
            {'type': 'peaking', 'freq': 6000, 'gain': 1, 'Q': 1.2},
            {'type': 'highshelf', 'freq': 10000, 'gain': -1, 'Q': 0.7},
        ]
    
    def _get_presence_bands(self) -> list:
        """
        Возвращает параметры фильтров для усиленного профиля presence.

        Returns:
            list: Список словарей с параметрами фильтров.
        """
        return [
            {'type': 'highpass', 'freq': 100, 'gain': 0, 'Q': 0.7},
            {'type': 'lowshelf', 'freq': 200, 'gain': -4, 'Q': 0.7},
            {'type': 'peaking', 'freq': 300, 'gain': 1, 'Q': 0.8},
            {'type': 'peaking', 'freq': 1000, 'gain': 2, 'Q': 1.0},
            {'type': 'peaking', 'freq': 2500, 'gain': 5, 'Q': 1.8},
            {'type': 'peaking', 'freq': 4000, 'gain': 5, 'Q': 2.0},
            {'type': 'peaking', 'freq': 6000, 'gain': 2, 'Q': 1.5},
            {'type': 'highshelf', 'freq': 8000, 'gain': -3, 'Q': 0.7},
        ]
    
    def _apply_highpass(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_freq: float,
        order: int = 2
    ) -> np.ndarray:
        """
        Применяет high-pass фильтр.

        Args:
            audio (np.ndarray): Входной сигнал.
            sample_rate (int): Частота дискретизации.
            cutoff_freq (float): Частота среза.
            order (int, optional): Порядок фильтра. По умолчанию 2.

        Returns:
            np.ndarray: Отфильтрованный сигнал.
        """
        nyquist = sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        sos = signal.butter(order, normalized_cutoff, btype='high', output='sos')
        filtered = signal.sosfiltfilt(sos, audio)
        
        return filtered
    
    def _apply_lowshelf(
        self,
        audio: np.ndarray,
        sample_rate: int,
        freq: float,
        gain_db: float,
        Q: float
    ) -> np.ndarray:
        """
        Применяет low-shelf фильтр.

        Args:
            audio (np.ndarray): Входной сигнал.
            sample_rate (int): Частота дискретизации.
            freq (float): Частота полки.
            gain_db (float): Усиление в дБ.
            Q (float): Добротность.

        Returns:
            np.ndarray: Отфильтрованный сигнал.
        """
        sos = self._design_lowshelf_biquad(sample_rate, freq, gain_db, Q)
        filtered = signal.sosfilt(sos, audio)
        
        return filtered
    
    def _apply_highshelf(
        self,
        audio: np.ndarray,
        sample_rate: int,
        freq: float,
        gain_db: float,
        Q: float
    ) -> np.ndarray:
        """
        Применяет high-shelf фильтр.

        Args:
            audio (np.ndarray): Входной сигнал.
            sample_rate (int): Частота дискретизации.
            freq (float): Частота полки.
            gain_db (float): Усиление в дБ.
            Q (float): Добротность.

        Returns:
            np.ndarray: Отфильтрованный сигнал.
        """
        sos = self._design_highshelf_biquad(sample_rate, freq, gain_db, Q)
        filtered = signal.sosfilt(sos, audio)
        
        return filtered
    
    def _apply_peaking(
        self,
        audio: np.ndarray,
        sample_rate: int,
        freq: float,
        gain_db: float,
        Q: float
    ) -> np.ndarray:
        """
        Применяет peaking EQ фильтр.

        Args:
            audio (np.ndarray): Входной сигнал.
            sample_rate (int): Частота дискретизации.
            freq (float): Центральная частота.
            gain_db (float): Усиление в дБ.
            Q (float): Добротность.

        Returns:
            np.ndarray: Отфильтрованный сигнал.
        """
        sos = self._design_peaking_biquad(sample_rate, freq, gain_db, Q)
        filtered = signal.sosfilt(sos, audio)
        
        return filtered
    
    def _design_peaking_biquad(
        self,
        sample_rate: int,
        freq: float,
        gain_db: float,
        Q: float
    ) -> np.ndarray:
        """
        Проектирует biquad peaking EQ фильтр.

        Args:
            sample_rate (int): Частота дискретизации.
            freq (float): Центральная частота.
            gain_db (float): Усиление в дБ.
            Q (float): Добротность.

        Returns:
            np.ndarray: SOS коэффициенты.
        """
        A = 10 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * freq / sample_rate
        alpha = np.sin(w0) / (2.0 * Q)
        
        b0 = 1.0 + alpha * A
        b1 = -2.0 * np.cos(w0)
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * np.cos(w0)
        a2 = 1.0 - alpha / A
        
        b = np.array([b0, b1, b2]) / a0
        a = np.array([1.0, a1 / a0, a2 / a0])
        
        sos = np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])
        
        return sos
    
    def _design_lowshelf_biquad(
        self,
        sample_rate: int,
        freq: float,
        gain_db: float,
        Q: float
    ) -> np.ndarray:
        """
        Проектирует biquad low-shelf фильтр.

        Args:
            sample_rate (int): Частота дискретизации.
            freq (float): Частота полки.
            gain_db (float): Усиление в дБ.
            Q (float): Добротность.

        Returns:
            np.ndarray: SOS коэффициенты.
        """
        A = 10 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * freq / sample_rate
        alpha = np.sin(w0) / (2.0 * Q)
        
        b0 = A * ((A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 = 2 * A * ((A - 1) - (A + 1) * np.cos(w0))
        b2 = A * ((A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 = -2 * ((A - 1) + (A + 1) * np.cos(w0))
        a2 = (A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
        
        b = np.array([b0, b1, b2]) / a0
        a = np.array([1.0, a1 / a0, a2 / a0])
        
        sos = np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])
        
        return sos
    
    def _design_highshelf_biquad(
        self,
        sample_rate: int,
        freq: float,
        gain_db: float,
        Q: float
    ) -> np.ndarray:
        """
        Проектирует biquad high-shelf фильтр.

        Args:
            sample_rate (int): Частота дискретизации.
            freq (float): Частота полки.
            gain_db (float): Усиление в дБ.
            Q (float): Добротность.

        Returns:
            np.ndarray: SOS коэффициенты.
        """
        A = 10 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * freq / sample_rate
        alpha = np.sin(w0) / (2.0 * Q)
        
        b0 = A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * np.cos(w0))
        b2 = A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 = 2 * ((A - 1) - (A + 1) * np.cos(w0))
        a2 = (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
        
        b = np.array([b0, b1, b2]) / a0
        a = np.array([1.0, a1 / a0, a2 / a0])
        
        sos = np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])
        
        return sos