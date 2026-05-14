"""
Оценка качества ML-моделей очистки речи на реальных парах clean/noisy.

Метрики:
  PESQ   — перцептуальное качество (↑ лучше, макс ≈ 4.5)
  STOI   — разборчивость речи (0–1, ↑ лучше)
  SI-SDR — шкала сигнал/шум в дБ (↑ лучше)

Запуск:
  python evaluate_models.py
  python evaluate_models.py --models frcrn deepfilternet metricgan mossformer
  python evaluate_models.py --examples examples/
  python evaluate_models.py --scp examples/pairs.scp

Режимы указания пар:
  --examples DIR   ищет clean_*.wav / noisy_*.wav в DIR/clean и DIR/noisy
  --scp FILE       читает пары из .scp-файла (одна пара на строку: "noisy clean")
                   поддерживаются Windows- и Unix-пути

Результаты сохраняются в <output>/enhanced_N.wav
  (output = <examples>/output по умолчанию, или рядом с .scp при --scp)
"""

import argparse
import os
import sys
from pathlib import Path, PureWindowsPath

import numpy as np
import soundfile as sf

# Ранний парсинг --device до импорта torch (аналогично benchmark_processing.py)
def _early_device() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == "--device" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].lower()
    return "auto"

if _early_device() == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

sys.path.insert(0, ".")

SAMPLE_RATE = 16000

MODEL_REGISTRY = {
    "frcrn": {
        "label": "FRCRN_SE_16K",
        "cls_path": "src.processing.ml.frcrn_se_16k",
        "cls_name": "FRCRNSE16KMethod",
        "model_name": "FRCRN_SE_16K",
    },
    "mossformer": {
        "label": "MossFormerGAN",
        "cls_path": "src.processing.ml.mossformer_gan_se_16k",
        "cls_name": "MossFormerGANSE16KMethod",
        "model_name": "MossFormerGAN_SE_16K",
    },
    "metricgan": {
        "label": "MetricGAN+",
        "cls_path": "src.processing.ml.metricgan_plus",
        "cls_name": "MetricGANPlusMethod",
        "model_name": "metricgan_plus",
    },
    "deepfilternet": {
        "label": "DeepFilterNet",
        "cls_path": "src.processing.ml.deepfilternet_method",
        "cls_name": "DeepFilterNetMethod",
        "model_name": "DeepFilterNet",
    },
}


# ─── Выравнивание по времени ──────────────────────────────────────────────────

def find_delay(reference: np.ndarray, estimated: np.ndarray) -> int:
    """
    Возвращает задержку estimated относительно reference в сэмплах
    (положительное = estimated запаздывает, отрицательное = опережает).
    Использует FFT кросс-корреляцию — O(n log n).
    """
    ref = reference.astype(np.float64)
    est = estimated.astype(np.float64)
    n = len(ref) + len(est)
    nfft = 1 << (n - 1).bit_length()
    cross = np.fft.irfft(
        np.conj(np.fft.rfft(ref, nfft)) * np.fft.rfft(est, nfft),
        nfft,
    )
    peak = int(np.argmax(cross))
    if peak > nfft // 2:
        peak -= nfft
    return peak


def compensate_delay(reference: np.ndarray, estimated: np.ndarray) -> np.ndarray:
    """Сдвигает estimated, чтобы устранить найденное смещение, и обрезает под длину reference."""
    delay = find_delay(reference, estimated)
    n = len(reference)
    if delay > 0:
        # estimated запаздывает: убираем первые delay сэмплов
        aligned = estimated[delay:]
    elif delay < 0:
        # estimated опережает: добавляем нули в начало
        aligned = np.concatenate([np.zeros(-delay, dtype=np.float32), estimated])
    else:
        aligned = estimated
    if len(aligned) >= n:
        return aligned[:n].astype(np.float32)
    return np.concatenate([aligned, np.zeros(n - len(aligned), dtype=np.float32)]).astype(np.float32)


# ─── Метрики ──────────────────────────────────────────────────────────────────

def si_sdr(reference: np.ndarray, estimated: np.ndarray) -> float:
    ref = reference - reference.mean()
    est = estimated - estimated.mean()
    alpha = np.dot(ref, est) / (np.dot(ref, ref) + 1e-8)
    target = alpha * ref
    noise = est - target
    return float(10 * np.log10(np.dot(target, target) / (np.dot(noise, noise) + 1e-8)))


def sanitize(audio: np.ndarray) -> np.ndarray:
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def compute_pesq(clean: np.ndarray, enhanced: np.ndarray, sr: int) -> float:
    from pesq import pesq
    try:
        return float(pesq(sr, clean, enhanced, "wb"))
    except Exception:
        return float("nan")


def compute_stoi(clean: np.ndarray, enhanced: np.ndarray, sr: int) -> float:
    from pystoi import stoi
    try:
        return float(stoi(clean, enhanced, sr, extended=False))
    except Exception:
        return float("nan")


