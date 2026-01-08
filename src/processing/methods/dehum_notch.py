# src/processing/methods/dehum_notch.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from .base import AudioMethod


@dataclass
class _BiquadCoeffs:
    b0: float
    b1: float
    b2: float
    a1: float
    a2: float


def _design_notch(fs: int, f0: float, q: float) -> _BiquadCoeffs:
    """
    RBJ Audio EQ Cookbook: Notch filter
    H(z) = (b0 + b1 z^-1 + b2 z^-2) / (1 + a1 z^-1 + a2 z^-2)
    """
    w0 = 2.0 * np.pi * (f0 / fs)
    cosw0 = float(np.cos(w0))
    sinw0 = float(np.sin(w0))
    alpha = sinw0 / (2.0 * q)

    b0 = 1.0
    b1 = -2.0 * cosw0
    b2 = 1.0

    a0 = 1.0 + alpha
    a1 = -2.0 * cosw0
    a2 = 1.0 - alpha

    # normalize by a0
    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0

    return _BiquadCoeffs(b0=b0, b1=b1, b2=b2, a1=a1, a2=a2)


class _NotchBiquad:
    """
    IIR biquad (Direct Form II Transposed) со state на канал.
    Подходит для streaming чанками.
    """

    def __init__(self, coeffs: _BiquadCoeffs, num_channels: int):
        self.c = coeffs
        self.z1 = np.zeros((num_channels,), dtype=np.float32)
        self.z2 = np.zeros((num_channels,), dtype=np.float32)

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        x: float32, shape (N, C)
        returns: float32, shape (N, C)
        """
        c = self.c
        y = np.empty_like(x, dtype=np.float32)

        for n in range(x.shape[0]):
            xn = x[n]
            yn = c.b0 * xn + self.z1
            self.z1 = c.b1 * xn - c.a1 * yn + self.z2
            self.z2 = c.b2 * xn - c.a2 * yn
            y[n] = yn

        return y


class DeHumNotch(AudioMethod):
    """
    Удаление гула сети 50/60 Гц и гармоник через каскад notch-фильтров.

    base_freq: 50.0 или 60.0
    harmonics: сколько гармоник подавлять (включая базовую)
    q: добротность (обычно 20..60). Больше => уже вырез.
    """

    def __init__(self, base_freq: float = 50.0, harmonics: int = 4, q: float = 35.0):
        self.base_freq = float(base_freq)
        self.harmonics = int(harmonics)
        self.q = float(q)

        self.sample_rate: Optional[int] = None
        self.num_channels: Optional[int] = None
        self._filters: List[_NotchBiquad] = []

    def reset(self, sample_rate: int, num_channels: int) -> None:
        self.sample_rate = int(sample_rate)
        self.num_channels = int(num_channels)

        self._filters = []
        nyq = 0.5 * self.sample_rate

        for k in range(1, self.harmonics + 1):
            f0 = self.base_freq * k
            if f0 >= nyq:
                break
            coeffs = _design_notch(self.sample_rate, f0, self.q)
            self._filters.append(_NotchBiquad(coeffs, num_channels=self.num_channels))

    def process(self, chunk: np.ndarray) -> np.ndarray:
        if chunk.dtype != np.float32:
            chunk = chunk.astype(np.float32, copy=False)

        # приводим к (N, C)
        if chunk.ndim == 1:
            x = chunk[:, None]
            squeeze_back = True
        else:
            x = chunk
            squeeze_back = False

        y = x
        for f in self._filters:
            y = f.process(y)

        if squeeze_back:
            return y[:, 0]
        return y
