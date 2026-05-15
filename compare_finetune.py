"""
Сравнение pretrain / finetune весов для MossFormerGAN_SE_16K или FRCRN_SE_16K.

Запуск:
  python compare_finetune.py --network mossformer \
      --scp examples/pairs.scp \
      --pretrain src/processing/ml/models/MossFormerGAN_SE_16K.pt \
      --finetune  /path/to/finetuned.pt

  python compare_finetune.py --network frcrn \
      --scp examples/pairs.scp \
      --pretrain src/processing/ml/models/FRCRN_SE_16K.pt \
      --finetune  /path/to/finetuned.pt

Формат .scp-файла (одна пара на строку, разделитель — пробел):
  /path/to/noisy_1.wav /path/to/clean_1.wav
  /path/to/noisy_2.wav /path/to/clean_2.wav
"""

import argparse
import importlib
import sys
from pathlib import Path, PureWindowsPath

import numpy as np
import soundfile as sf

sys.path.insert(0, ".")

SAMPLE_RATE = 16000

NETWORK_REGISTRY = {
    "mossformer": {
        "cls_path": "src.processing.ml.mossformer_gan_se_16k",
        "cls_name": "MossFormerGANSE16KMethod",
        "model_name": "MossFormerGAN_SE_16K",
    },
    "frcrn": {
        "cls_path": "src.processing.ml.frcrn_se_16k",
        "cls_name": "FRCRNSE16KMethod",
        "model_name": "FRCRN_SE_16K",
    },
}


# ─── Метрики (идентичны evaluate_models.py) ───────────────────────────────────

def find_delay(reference: np.ndarray, estimated: np.ndarray) -> int:
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
    delay = find_delay(reference, estimated)
    n = len(reference)
    if delay > 0:
        aligned = estimated[delay:]
    elif delay < 0:
        aligned = np.concatenate([np.zeros(-delay, dtype=np.float32), estimated])
    else:
        aligned = estimated
    if len(aligned) >= n:
        return aligned[:n].astype(np.float32)
    return np.concatenate([aligned, np.zeros(n - len(aligned), dtype=np.float32)]).astype(np.float32)


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


def compute_metrics(clean: np.ndarray, audio: np.ndarray, sr: int) -> dict:
    audio = sanitize(audio)
    audio = compensate_delay(clean, audio)
    return {
        "pesq":   compute_pesq(clean, audio, sr),
        "stoi":   compute_stoi(clean, audio, sr),
        "si_sdr": si_sdr(clean, audio),
    }


def avg(scores: list[dict]) -> dict:
    keys = scores[0].keys()
    result = {}
    for k in keys:
        vals = [s[k] for s in scores if s[k] == s[k]]
        result[k] = float(np.mean(vals)) if vals else float("nan")
    return result


# ─── Файлы ────────────────────────────────────────────────────────────────────

def _to_path(raw: str) -> Path:
    """Конвертирует Windows- или Unix-путь в Path."""
    raw = raw.strip()
    if "\\" in raw:
        # Windows-путь: конвертируем через PureWindowsPath
        p = PureWindowsPath(raw)
        # Убираем букву диска, оставляем остаток как Unix-путь
        return Path(*p.parts[1:]) if p.drive else Path(*p.parts)
    return Path(raw)


def load_scp(scp_path: Path) -> list[tuple[Path, Path]]:
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
            pairs.append((noisy, clean))
    return pairs


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return audio, sr


# ─── Модель ───────────────────────────────────────────────────────────────────

def load_model_with_weights(network: str, weights_path: Path):
    """Создаёт экземпляр модели и загружает веса из указанного .pt файла."""
    from src.processing.core.settings import ProcessingSettings

    info = NETWORK_REGISTRY[network]
    module = importlib.import_module(info["cls_path"])
    cls = getattr(module, info["cls_name"])

    method = cls(preload=False)
    method.model_path = weights_path
    method._load_model()

    settings = ProcessingSettings(ml_model_name=info["model_name"], ml_strength=1.0)
    return method, settings


# ─── Таблица ──────────────────────────────────────────────────────────────────