def trim_to_ref(ref: np.ndarray, est: np.ndarray) -> np.ndarray:
    n = len(ref)
    if len(est) >= n:
        return est[:n]
    return np.concatenate([est, np.zeros(n - len(est), dtype=np.float32)])


def compute_metrics(clean: np.ndarray, audio: np.ndarray, sr: int,
                    align: bool = False) -> tuple[dict, int]:
    """
    Возвращает (метрики, задержка_в_сэмплах).
    Если align=True — сначала компенсирует временное смещение.
    """
    audio = sanitize(audio)
    delay = 0
    if align:
        delay = find_delay(clean, audio)
        audio = compensate_delay(clean, audio)
    else:
        audio = trim_to_ref(clean, audio)
    return {
        "pesq":   compute_pesq(clean, audio, sr),
        "stoi":   compute_stoi(clean, audio, sr),
        "si_sdr": si_sdr(clean, audio),
    }, delay


# ─── Файлы ────────────────────────────────────────────────────────────────────

def _to_path(raw: str) -> Path:
    """Конвертирует Windows- или Unix-путь в Path текущей платформы."""
    raw = raw.strip()
    if "\\" in raw:
        if sys.platform == "win32":
            return Path(raw)
        p = PureWindowsPath(raw)
        # Убираем букву диска (D:), оставляем остаток
        parts = p.parts[1:] if p.drive else p.parts
        return Path(*parts)
    return Path(raw)


def load_scp(scp_path: Path) -> list[tuple[Path, Path]]:
    """Читает .scp-файл и возвращает список пар (noisy, clean)."""
    pairs = []
    with scp_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                print(f"  [предупреждение] строка {lineno}: ожидается 'noisy clean', пропуск")
                continue
            noisy = _to_path(parts[0])
            clean = _to_path(parts[1])
            if not noisy.exists():
                print(f"  [предупреждение] не найден: {noisy}, пропуск")
                continue
            if not clean.exists():
                print(f"  [предупреждение] не найден: {clean}, пропуск")
                continue
            pairs.append((clean, noisy))
    return pairs


def find_pairs(examples_dir: Path) -> list[tuple[Path, Path]]:
    clean_files = sorted((examples_dir / "clean").glob("clean_*.wav"))
    pairs = []
    for c in clean_files:
        idx = c.stem[len("clean_"):]
        n = examples_dir / "noisy" / f"noisy_{idx}.wav"
        if n.exists():
            pairs.append((c, n))
        else:
            print(f"  [предупреждение] нет пары для {c.name}, пропуск")
    return pairs


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return audio, sr


# ─── Загрузка модели ──────────────────────────────────────────────────────────

def load_model(key: str):
    import importlib
    from src.processing.core.settings import ProcessingSettings

    info = MODEL_REGISTRY[key]
    module = importlib.import_module(info["cls_path"])
    cls = getattr(module, info["cls_name"])
    print(f"  Загрузка {info['label']}...")
    method = cls(preload=True)
    settings = ProcessingSettings(ml_model_name=info["model_name"], ml_strength=1.0)
    return method, settings


# ─── Таблица ──────────────────────────────────────────────────────────────────

def nan_str(v: float) -> str:
    return "n/a" if v != v else None


def print_table(baseline: dict, rows: list[tuple[str, dict]]):
    """
    baseline — средние метрики noisy.
    rows — [(label, avg_model_scores)].
    Формат: до | после | Δ для каждой метрики.
    STOI без знака у дельты.
    """
    col = 16

    # Шапка
    header = (
        f"{'Модель':<{col}}"
        f"  {'PESQ до':>7} {'после':>6} {'Δ':>6}"
        f"  {'STOI до':>7} {'после':>6} {'Δ':>6}"
        f"  {'SI-SDR до':>9} {'после':>7} {'Δ':>7}"
    )
    sep = "─" * len(header)

    def fv(v: float, fmt: str) -> str:
        return "  n/a" if v != v else format(v, fmt)

    def delta_pesq(d: float) -> str:
        return "  n/a" if d != d else f"{d:+.2f}"

    def delta_stoi(d: float) -> str:
        return "  n/a" if d != d else f"{d:+.3f}"

    def delta_sdr(d: float) -> str:
        return "  n/a" if d != d else f"{d:+.2f}"

    print(f"\n{sep}")
    print(header)
    print(sep)

    b = baseline
    # Строка baseline
    print(
        f"{'Noisy (baseline)':<{col}}"
        f"  {fv(b['pesq'],   '7.2f')} {'—':>6} {'—':>6}"
        f"  {fv(b['stoi'],   '7.3f')} {'—':>6} {'—':>6}"
        f"  {fv(b['si_sdr'], '9.2f')} {'—':>7} {'—':>7}"
    )

    for label, m in rows:
        dp = m["pesq"]   - b["pesq"]
        ds = m["stoi"]   - b["stoi"]
        dd = m["si_sdr"] - b["si_sdr"]
        print(
            f"{label:<{col}}"
            f"  {fv(b['pesq'],   '7.2f')} {fv(m['pesq'],   '6.2f')} {delta_pesq(dp):>6}"
            f"  {fv(b['stoi'],   '7.3f')} {fv(m['stoi'],   '6.3f')} {delta_stoi(ds):>6}"
            f"  {fv(b['si_sdr'], '9.2f')} {fv(m['si_sdr'], '7.2f')} {delta_sdr(dd):>7}"
        )

    print(sep)


