import numpy as np
import torch
import soundfile as sf
from pathlib import Path
from threading import Lock
import tempfile

from processing.core.base import AudioProcessingMethod
from processing.core.settings import ProcessingSettings
from speechbrain.inference.enhancement import SpectralMaskEnhancement


class MetricGANPlusMethod(AudioProcessingMethod):
    def __init__(self):
        self._lock = Lock()
        self.model = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # Папка с локальными весами
        self.model_dir = Path(__file__).resolve().parent / "models" / "metricgan_plus"
        self._load_model()

    def _load_model(self):
        with self._lock:
            if self.model is not None:
                return
            if not self.model_dir.exists():
                raise FileNotFoundError(f"Локальные веса модели не найдены: {self.model_dir}")

            # Загружаем SpectralMaskEnhancement с локальными файлами
            self.model = SpectralMaskEnhancement.from_hparams(
                source=str(self.model_dir),
                savedir=str(self.model_dir),
                hparams_file="hyperparams.yaml",
                run_opts={"device": self.device}
            )

    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return bool(settings.ml_model)

    def process(self, audio: np.ndarray, sample_rate: int, settings: ProcessingSettings) -> np.ndarray:
        # Приведение к float32 и диапазону [-1, 1]
        audio = np.clip(audio.astype(np.float32), -1.0, 1.0)

        # Если модель выключена, возвращаем оригинал
        if not self.is_enabled(settings):
            return audio

        # Сохраняем во временный WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            sf.write(tmp_path, audio, sample_rate)

            # Загружаем аудио и добавляем батч-измерение
            noisy = self.model.load_audio(tmp_path).unsqueeze(0)
            enhanced = self.model.enhance_batch(noisy, lengths=torch.tensor([1.0], device=self.device))

            # Переводим в numpy и приводим к 1D
            enhanced = enhanced.squeeze().cpu().numpy().astype(np.float32)

            # Обрезаем или дополняем до длины исходного сигнала
            if len(enhanced) > len(audio):
                enhanced = enhanced[:len(audio)]
            elif len(enhanced) < len(audio):
                pad = np.zeros(len(audio) - len(enhanced), dtype=np.float32)
                enhanced = np.concatenate([enhanced, pad])

            # Клиппинг для безопасности
            enhanced = np.clip(enhanced, -1.0, 1.0)

            return enhanced

        finally:
            Path(tmp_path).unlink(missing_ok=True)