def print_table(baseline: dict, rows: list[tuple[str, dict]]):
    col = 18

    header = (
        f"{'Модель':<{col}}"
        f"  {'PESQ до':>7} {'после':>6} {'Δ':>6}"
        f"  {'STOI до':>7} {'после':>6} {'Δ':>6}"
        f"  {'SI-SDR до':>9} {'после':>7} {'Δ':>7}"
    )
    sep = "─" * len(header)

    def fv(v: float, fmt: str) -> str:
        return "  n/a" if v != v else format(v, fmt)

    def delta(d: float, fmt: str) -> str:
        return "  n/a" if d != d else format(d, fmt)

    print(f"\n{sep}")
    print(header)
    print(sep)

    b = baseline
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
            f"  {fv(b['pesq'],   '7.2f')} {fv(m['pesq'],   '6.2f')} {delta(dp, '+.2f'):>6}"
            f"  {fv(b['stoi'],   '7.3f')} {fv(m['stoi'],   '6.3f')} {delta(ds, '+.3f'):>6}"
            f"  {fv(b['si_sdr'], '9.2f')} {fv(m['si_sdr'], '7.2f')} {delta(dd, '+.2f'):>7}"
        )

    print(sep)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Сравнение pretrain / finetune для MossFormerGAN или FRCRN"
    )
    parser.add_argument(
        "--network", required=True, choices=list(NETWORK_REGISTRY.keys()),
        help="Архитектура модели: mossformer | frcrn"
    )
    parser.add_argument(
        "--scp", type=Path, default=Path("examples/pairs.scp"),
        help="Путь к .scp-файлу с парами noisy/clean (default: examples/pairs.scp)"
    )
    parser.add_argument(
        "--pretrain", required=True, type=Path,
        help="Путь к pretrain .pt файлу"
    )
    parser.add_argument(
        "--finetune", required=True, type=Path,
        help="Путь к finetune .pt файлу"
    )
    parser.add_argument(
        "--max-pairs", type=int, default=None,
        help="Ограничить число пар (для быстрой проверки)"
    )
    args = parser.parse_args()

    for p, name in [(args.scp, "--scp"), (args.pretrain, "--pretrain"), (args.finetune, "--finetune")]:
        if not p.exists():
            print(f"Файл не найден: {p} ({name})")
            sys.exit(1)

    print(f"Читаю пары из {args.scp}...")
    pairs = load_scp(args.scp)
    if not pairs:
        print("Не найдено ни одной валидной пары.")
        sys.exit(1)

    if args.max_pairs:
        pairs = pairs[:args.max_pairs]

    print(f"Пар для оценки: {len(pairs)}")

    # Загрузка аудио
    clean_list, noisy_list = [], []
    for noisy_path, clean_path in pairs:
        clean, sr = load_wav(clean_path)
        noisy, _  = load_wav(noisy_path)
        assert sr == SAMPLE_RATE, f"Ожидается {SAMPLE_RATE} Гц, получен {sr} ({noisy_path})"
        clean_list.append(clean)
        noisy_list.append(noisy)

    # Базовые метрики (noisy)
    print("\nВычисление базовых метрик (noisy)...")
    noisy_scores = [compute_metrics(c, n, SAMPLE_RATE) for c, n in zip(clean_list, noisy_list)]
    baseline = avg(noisy_scores)

    model_rows = []

    for label, weights_path in [("Pretrain", args.pretrain), ("Finetune", args.finetune)]:
        print(f"\n{label}: загрузка весов из {weights_path}...")
        try:
            method, settings = load_model_with_weights(args.network, weights_path)
        except Exception as e:
            print(f"  Ошибка загрузки: {e}")
            model_rows.append((label, {"pesq": float("nan"), "stoi": float("nan"), "si_sdr": float("nan")}))
            continue

        print(f"  Обработка {len(noisy_list)} файл(ов)...")
        scores = []
        for i, (clean, noisy) in enumerate(zip(clean_list, noisy_list)):
            enhanced = method.process(noisy.copy(), SAMPLE_RATE, settings)
            score = compute_metrics(clean, enhanced, SAMPLE_RATE)
            scores.append(score)
            print(
                f"    [{i+1}/{len(noisy_list)}]"
                f"  PESQ={score['pesq']:.2f}"
                f"  STOI={score['stoi']:.3f}"
                f"  SI-SDR={score['si_sdr']:.2f} dB"
            )

        model_rows.append((label, avg(scores)))

        del method
        import gc, torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print_table(baseline, model_rows)


if __name__ == "__main__":
    main()
