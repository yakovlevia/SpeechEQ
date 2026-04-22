import ast
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Optional

import numpy as np
import torch
import torch.nn.functional as F

from src.processing.core.base import AudioProcessingMethod
from src.processing.core.settings import ProcessingSettings

logger = logging.getLogger(__name__)


class BaseClearerVoiceMethod(AudioProcessingMethod, ABC):
    """
    Базовый класс для локального inference моделей ClearerVoice-Studio.

    Особенности:
    - eager preload модели при создании объекта
    - один общий экземпляр модели на всё приложение
    - thread-safe inference через lock
    - shape-aware загрузка checkpoint
    - ограничение single-pass для снижения нагрузки на RAM/VRAM
    """

    KEY_PREFIX_CANDIDATES = (
        "",
        "module.",
        "model.",
        "se_network.",
        "se_model.",
        "generator.",
        "network.",
    )

    def __init__(
        self,
        model_filename: str,
        config_filename: str,
        preload: bool = True,
    ):
        super().__init__()
        self._load_lock = Lock()
        self._infer_lock = Lock()
        self.model: Optional[torch.nn.Module] = None

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.base_dir = Path(__file__).resolve().parent
        self.models_dir = self.base_dir / "models"
        self.configs_dir = self.base_dir / "configs"

        self.model_path = self.models_dir / model_filename
        self.config_path = self.configs_dir / config_filename

        self.config = self._load_local_config(self.config_path)

        self.sample_rate = int(self.config.get("sampling_rate", 16000))
        self.win_len = int(self.config.get("win_len", 640))
        self.win_inc = int(self.config.get("win_inc", 320))
        self.fft_len = int(self.config.get("fft_len", 640))
        self.win_type = str(self.config.get("win_type", "hanning"))

        self.one_time_decode_length = int(
            self.config.get("one_time_decode_length", 120)
        )
        self.decode_window = int(self.config.get("decode_window", 1))

        # Безопасный лимит single-pass для десктопного/серверного использования.
        # Official config часто слишком оптимистичен для GUI/CPU.
        if self.device.type == "cuda":
            default_single_pass = min(self.one_time_decode_length, 12)
        else:
            default_single_pass = min(self.one_time_decode_length, 4)

        self.max_single_pass_seconds = int(
            self.config.get("max_single_pass_seconds", default_single_pass)
        )

        # Можно ограничить число CPU thread'ов через env
        # например SPEECHEQ_TORCH_THREADS=4
        env_threads = os.getenv("SPEECHEQ_TORCH_THREADS")
        if env_threads:
            try:
                torch.set_num_threads(max(1, int(env_threads)))
            except Exception:
                pass

        if preload:
            self._load_model()

    def is_enabled(self, settings: ProcessingSettings) -> bool:
        return bool(settings.ml_model and settings.ml_model_name == self.model_name)

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def _build_model(self) -> torch.nn.Module:
        pass

    @abstractmethod
    def _enhance_tensor(self, waveform: torch.Tensor) -> torch.Tensor:
        """
        Вход:  waveform [1, T] на self.device
        Выход: waveform [1, T']
        """
        pass

    def warmup(self) -> None:
        """Явная предзагрузка модели."""
        self._load_model()

    def _load_local_config(self, config_path: Path) -> Dict[str, Any]:
        if not config_path.exists():
            raise FileNotFoundError(f"YAML-конфиг не найден: {config_path}")

        config: Dict[str, Any] = {}

        with config_path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()

                if not line:
                    continue
                if line.startswith("#"):
                    continue
                if line.startswith("#!/"):
                    continue

                line = self._strip_inline_comment(line).strip()
                if not line or ":" not in line:
                    continue

                key, value = line.split(":", 1)
                config[key.strip()] = self._parse_scalar(value.strip())

        logger.info("Загружен локальный config %s: %s", config_path.name, config)
        return config

    def _strip_inline_comment(self, line: str) -> str:
        in_single = False
        in_double = False
        result = []

        for ch in line:
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                break
            result.append(ch)

        return "".join(result)

    def _parse_scalar(self, value: str) -> Any:
        if value == "":
            return ""

        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null":
            return None

        try:
            return ast.literal_eval(value)
        except Exception:
            pass

        try:
            if "." in value:
                return float(value)
            return int(value)
        except Exception:
            return value

    def _get_args(self) -> SimpleNamespace:
        return SimpleNamespace(
            mode=self.config.get("mode", "inference"),
            use_cuda=1 if self.device.type == "cuda" else 0,
            num_gpu=int(self.config.get("num_gpu", 1)),
            sampling_rate=self.sample_rate,
            network=self.model_name,
            checkpoint_dir=str(self.config.get("checkpoint_dir", "")),
            input_path=str(self.config.get("input_path", "")),
            output_dir=str(self.config.get("output_dir", "")),
            one_time_decode_length=self.one_time_decode_length,
            decode_window=self.decode_window,
            win_type=self.win_type,
            win_len=self.win_len,
            win_inc=self.win_inc,
            fft_len=self.fft_len,
            num_mels=int(self.config.get("num_mels", 60)),
        )

    def _load_model(self) -> None:
        with self._load_lock:
            if self.model is not None:
                return

            if not self.model_path.exists():
                raise FileNotFoundError(f"Вес модели не найден: {self.model_path}")

            logger.info("Загрузка модели %s из %s", self.model_name, self.model_path)

            model = self._build_model()
            checkpoint = torch.load(self.model_path, map_location="cpu")
            pretrained = self._extract_state_dict_recursive(checkpoint)

            model_state = model.state_dict()
            remapped = self._remap_state_dict(pretrained, model_state)

            loaded_keys = 0
            for key, tensor in remapped.items():
                if key in model_state and model_state[key].shape == tensor.shape:
                    model_state[key] = tensor
                    loaded_keys += 1

            model.load_state_dict(model_state)
            model.to(self.device)
            model.eval()

            logger.info(
                "%s: загружено %d/%d параметров",
                self.model_name,
                loaded_keys,
                len(model_state),
            )

            if loaded_keys == 0:
                sample_model_keys = list(model_state.keys())[:20]
                sample_ckpt_keys = list(pretrained.keys())[:20]
                logger.error("%s: не удалось сопоставить ни одного параметра.", self.model_name)
                logger.error("MODEL KEYS SAMPLE: %s", sample_model_keys)
                logger.error("CKPT KEYS SAMPLE: %s", sample_ckpt_keys)
                raise RuntimeError(
                    f"{self.model_name}: загружено 0 параметров из {self.model_path}. "
                    f"Checkpoint не соответствует архитектуре."
                )

            self.model = model

    def _extract_state_dict_recursive(self, obj: Any) -> Dict[str, torch.Tensor]:
        if isinstance(obj, dict):
            if obj and all(isinstance(k, str) for k in obj.keys()) and all(torch.is_tensor(v) for v in obj.values()):
                return obj

            preferred_keys = (
                "state_dict",
                "model_state_dict",
                "model",
                "net",
                "network",
                "generator",
                "se_network",
            )
            for key in preferred_keys:
                if key in obj:
                    found = self._try_extract_tensor_dict(obj[key])
                    if found is not None:
                        return found

            for _, value in obj.items():
                found = self._try_extract_tensor_dict(value)
                if found is not None:
                    return found

        raise ValueError(
            f"Не удалось извлечь state_dict из файла весов {self.model_path}"
        )

    def _try_extract_tensor_dict(self, obj: Any) -> Optional[Dict[str, torch.Tensor]]:
        try:
            return self._extract_state_dict_recursive(obj)
        except Exception:
            return None

    def _strip_known_prefixes(self, key: str) -> Iterable[str]:
        variants = {key}
        changed = True

        while changed:
            changed = False
            current = list(variants)
            for item in current:
                for prefix in self.KEY_PREFIX_CANDIDATES:
                    if prefix and item.startswith(prefix):
                        stripped = item[len(prefix):]
                        if stripped not in variants:
                            variants.add(stripped)
                            changed = True

        return variants

    def _remap_state_dict(
        self,
        pretrained: Dict[str, torch.Tensor],
        model_state: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        normalized_pretrained: Dict[str, torch.Tensor] = {}

        for ckpt_key, ckpt_tensor in pretrained.items():
            for variant in self._strip_known_prefixes(ckpt_key):
                if variant not in normalized_pretrained:
                    normalized_pretrained[variant] = ckpt_tensor

        remapped: Dict[str, torch.Tensor] = {}

        for model_key, model_tensor in model_state.items():
            candidates = set(self._strip_known_prefixes(model_key))
            candidates.add(model_key)

            for candidate in candidates:
                if candidate in normalized_pretrained:
                    tensor = normalized_pretrained[candidate]
                    if tensor.shape == model_tensor.shape:
                        remapped[model_key] = tensor
                        break

        return remapped

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        if len(audio) == 0:
            return audio

        if not self.is_enabled(settings):
            return audio

        self._load_model()

        audio = np.asarray(audio, dtype=np.float32)
        audio = np.clip(audio, -1.0, 1.0)

        original_audio = audio.copy()
        original_length = len(audio)

        # Важно: один inference за раз на модель.
        # Это не даёт нескольким gRPC-потокам одновременно раздувать память.
        with self._infer_lock:
            with torch.inference_mode():
                waveform = torch.from_numpy(audio).to(self.device).float().unsqueeze(0)

                if sample_rate != self.sample_rate:
                    waveform = self._resample_torch(
                        waveform,
                        orig_sr=sample_rate,
                        target_sr=self.sample_rate
                    )

                enhanced = self._enhance_tensor(waveform)

                if sample_rate != self.sample_rate:
                    enhanced = self._resample_torch(
                        enhanced,
                        orig_sr=self.sample_rate,
                        target_sr=sample_rate
                    )

                enhanced = enhanced.squeeze(0).detach().cpu().numpy().astype(np.float32)

                if self.device.type == "cuda":
                    torch.cuda.empty_cache()

        enhanced = self._fix_length(enhanced, original_length)
        enhanced = np.clip(enhanced, -1.0, 1.0)

        mix = float(np.clip(getattr(settings, "ml_strength", 1.0), 0.0, 1.0))
        if mix < 1.0:
            enhanced = (1.0 - mix) * original_audio + mix * enhanced
            enhanced = np.clip(enhanced, -1.0, 1.0)

        return enhanced

    def _resample_torch(
        self,
        waveform: torch.Tensor,
        orig_sr: int,
        target_sr: int
    ) -> torch.Tensor:
        if orig_sr == target_sr:
            return waveform

        old_len = waveform.shape[-1]
        new_len = max(1, int(round(old_len * target_sr / orig_sr)))

        x = waveform.unsqueeze(1)
        x = F.interpolate(x, size=new_len, mode="linear", align_corners=False)
        return x.squeeze(1)

    def _fix_length(self, audio: np.ndarray, target_len: int) -> np.ndarray:
        if len(audio) > target_len:
            return audio[:target_len]
        if len(audio) < target_len:
            pad = np.zeros(target_len - len(audio), dtype=np.float32)
            return np.concatenate([audio, pad], axis=0)
        return audio