# ─── Main ─────────────────────────────────────────────────────────────────────

def avg(scores: list[dict]) -> dict:
    keys = scores[0].keys()
    result = {}
    for k in keys:
        vals = [s[k] for s in scores if s[k] == s[k]]
        result[k] = float(np.mean(vals)) if vals else float("nan")
    return result


def main():
    parser = argparse.ArgumentParser(description="Оценка ML-моделей: PESQ / STOI / SI-SDR")
    parser.add_argument(
        "--models", nargs="+",
        choices=list(MODEL_REGISTRY.keys()),
        default=list(MODEL_REGISTRY.keys()),
        help="Модели для оценки (default: все)"
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument(
        "--examples", type=Path, default=None,
        help="Папка с clean/noisy парами (default: examples/)"
    )
    src.add_argument(
        "--scp", type=Path, default=None,
        help=".scp-файл с парами (одна строка: 'noisy clean')"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Папка для сохранения enhanced файлов (default: рядом с --examples или --scp)"
    )
    parser.add_argument(
        "--device", type=str, default="auto", choices=["auto", "cpu", "cuda"],
        help="Устройство для ML-моделей: auto (default), cpu, cuda"
    )
    args = parser.parse_args()

    import torch
    if args.device == "cuda" and not torch.cuda.is_available():
        print("[!] CUDA недоступна, используется CPU.")
    device_label = "cpu"
    if torch.cuda.is_available():
        device_label = f"cuda ({torch.cuda.get_device_name(0)})"
    print(f"Устройство: {device_label}")

    if args.scp is not None:
        if not args.scp.exists():
            print(f"Файл не найден: {args.scp}")
            sys.exit(1)
        pairs = load_scp(args.scp)
        output_root = args.output or args.scp.parent / "output"
    else:
        examples_dir = args.examples or Path("examples")
        pairs = find_pairs(examples_dir)
        output_root = args.output or examples_dir / "output"

    if not pairs:
        print("Не найдено ни одной валидной пары clean/noisy.")
        sys.exit(1)

    print(f"Найдено пар: {len(pairs)}")
    for c, n in pairs:
        print(f"  {n.name}  ←→  {c.name}")

    clean_list, noisy_list = [], []
    for c_path, n_path in pairs:
        clean, sr = load_wav(c_path)
        noisy, _ = load_wav(n_path)
        assert sr == SAMPLE_RATE, f"Ожидается {SAMPLE_RATE} Гц, получен {sr}"
        clean_list.append(clean)
        noisy_list.append(noisy)

    print("\nВычисление базовых метрик (noisy)...")
    noisy_scores = [compute_metrics(c, n, SAMPLE_RATE)[0] for c, n in zip(clean_list, noisy_list)]
    baseline = avg(noisy_scores)

    model_rows = []

    for key in args.models:
        info = MODEL_REGISTRY[key]
        label = info["label"]
        out_dir = output_root / label
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            method, settings = load_model(key)
        except Exception as e:
            print(f"  {label}: ошибка загрузки — {e}")
            nan_row = {"pesq": float("nan"), "stoi": float("nan"), "si_sdr": float("nan")}
            model_rows.append((label, nan_row))
            continue

        print(f"  {label}: обработка {len(noisy_list)} файл(ов)...")
        model_scores = []

        for i, (clean, noisy) in enumerate(zip(clean_list, noisy_list)):
            stem = pairs[i][1].stem
            idx = stem[len("noisy_"):] if stem.startswith("noisy_") else str(i + 1)
            out_name = f"enhanced_{idx}.wav"

            enhanced = method.process(noisy.copy(), SAMPLE_RATE, settings)
            sf.write(str(out_dir / out_name), enhanced, SAMPLE_RATE)

            score, delay = compute_metrics(clean, enhanced, SAMPLE_RATE, align=True)
            model_scores.append(score)

            delay_ms = delay / SAMPLE_RATE * 1000
            print(
                f"    [{i+1}/{len(noisy_list)}]"
                f"  PESQ={score['pesq']:.2f}"
                f"  STOI={score['stoi']:.3f}"
                f"  SI-SDR={score['si_sdr']:.2f} dB"
                f"  (смещение {delay_ms:+.1f} мс)"
            )

        model_rows.append((label, avg(model_scores)))

        del method
        import gc, torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print_table(baseline, model_rows)
    print(f"\nФайлы сохранены в {output_root}/")


if __name__ == "__main__":
    main()
