"""
Сравнение весов MetricGAN+ на парах clean/noisy из .scp-файла.

Сравниваются три чекпоинта:
  1. production  — src/processing/ml/models/metricgan_plus/enhance_model.ckpt
                   (ключи blstm.rnn.* / linear1.* / linear2.*)
  2+. все *.pth из --test-dir (ключи lstm.* / fc1.* / fc2.*, обёрнут в ckpt['generator'])

Метрики: PESQ (↑), STOI (↑), SI-SDR в дБ (↑).

Запуск:
  python compare_metricgan_weights.py --scp examples/pairs.scp
  python compare_metricgan_weights.py --scp examples/pairs.scp --test-dir /other/path
  python compare_metricgan_weights.py --scp examples/pairs.scp --device cpu
"""

import argparse
import os
import sys
from pathlib import Path, PureWindowsPath

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn

# ─── Ранний парсинг --device ──────────────────────────────────────────────────

def _early_device() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == "--device" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].lower()
    return "auto"

if _early_device() == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

sys.path.insert(0, ".")

SAMPLE_RATE = 16000

_N_FFT   = 512
_WIN_LEN = 512
_HOP_LEN = 256
_N_FREQ  = _N_FFT // 2 + 1  # 257


# ─── Архитектуры ─────────────────────────────────────────────────────────────

class _LearnableSigmoid(nn.Module):
    def __init__(self):
        super().__init__()
        self.slope = nn.Parameter(torch.ones(_N_FREQ))

    def forward(self, x):
        return 1.2 * torch.sigmoid(self.slope * x)


class _GeneratorProd(nn.Module):
    """Ключи: blstm.rnn.* / linear1.* / linear2.* / Learnable_sigmoid.*"""
    class _BLSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.rnn = nn.LSTM(_N_FREQ, 200, num_layers=2, bidirectional=True, batch_first=True)
        def forward(self, x):
            out, _ = self.rnn(x)
            return out

    def __init__(self):
        super().__init__()
        self.blstm = self._BLSTM()
        self.linear1 = nn.Linear(400, 300)
        self.linear2 = nn.Linear(300, _N_FREQ)
        self.Learnable_sigmoid = _LearnableSigmoid()
        self.lrelu = nn.LeakyReLU(0.3)

    def forward(self, x):
        out = self.blstm(x)
        out = self.lrelu(self.linear1(out))
        out = self.linear2(out)
        return self.Learnable_sigmoid(out)


class _GeneratorTest(nn.Module):
    """Ключи: lstm.* / fc1.* / fc2.* / Learnable_sigmoid.*"""
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(_N_FREQ, 200, num_layers=2, bidirectional=True, batch_first=True)
        self.fc1 = nn.Linear(400, 300)
        self.fc2 = nn.Linear(300, _N_FREQ)
        self.Learnable_sigmoid = _LearnableSigmoid()
        self.lrelu = nn.LeakyReLU(0.3)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.lrelu(self.fc1(out))
        out = self.fc2(out)
        return self.Learnable_sigmoid(out)


# ─── Signal processing ───────────────────────────────────────────────────────

def _get_mag_phase(wav: torch.Tensor):
    window = torch.hamming_window(_WIN_LEN, device=wav.device)
    stft = torch.stft(
        wav, _N_FFT, _HOP_LEN, _WIN_LEN, window,
        center=True, pad_mode="constant", normalized=False,
        onesided=True, return_complex=True,
    )  # [F, T]
    stft = stft.transpose(0, 1).unsqueeze(0)  # [1, T, F]
    phase = torch.angle(stft)
    mag = stft.abs().clamp(min=1e-14)
    return torch.log1p(mag), phase


def _mag_phase_to_wav(enh_log_mag: torch.Tensor, phase: torch.Tensor, length: int) -> np.ndarray:
    mag = torch.expm1(enh_log_mag)
    cpx = torch.complex(mag * torch.cos(phase), mag * torch.sin(phase)).permute(0, 2, 1)
    window = torch.hamming_window(_WIN_LEN, device=cpx.device)
    wav = torch.istft(cpx, _N_FFT, _HOP_LEN, _WIN_LEN, window,
                      center=True, normalized=False, onesided=True, length=length)
    return wav.squeeze(0).cpu().numpy().astype(np.float32)


