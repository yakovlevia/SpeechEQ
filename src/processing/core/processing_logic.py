"""
Основная логика обработки аудио.

Координирует выполнение DSP и ML методов в правильном порядке
для достижения оптимального качества звука.

Если один из методов падает с ошибкой, обработка продолжается
со следующим методом, а ошибка логируется.
"""
import numpy as np
from typing import List
from processing.core.settings import ProcessingSettings
from processing.dsp.base import DSPMethod
import logging
import traceback

logger = logging.getLogger(__name__)


class AudioProcessingLogic:
    """
    Координатор обработки аудио с поддержкой цепочки DSP и ML методов.

    Attributes:
        dsp_methods (List[DSPMethod]): Список DSP методов для обработки.
        ml_methods (List[str]): Список ML методов для обработки.
        error_stats (dict): Статистика ошибок по именам методов.
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
            ml_methods (List[str] | None): Список ML методов для обработки.
        """
        self.dsp_methods = dsp_methods
        self.ml_methods = ml_methods or []

        self.error_stats = {method.__class__.__name__: 0 for method in dsp_methods}
        for ml_method in self.ml_methods:
            self.error_stats[ml_method] = 0

    def _safe_apply_dsp_method(
        self,
        method: DSPMethod,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings,
        method_index: int
    ) -> np.ndarray:
        """
        Безопасно применяет DSP метод обработки.

        Args:
            method (DSPMethod): DSP метод для применения.
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
            method_index (int): Индекс метода в пайплайне (для логирования).

        Returns:
            np.ndarray: Обработанный аудио сигнал (или исходный в случае ошибки).
        """
        method_name = method.__class__.__name__

        try:
            if not method.is_enabled(settings):
                logger.debug(f"Метод {method_name} пропущен (отключен в настройках)")
                return audio

            original_audio = audio.copy()

            logger.debug(f"Применение {method_name}...")
            result = method.process(audio, sample_rate, settings)

            if result is None:
                logger.error(f"Метод {method_name} вернул None")
                self.error_stats[method_name] += 1
                return original_audio

            if np.any(np.isnan(result)) or np.any(np.isinf(result)):
                logger.error(f"Метод {method_name} вернул NaN/Inf значения")
                self.error_stats[method_name] += 1
                return original_audio

            return result

        except Exception as e:
            logger.error(
                f"Ошибка в методе {method_name} (индекс {method_index}): {str(e)}"
            )
            logger.debug(traceback.format_exc())
            self.error_stats[method_name] += 1

            logger.info(f"Метод {method_name} пропущен из-за ошибки, обработка продолжается")
            return audio

    def _safe_apply_ml_method(
        self,
        method_name: str,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings,
        method_index: int
    ) -> np.ndarray:
        """
        Безопасно применяет ML метод обработки.

        Args:
            method_name (str): Имя ML метода для применения.
            audio (np.ndarray): Входной аудио сигнал.
            sample_rate (int): Частота дискретизации.
            settings (ProcessingSettings): Настройки обработки.
            method_index (int): Индекс метода в пайплайне (для логирования).

        Returns:
            np.ndarray: Обработанный аудио сигнал (или исходный в случае ошибки).
        """
        try:
            original_audio = audio.copy()

            logger.debug(f"Применение ML метода {method_name}...")

            if not settings.ml_model:
                logger.debug(f"ML метод {method_name} пропущен (отключен в настройках)")
                return audio

            # Здесь будет вызов ML метода
            # result = self._call_ml_method(method_name, audio, sample_rate, settings)
            result = None

            if result is None:
                logger.error(f"ML метод {method_name} вернул None")
                self.error_stats[method_name] += 1
                return original_audio

            if np.any(np.isnan(result)) or np.any(np.isinf(result)):
                logger.error(f"ML метод {method_name} вернул NaN/Inf значения")
                self.error_stats[method_name] += 1
                return original_audio

            return result

        except Exception as e:
            logger.error(
                f"Ошибка в ML методе {method_name} (индекс {method_index}): {str(e)}"
            )
            logger.debug(traceback.format_exc())
            self.error_stats[method_name] += 1

            logger.info(f"ML метод {method_name} пропущен из-за ошибки, обработка продолжается")
            return audio

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Обрабатывает аудио сигнал с использованием настроенных методов.

        Порядок обработки (определяется порядком методов в dsp_methods и ml_methods):
        1. DSP методы (удаление гула, подавление шума, де-эссер, эквалайзер)
        2. ML методы (нейросетевое улучшение речи)
        3. Нормализация громкости

        Если какой-то метод падает, обработка продолжается со следующим,
        а ошибка логируется.

        Args:
            audio (np.ndarray): Входной аудио сигнал (float32).
            sample_rate (int): Частота дискретизации в Гц.
            settings (ProcessingSettings): Настройки обработки.

        Returns:
            np.ndarray: Обработанный аудио сигнал.

        Raises:
            ValueError: Если аудио сигнал пуст или некорректен.
        """
        if audio is None:
            raise ValueError("Аудио сигнал равен None")

        if len(audio) == 0:
            raise ValueError("Пустой аудио сигнал")

        if sample_rate <= 0:
            raise ValueError(f"Некорректная частота дискретизации: {sample_rate}")

        processed = audio.copy()

        applied_methods = []
        failed_methods = []

        # ===== DSP PIPELINE =====
        for i, dsp in enumerate(self.dsp_methods):
            method_name = dsp.__class__.__name__

            if not dsp.is_enabled(settings):
                logger.debug(f"Метод {method_name} пропущен (отключен в настройках)")
                continue

            result = self._safe_apply_dsp_method(
                dsp, processed, sample_rate, settings, i
            )

            if result is not processed:
                processed = result
                applied_methods.append(method_name)
                logger.debug(f"Метод {method_name} успешно применен")
            else:
                if self.error_stats[method_name] > 0:
                    failed_methods.append(method_name)

        # ===== ML PIPELINE =====
        for i, ml_method in enumerate(self.ml_methods):
            if not settings.ml_model:
                logger.debug(f"ML метод {ml_method} пропущен (отключен в настройках)")
                continue

            result = self._safe_apply_ml_method(
                ml_method, processed, sample_rate, settings, i
            )

            if result is not processed:
                processed = result
                applied_methods.append(ml_method)
                logger.debug(f"ML метод {ml_method} успешно применен")
            else:
                if self.error_stats[ml_method] > 0:
                    failed_methods.append(ml_method)

        if applied_methods:
            logger.debug(f"Успешно применены методы: {', '.join(applied_methods)}")

        if failed_methods:
            logger.warning(f"Методы с ошибками: {', '.join(failed_methods)}")

        errors = {name: count for name, count in self.error_stats.items() if count > 0}
        if errors:
            logger.info(f"Статистика ошибок за сессию: {errors}")

        if np.any(np.isnan(processed)):
            logger.error("Результат обработки содержит NaN значения, возвращаем исходный сигнал")
            return audio

        if np.any(np.isinf(processed)):
            logger.error("Результат обработки содержит Inf значения, возвращаем исходный сигнал")
            return audio

        return processed

    def get_error_stats(self) -> dict:
        """
        Возвращает статистику ошибок по методам.

        Returns:
            dict: Словарь с именами методов и количеством ошибок.
        """
        return dict(self.error_stats)

    def reset_error_stats(self):
        """Сбрасывает статистику ошибок."""
        for method in self.error_stats:
            self.error_stats[method] = 0
        logger.info("Статистика ошибок сброшена")