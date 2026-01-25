# processing/core/processing_logic.py
import numpy as np
from typing import List
from processing.core.settings import ProcessingSettings
from processing.dsp.base import DSPMethod
import logging

logger = logging.getLogger(__name__)


class AudioProcessingLogic:
    """
    Основная логика обработки аудио.
    
    Координирует выполнение DSP методов в правильном порядке
    для достижения оптимального качества звука.
    """
    
    def __init__(
        self,
        dsp_methods: List[DSPMethod],
        ml_methods: List[str] | None = None
    ):
        """
        Инициализирует обработчик аудио.
        
        Args:
            dsp_methods (List[DSPMethod]): Список DSP методов для обработки.
            ml_methods (List[str] | None): Список ML методов (резерв).
        """
        self.dsp_methods = dsp_methods
        self.ml_methods = ml_methods or []
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Обрабатывает аудио сигнал с использованием настроенных методов.
        
        Порядок обработки:
        1. Удаление гула (если есть)
        2. Подавление шума
        3. Де-эссер
        4. Речевой эквалайзер
        5. Нормализация громкости
        
        Args:
            audio (np.ndarray): Входной аудио сигнал (float32).
            sample_rate (int): Частота дискретизации в Гц.
            settings (ProcessingSettings): Настройки обработки.
        
        Returns:
            np.ndarray: Обработанный аудио сигнал.
        
        Raises:
            ValueError: Если аудио сигнал пуст или некорректен.
            RuntimeError: Если произошла ошибка в одном из методов обработки.
        """
        if audio is None or len(audio) == 0:
            raise ValueError("Пустой аудио сигнал")
        
        if sample_rate <= 0:
            raise ValueError(f"Некорректная частота дискретизации: {sample_rate}")
        
        processed = audio.copy()
        
        # ===== DSP PIPELINE =====
        for dsp in self.dsp_methods:
            try:
                if dsp.is_enabled(settings):
                    # Логируем начало обработки
                    logger.debug(f"Применение {dsp.__class__.__name__}...")
                    processed = dsp.process(processed, sample_rate, settings)
            except Exception as e:
                raise RuntimeError(
                    f"Ошибка в методе {dsp.__class__.__name__}: {str(e)}"
                ) from e
        
        if np.any(np.isnan(processed)):
            raise RuntimeError("Результат обработки содержит NaN значения")
        
        return processed