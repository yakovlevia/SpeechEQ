# src/processing/settings.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from processing.methods.base import AudioMethod
from processing.methods.dehum_notch import DeHumNotch


@dataclass(frozen=True)
class ProcessingSettings:
    """
    Только включение/выключение методов.
    Параметров методов тут нет.

    На будущее добавишь флаги под другие DSP и ML:
      - noise_reduction
      - deesser
      - speech_eq
      - loudness_normalization
      - ml_model
    """
    dehum_notch: bool = True
    # пример задела под будущее:
    ml_model: bool = False


def build_methods(settings: ProcessingSettings) -> List[AudioMethod]:
    """
    settings -> список методов.
    Важно: возвращаем НОВЫЕ инстансы методов (stateful) на каждый запуск/сессию.
    """
    methods: List[AudioMethod] = []

    if settings.dehum_notch:
        # Параметры фиксированные внутри метода (или дефолты)
        methods.append(DeHumNotch())  # base_freq=50, harmonics=4, q=35 по умолчанию

    # if settings.ml_model:
    #     methods.append(SomeMLMethod(...))  # потом

    return methods
