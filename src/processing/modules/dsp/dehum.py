import numpy as np


def apply_dehum(x: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Простейший DSP пример:
    лёгкое затухание сигнала (заглушка под notch-filter)
    """
    return x * 0.98
