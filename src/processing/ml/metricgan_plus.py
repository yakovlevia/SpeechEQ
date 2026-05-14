import logging
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from threading import Lock

from src.processing.core.base import AudioProcessingMethod
from src.processing.core.settings import ProcessingSettings

logger = logging.getLogger(__name__)

_N_FFT = 512
_WIN_LEN = 512
_HOP_LEN = 256
_N_FREQ = _N_FFT // 2 + 1  # 257


# ─── Model ───────────────────────────────────────────────────────────────────

class _LearnableSigmoid(nn.Module):
    def __init__(self):
        super().__init__()
        self.slope = nn.Parameter(torch.ones(_N_FREQ))

    def forward(self, x):
        return 1.2 * torch.sigmoid(self.slope * x)


class _BLSTM(nn.Module):
    """Matches checkpoint key prefix blstm.rnn.*"""
    def __init__(self):
        super().__init__()
        self.rnn = nn.LSTM(_N_FREQ, 200, num_layers=2, bidirectional=True, batch_first=True)

    def forward(self, x):
        out, _ = self.rnn(x)
        return out


class _Generator(nn.Module):
    """Architecture matching speechbrain EnhancementGenerator checkpoint keys."""
    def __init__(self):
        super().__init__()
        self.blstm = _BLSTM()
        self.linear1 = nn.Linear(400, 300)
        self.linear2 = nn.Linear(300, _N_FREQ)
        self.Learnable_sigmoid = _LearnableSigmoid()
        self.lrelu = nn.LeakyReLU(0.3)

    def forward(self, x):
        out = self.blstm(x)
        out = self.lrelu(self.linear1(out))
        out = self.linear2(out)
        return self.Learnable_sigmoid(out)


# ─── Signal processing ───────────────────────────────────────────────────────

def _get_mag_phase(wav: torch.Tensor):
    """wav: [N]. Returns log-magnitude [1, T, F] and phase [1, T, F]."""
    window = torch.hamming_window(_WIN_LEN, device=wav.device)
    stft = torch.stft(
        wav, _N_FFT, _HOP_LEN, _WIN_LEN, window,
        center=True, pad_mode='constant', normalized=False,
        onesided=True, return_complex=True,
    )  # [F, T] complex
    stft = stft.transpose(0, 1).unsqueeze(0)  # [1, T, F] complex
    phase = torch.angle(stft)                               # [1, T, F]
    mag = stft.abs().clamp(min=1e-14)                      # [1, T, F]
    log_mag = torch.log1p(mag)
    return log_mag, phase


def _mag_phase_to_wav(enh_log_mag: torch.Tensor, phase: torch.Tensor, length: int) -> np.ndarray:
    """enh_log_mag, phase: [1, T, F]. Returns numpy [N]."""
    mag = torch.expm1(enh_log_mag)  # [1, T, F]
    # Reconstruct complex spectrogram
    real = mag * torch.cos(phase)   # [1, T, F]
    imag = mag * torch.sin(phase)   # [1, T, F]
    # [1, T, F] → [1, F, T]
    cpx = torch.complex(real, imag).permute(0, 2, 1)   # [1, F, T]
    window = torch.hamming_window(_WIN_LEN, device=cpx.device)
    wav = torch.istft(
        cpx, _N_FFT, _HOP_LEN, _WIN_LEN, window,
        center=True, normalized=False, onesided=True, length=length,
    )  # [1, N]
    return wav.squeeze(0).cpu().numpy().astype(np.float32)


# ─── Method ──────────────────────────────────────────────────────────────────

class MetricGANPlusMethod(AudioProcessingMethod):
    def __init__(self, preload: bool = True):
        self._load_lock = Lock()
        self._infer_lock = Lock()
        self.model: _Generator | None = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.ckpt_path = Path(__file__).resolve().parent / "models" / "metricgan_plus" / "enhance_model.ckpt"

        if preload:
            self._load_model()

    def _load_model(self):
        with self._load_lock:
            if self.model is not None:
                return
            if not self.ckpt_path.exists():
                raise FileNotFoundError(f"Веса MetricGAN+ не найдены: {self.ckpt_path}")

            g = _Generator()
            state = torch.load(self.ckpt_path, map_location="cpu", weights_only=True)
            g.load_state_dict(state, strict=True)
            g.eval()
            self.model = g.to(self.device)
            logger.info("MetricGAN+: загружено на %s", self.device)

    def warmup(self) -> None:
        self._load_model()

    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return bool(settings.ml_model and settings.ml_model_name == "metricgan_plus")

    def process(self, audio: np.ndarray, sample_rate: int, settings: ProcessingSettings) -> np.ndarray:
        audio = np.clip(audio.astype(np.float32), -1.0, 1.0)

        if not self.is_enabled(settings):
            return audio

        self._load_model()

        with self._infer_lock:
            wav = torch.from_numpy(audio).to(self.device)
            with torch.inference_mode():
                log_mag, phase = _get_mag_phase(wav)
                mask = self.model(log_mag).clamp(min=0.05)
                enh_log_mag = mask * log_mag
                enhanced = _mag_phase_to_wav(enh_log_mag, phase, length=len(audio))

        return np.clip(enhanced, -1.0, 1.0)