def run_model(model: nn.Module, audio: np.ndarray, device: str) -> np.ndarray:
    audio = np.clip(audio.astype(np.float32), -1.0, 1.0)
    wav = torch.from_numpy(audio).to(device)
    with torch.inference_mode():
        log_mag, phase = _get_mag_phase(wav)
        mask = model(log_mag).clamp(min=0.05)
        enhanced = _mag_phase_to_wav(mask * log_mag, phase, length=len(audio))
    return np.clip(enhanced, -1.0, 1.0)


# ─── Загрузка чекпоинтов ─────────────────────────────────────────────────────

def load_production(device: str) -> nn.Module:
    ckpt_path = Path("src/processing/ml/models/metricgan_plus/enhance_model.ckpt")
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Production чекпоинт не найден: {ckpt_path}")
    g = _GeneratorProd()
    state = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    g.load_state_dict(state, strict=True)
    g.eval()
    return g.to(device)


def load_test_ckpt(path: Path, device: str) -> nn.Module:
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    state = ckpt["generator"]
    g = _GeneratorTest()
    g.load_state_dict(state, strict=True)
    g.eval()
    return g.to(device)


# ─── Метрики ─────────────────────────────────────────────────────────────────

def si_sdr(ref: np.ndarray, est: np.ndarray) -> float:
    ref = ref - ref.mean()
    est = est - est.mean()
    alpha = np.dot(ref, est) / (np.dot(ref, ref) + 1e-8)
    target = alpha * ref
    noise = est - target
    return float(10 * np.log10(np.dot(target, target) / (np.dot(noise, noise) + 1e-8)))


def compute_pesq(clean: np.ndarray, enhanced: np.ndarray) -> float:
    from pesq import pesq
    try:
        return float(pesq(SAMPLE_RATE, clean, enhanced, "wb"))
    except Exception:
        return float("nan")


def compute_stoi(clean: np.ndarray, enhanced: np.ndarray) -> float:
    from pystoi import stoi
    try:
        return float(stoi(clean, enhanced, SAMPLE_RATE, extended=False))
    except Exception:
        return float("nan")


def metrics(clean: np.ndarray, enhanced: np.ndarray) -> dict:
    n = len(clean)
    if len(enhanced) > n:
        enhanced = enhanced[:n]
    elif len(enhanced) < n:
        enhanced = np.concatenate([enhanced, np.zeros(n - len(enhanced), dtype=np.float32)])
    enhanced = np.nan_to_num(np.clip(enhanced, -1.0, 1.0))
    return {
        "pesq":   compute_pesq(clean, enhanced),
        "stoi":   compute_stoi(clean, enhanced),
        "si_sdr": si_sdr(clean, enhanced),
    }


def avg(scores: list[dict]) -> dict:
    keys = scores[0].keys()
    result = {}
    for k in keys:
        vals = [s[k] for s in scores if s[k] == s[k]]
        result[k] = float(np.mean(vals)) if vals else float("nan")
    return result


# ─── SCP / файлы ─────────────────────────────────────────────────────────────

def _to_path(raw: str) -> Path:
    raw = raw.strip()
    if "\\" in raw:
        if sys.platform == "win32":
            return Path(raw)
        p = PureWindowsPath(raw)
        parts = p.parts[1:] if p.drive else p.parts
        return Path(*parts)
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
                print(f"  [!] строка {lineno}: ожидается 'noisy clean', пропуск")
                continue
            noisy, clean = _to_path(parts[0]), _to_path(parts[1])
            if not noisy.exists():
                print(f"  [!] не найден: {noisy}")
                continue
            if not clean.exists():
                print(f"  [!] не найден: {clean}")
                continue
            pairs.append((clean, noisy))
    return pairs


def load_wav(path: Path) -> np.ndarray:
    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    assert sr == SAMPLE_RATE, f"Ожидается {SAMPLE_RATE} Гц, получен {sr} в {path}"
    return audio


# ─── Таблица ─────────────────────────────────────────────────────────────────

