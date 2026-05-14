"""
Бенчмарк методов очистки аудио.

Генерирует синтетический сигнал 16000 Гц моно и замеряет время
каждого метода обработки отдельно.

Запуск:
    python benchmark_processing.py
    python benchmark_processing.py --duration 30   # длительность в секундах
    python benchmark_processing.py --runs 5        # число прогонов
    python benchmark_processing.py --skip-ml       # пропустить ML модели
    python benchmark_processing.py --device cuda   # использовать GPU
    python benchmark_processing.py --device cpu    # принудительно CPU
"""

import gc
import os
import sys
import time
import argparse
import numpy as np

# ─── Ранний парсинг --device чтобы успеть до импорта torch ──────────────────

def _early_device() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == "--device" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].lower()
    return "auto"

_DEVICE_ARG = _early_device()
if _DEVICE_ARG == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

# ─── Основные импорты ────────────────────────────────────────────────────────

sys.path.insert(0, ".")

from src.processing.core.settings import ProcessingSettings
from src.processing.dsp.noise_reduction import NoiseReductionDSP
from src.processing.dsp.hum_removal import HumRemovalDSP
from src.processing.dsp.deesser import DeEsserDSP
from src.processing.dsp.speech_eq import SpeechEQDSP
from src.processing.dsp.loudness_normalization import LoudnessNormalizationDSP

SAMPLE_RATE = 16000


def detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return f"cuda ({torch.cuda.get_device_name(0)})"
    except ImportError:
        pass
    return "cpu"


def generate_audio(duration_sec: float) -> np.ndarray:
    n = int(SAMPLE_RATE * duration_sec)
    t = np.linspace(0, duration_sec, n, dtype=np.float32)

    speech = (
        0.4 * np.sin(2 * np.pi * 200 * t)
        + 0.3 * np.sin(2 * np.pi * 800 * t)
        + 0.2 * np.sin(2 * np.pi * 2200 * t)
        + 0.1 * np.sin(2 * np.pi * 3500 * t)
    )
    hum = 0.05 * np.sin(2 * np.pi * 50 * t)
    rng = np.random.default_rng(42)
    noise = 0.05 * rng.standard_normal(n).astype(np.float32)

    sibilant = np.zeros(n, dtype=np.float32)
    for start in range(int(SAMPLE_RATE * 0.5), n, int(SAMPLE_RATE * 1.5)):
        end = min(start + int(SAMPLE_RATE * 0.05), n)
        sibilant[start:end] = 0.3 * rng.standard_normal(end - start).astype(np.float32)

    audio = speech + hum + noise + sibilant
    return np.clip(audio / np.abs(audio).max(), -1.0, 1.0)


def bench(method, settings: ProcessingSettings, audio: np.ndarray, runs: int) -> dict:
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        method.process(audio.copy(), SAMPLE_RATE, settings)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    times = np.array(times)
    return {
        "min":  float(times.min()),
        "max":  float(times.max()),
        "mean": float(times.mean()),
        "std":  float(times.std()),
    }


def print_results(results: list, duration_sec: float, device: str):
    audio_ms = duration_sec * 1000
    col_w = 26
    header = (
        f"{'Method':<{col_w}} {'Min (ms)':>10} {'Mean (ms)':>10}"
        f" {'Max (ms)':>10} {'Std (ms)':>10} {'RTF':>8}"
    )
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print(f"  Audio: {duration_sec:.1f}s @ {SAMPLE_RATE} Hz mono"
          f" | Device: {device}"
          f" | RTF = processing_time / audio_duration")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)
    for name, r in results:
        rtf = r["mean"] / audio_ms
        print(
            f"{name:<{col_w}} {r['min']:>10.1f} {r['mean']:>10.1f}"
            f" {r['max']:>10.1f} {r['std']:>10.1f} {rtf:>8.3f}"
        )
    print(sep)


def unload(method):
    del method
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Бенчмарк методов очистки аудио")
    parser.add_argument("--duration", type=float, default=5.0,
                        help="Длительность аудио в секундах (default: 5)")
    parser.add_argument("--runs", type=int, default=3,
                        help="Число прогонов на каждый метод (default: 3)")
    parser.add_argument("--skip-ml", action="store_true",
                        help="Пропустить ML модели")
    parser.add_argument("--device", type=str, default="auto",
                        choices=["auto", "cpu", "cuda"],
                        help="Устройство: auto (default), cpu, cuda")
    args = parser.parse_args()

    device_label = detect_device()

    if args.device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                print("[!] CUDA недоступна. Используется CPU.")
                device_label = "cpu"
        except ImportError:
            pass

    print(f"Устройство: {device_label}")
    print(f"Генерация аудио {args.duration}с @ {SAMPLE_RATE} Гц моно...")
    audio = generate_audio(args.duration)
    print(f"  Сэмплов: {len(audio)}, dtype: {audio.dtype}, peak: {np.abs(audio).max():.4f}")
    print(f"\nЗапуск бенчмарка ({args.runs} прогонов на метод)...")

    results = []
    dsp_settings = ProcessingSettings()

    dsp_methods = [
        ("NoiseReduction", NoiseReductionDSP()),
        ("HumRemoval",     HumRemovalDSP()),
        ("DeEsser",        DeEsserDSP()),
        ("SpeechEQ",       SpeechEQDSP()),
        ("LoudnessNorm",   LoudnessNormalizationDSP()),
    ]

    for name, method in dsp_methods:
        print(f"  {name}...")
        results.append((name, bench(method, dsp_settings, audio, args.runs)))

    if not args.skip_ml:
        from src.processing.ml.metricgan_plus import MetricGANPlusMethod
        from src.processing.ml.frcrn_se_16k import FRCRNSE16KMethod
        from src.processing.ml.mossformer_gan_se_16k import MossFormerGANSE16KMethod
        from src.processing.ml.deepfilternet_method import DeepFilterNetMethod

        ml_candidates = [
            ("MetricGAN+",        MetricGANPlusMethod,      "metricgan_plus"),
            ("FRCRN_SE_16K",      FRCRNSE16KMethod,         "FRCRN_SE_16K"),
            ("MossFormerGAN_16K", MossFormerGANSE16KMethod, "MossFormerGAN_SE_16K"),
            ("DeepFilterNet",     DeepFilterNetMethod,      "DeepFilterNet"),
        ]

        for name, cls, model_name in ml_candidates:
            method = None
            print(f"  {name} (загрузка модели)...")
            try:
                method = cls(preload=True)
                settings = ProcessingSettings(ml_model_name=model_name)
                print(f"  {name} (замер)...")
                results.append((name, bench(method, settings, audio, args.runs)))
            except Exception as e:
                print(f"  {name} ПРОПУСК: {e}")
            finally:
                unload(method)

    print_results(results, args.duration, device_label)


if __name__ == "__main__":
    main()
