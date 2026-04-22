import numpy as np
import torch
import soundfile as sf
from pathlib import Path
from threading import Lock
import tempfile

from src.processing.core.base import AudioProcessingMethod
from src.processing.core.settings import ProcessingSettings
from speechbrain.inference.enhancement import SpectralMaskEnhancement


class MetricGANPlusMethod(AudioProcessingMethod):
    def __init__(self, preload: bool = True):
        self._load_lock = Lock()
        self._infer_lock = Lock()
        self.model = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model_dir = Path(__file__).resolve().parent / "models" / "metricgan_plus"

        if preload:
            self._load_model()

    def _load_model(self):
        with self._load_lock:
            if self.model is not None:
                return
            if not self.model_dir.exists():
                raise FileNotFoundError(f"Локальные веса модели не найдены: {self.model_dir}")

            self.model = SpectralMaskEnhancement.from_hparams(
                source=str(self.model_dir),
                savedir=str(self.model_dir),
                hparams_file="hyperparams.yaml",
                run_opts={"device": self.device}
            )

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
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                sf.write(tmp_path, audio, sample_rate)

                with torch.inference_mode():
                    noisy = self.model.load_audio(tmp_path).unsqueeze(0)
                    enhanced = self.model.enhance_batch(
                        noisy,
                        lengths=torch.tensor([1.0], device=self.device)
                    )
                
                enhanced = enhanced.squeeze().cpu().numpy().astype(np.float32)

                if len(enhanced) > len(audio):
                    enhanced = enhanced[:len(audio)]
                elif len(enhanced) < len(audio):
                    pad = np.zeros(len(audio) - len(enhanced), dtype=np.float32)
                    enhanced = np.concatenate([enhanced, pad])

                enhanced = np.clip(enhanced, -1.0, 1.0)
                return enhanced

            finally:
                Path(tmp_path).unlink(missing_ok=True)
