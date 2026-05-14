import logging
import sys
import types
from collections import namedtuple
from pathlib import Path
from threading import Lock

import numpy as np
import torch
import torch.nn.functional as F

from src.processing.core.base import AudioProcessingMethod
from src.processing.core.settings import ProcessingSettings

logger = logging.getLogger(__name__)

_DF_SR = 48000  # нативный sample rate DeepFilterNet


class DeepFilterNetMethod(AudioProcessingMethod):
    """
    Speech enhancement via DeepFilterNet.
    Требует: pip install deepfilternet
    Модель скачивается автоматически при первом запуске (~30 MB).
    """

    def __init__(self, preload: bool = True):
        self._load_lock = Lock()
        self._infer_lock = Lock()
        self.model = None
        self.df_state = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # init_df ожидает директорию, в которой лежит config.ini
        self.models_dir = Path(__file__).resolve().parent / "models" / "DeepFilterNet3"

        if preload:
            self._load_model()

    @property
    def model_name(self) -> str:
        return "DeepFilterNet"

    @staticmethod
    def _patch_torchaudio_compat():
        """deepfilternet 0.5.6 импортирует torchaudio.backend.common.AudioMetaData,
        которого нет в torchaudio 2.x. Создаём заглушку до импорта df."""
        if "torchaudio.backend.common" not in sys.modules:
            _AudioMetaData = namedtuple(
                "AudioMetaData",
                ["sample_rate", "num_frames", "num_channels", "bits_per_sample", "encoding"],
            )
            _backend_common = types.ModuleType("torchaudio.backend.common")
            _backend_common.AudioMetaData = _AudioMetaData
            _backend = types.ModuleType("torchaudio.backend")
            _backend.common = _backend_common
            sys.modules.setdefault("torchaudio.backend", _backend)
            sys.modules["torchaudio.backend.common"] = _backend_common

    def _load_model(self):
        with self._load_lock:
            if self.model is not None:
                return
            self._patch_torchaudio_compat()
            try:
                from df.enhance import init_df
            except ImportError as e:
                logger.warning("DeepFilterNet: не удалось загрузить — %s", e)
                return
            logger.info("DeepFilterNet: загрузка модели из %s ...", self.models_dir)
            model, df_state, _ = init_df(model_base_dir=str(self.models_dir), log_level="ERROR")
            model = model.to(self.device)
            model.eval()
            self.model = model
            self.df_state = df_state
            logger.info("DeepFilterNet: модель загружена, sr=%d", df_state.sr())

    def warmup(self) -> None:
        self._load_model()

    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return bool(settings.ml_model and settings.ml_model_name == "DeepFilterNet")

    def _resample(self, waveform: torch.Tensor, orig_sr: int, target_sr: int) -> torch.Tensor:
        if orig_sr == target_sr:
            return waveform
        new_len = max(1, int(round(waveform.shape[-1] * target_sr / orig_sr)))
        return F.interpolate(waveform.unsqueeze(0), size=new_len, mode="linear", align_corners=False).squeeze(0)

    def process(self, audio: np.ndarray, sample_rate: int, settings: ProcessingSettings) -> np.ndarray:
        if not self.is_enabled(settings):
            return audio

        self._load_model()
        if self.model is None:
            return audio

        audio = np.asarray(audio, dtype=np.float32)
        audio = np.clip(audio, -1.0, 1.0)
        original_audio = audio.copy()
        original_length = len(audio)

        with self._infer_lock:
            with torch.inference_mode():
                self._patch_torchaudio_compat()
                from df.enhance import enhance

                waveform = torch.from_numpy(audio).unsqueeze(0)  # [1, T]

                if sample_rate != _DF_SR:
                    waveform = self._resample(waveform, sample_rate, _DF_SR)

                waveform = waveform.to(self.device)
                enhanced = enhance(self.model, self.df_state, waveform, pad=True)

                if sample_rate != _DF_SR:
                    enhanced = self._resample(enhanced.cpu(), _DF_SR, sample_rate)

                enhanced = enhanced.squeeze(0).cpu().numpy().astype(np.float32)

                if self.device.type == "cuda":
                    torch.cuda.empty_cache()

        if len(enhanced) > original_length:
            enhanced = enhanced[:original_length]
        elif len(enhanced) < original_length:
            pad = np.zeros(original_length - len(enhanced), dtype=np.float32)
            enhanced = np.concatenate([enhanced, pad])

        enhanced = np.clip(enhanced, -1.0, 1.0)

        mix = float(np.clip(getattr(settings, "ml_strength", 1.0), 0.0, 1.0))
        if mix < 1.0:
            enhanced = (1.0 - mix) * original_audio + mix * enhanced
            enhanced = np.clip(enhanced, -1.0, 1.0)

        return enhanced