def print_table(baseline: dict, rows: list[tuple[str, dict]]):
    col = 22

    def fv(v, fmt):
        return "  n/a" if v != v else format(v, fmt)

    def dv(v, fmt):
        return "  n/a" if v != v else format(v, fmt)

    header = (
        f"{'Модель':<{col}}"
        f"  {'PESQ до':>7} {'после':>6} {'Δ':>6}"
        f"  {'STOI до':>7} {'после':>6} {'Δ':>6}"
        f"  {'SI-SDR до':>9} {'после':>7} {'Δ':>7}"
    )
    sep = "─" * len(header)
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
        print(
            f"{label:<{col}}"
            f"  {fv(b['pesq'],   '7.2f')} {fv(m['pesq'],   '6.2f')} {dv(m['pesq']  - b['pesq'],   '+.2f'):>6}"
            f"  {fv(b['stoi'],   '7.3f')} {fv(m['stoi'],   '6.3f')} {dv(m['stoi']  - b['stoi'],   '+.3f'):>6}"
            f"  {fv(b['si_sdr'], '9.2f')} {fv(m['si_sdr'], '7.2f')} {dv(m['si_sdr']- b['si_sdr'], '+.2f'):>7}"
        )

    print(sep)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Сравнение весов MetricGAN+")
    parser.add_argument("--scp", type=Path, default=Path("examples/pairs.scp"),
                        help=".scp-файл с парами (default: examples/pairs.scp)")
    parser.add_argument("--test-dir", type=Path,
                        default=Path("src/processing/ml/models/metricgan_plus"),
                        help="Папка с best_model.pth и best_model2.pth (default: src/processing/ml/models/metricgan_plus/)")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                        help="Устройство (default: auto)")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if args.device == "cpu":
        device = "cpu"
    elif args.device == "cuda":
        if not torch.cuda.is_available():
            print("[!] CUDA недоступна, используется CPU.")
            device = "cpu"
    print(f"Устройство: {device}")

    if not args.scp.exists():
        print(f"Файл не найден: {args.scp}")
        sys.exit(1)

    pairs = load_scp(args.scp)
    if not pairs:
        print("Не найдено ни одной валидной пары.")
        sys.exit(1)

    print(f"Пар: {len(pairs)}")

    clean_list = [load_wav(c) for c, _ in pairs]
    noisy_list = [load_wav(n) for _, n in pairs]

    # ─── Описание чекпоинтов для сравнения ───────────────────────────────────

    candidates = []

    # Production
    try:
        print("Загрузка: production (enhance_model.ckpt)...")
        m = load_production(device)
        candidates.append(("production", m))
    except Exception as e:
        print(f"  [!] production: {e}")

    # все *.pth из test-dir
    pth_files = sorted(args.test_dir.glob("*.pth"))
    if not pth_files:
        print(f"  [!] нет .pth файлов в {args.test_dir}")
    for path in pth_files:
        try:
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            if "generator" not in ckpt:
                print(f"  [!] {path.name}: нет ключа 'generator', пропуск")
                continue
            label = path.name
            print(f"Загрузка: {path.name}...")
            m = load_test_ckpt(path, device)
            candidates.append((label, m))
        except Exception as e:
            print(f"  [!] {path.name}: {e}")

    if not candidates:
        print("Нет ни одной загруженной модели.")
        sys.exit(1)

    # ─── Baseline ────────────────────────────────────────────────────────────

    print("\nБазовые метрики (noisy)...")
    baseline = avg([metrics(c, n) for c, n in zip(clean_list, noisy_list)])

    # ─── Прогон моделей ──────────────────────────────────────────────────────

    rows = []
    for label, model in candidates:
        print(f"\n{label}:")
        scores = []
        for i, (clean, noisy) in enumerate(zip(clean_list, noisy_list)):
            enhanced = run_model(model, noisy.copy(), device)
            s = metrics(clean, enhanced)
            scores.append(s)
            print(f"  [{i+1}/{len(noisy_list)}]  PESQ={s['pesq']:.2f}  STOI={s['stoi']:.3f}  SI-SDR={s['si_sdr']:.2f} dB")
        rows.append((label, avg(scores)))

    print_table(baseline, rows)


if __name__ == "__main__":
    main()
