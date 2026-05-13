import logging
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.processing.ml.base_clearervoice import BaseClearerVoiceMethod, _total_ram_gb
from src.processing.ml.clearervoice_models.frcrn.frcrn import FRCRN_SE_16K

logger = logging.getLogger(__name__)


class FRCRNSE16KMethod(BaseClearerVoiceMethod):
    """
    Локальный inference для FRCRN_SE_16K.

    Особенности:
    - модель грузится один раз при старте
    - использует model.inference(...), как в official decode
    - для длинного аудио использует КРУПНЫЕ сегменты
    - подробное логирование для диагностики производительности
    """

    # Кастомные ComplexConv2d не поддерживаются torchinductor — compile отключён
    _supports_compile = False

    def __init__(self, preload: bool = True):
        super().__init__(
            model_filename="FRCRN_SE_16K.pt",
            config_filename="FRCRN_SE_16K.yaml",
            preload=preload,
        )

        ram_gb = _total_ram_gb()

        if self.device.type == "cuda":
            self.max_single_pass_seconds = 120
            self.segment_window_seconds = 30
            self.segment_stride_seconds = 24
        else:
            # Ограничиваем размер сегмента по доступной RAM.
            # Промежуточные тензоры FRCRN U-Net растут линейно с длиной входа.
            if ram_gb >= 32:
                self.max_single_pass_seconds = 30
                self.segment_window_seconds = 20
                self.segment_stride_seconds = 16
            elif ram_gb >= 16:
                self.max_single_pass_seconds = 10
                self.segment_window_seconds = 8
                self.segment_stride_seconds = 6
            else:
                # ≤8 ГБ: небольшие сегменты, минимальный пик памяти
                self.max_single_pass_seconds = 5
                self.segment_window_seconds = 4
                self.segment_stride_seconds = 3

        logger.info(
            "%s initialized: device=%s, sample_rate=%d, one_time_decode_length=%d sec, "
            "max_single_pass_seconds=%d sec, segment_window_seconds=%d sec, "
            "segment_stride_seconds=%d sec",
            self.model_name,
            self.device,
            self.sample_rate,
            self.one_time_decode_length,
            self.max_single_pass_seconds,
            self.segment_window_seconds,
            self.segment_stride_seconds,
        )

    @property
    def model_name(self) -> str:
        return "FRCRN_SE_16K"

    def _build_model(self):
        args = self._get_args()
        wrapper = FRCRN_SE_16K(args)
        return wrapper.model

    def _try_setup_ort(self) -> None:
        onnx_path = self.model_path.with_suffix(".onnx")
        try:
            import onnxruntime  # noqa: F401
        except ImportError:
            logger.info("%s: onnxruntime не установлен, используем PyTorch", self.model_name)
            return
        try:
            if not onnx_path.exists():
                logger.info("%s: экспорт в ONNX → %s", self.model_name, onnx_path)

                class _InferenceWrapper(nn.Module):
                    def __init__(self, m):
                        super().__init__()
                        self.m = m
                    def forward(self, x):
                        return self.m.inference(x)

                model_cpu = self.model.cpu()
                wrapper = _InferenceWrapper(model_cpu)
                dummy = torch.zeros(1, self.sample_rate)
                torch.onnx.export(
                    wrapper, dummy, str(onnx_path),
                    input_names=["waveform"],
                    output_names=["enhanced"],
                    dynamic_axes={"waveform": {1: "length"}, "enhanced": {0: "length"}},
                    opset_version=17,
                    do_constant_folding=True,
                )
                self.model.to(self.device)
                logger.info("%s: ONNX экспорт готов", self.model_name)

            self._ort_session = self._make_ort_session(onnx_path)
            logger.info("%s: ORT сессия запущена", self.model_name)
        except Exception as e:
            logger.warning("%s: ORT недоступен, используем PyTorch: %s", self.model_name, e)
            self._ort_session = None
            if onnx_path.exists():
                onnx_path.unlink(missing_ok=True)

    def _run_model_inference(self, waveform: torch.Tensor) -> torch.Tensor:
        """Вызывает model.inference через ORT или PyTorch."""
        if self._ort_session is not None:
            np_in = waveform.cpu().numpy()
            out = self._ort_session.run(None, {"waveform": np_in})[0]
            return torch.from_numpy(out).to(self.device)
        return self.model.inference(waveform)

    def _enhance_tensor(self, waveform: torch.Tensor) -> torch.Tensor:
        start_total = time.perf_counter()

        if waveform.ndim != 2 or waveform.shape[0] != 1:
            raise ValueError(
                f"{self.model_name}: ожидается waveform формы [1, T], получено {tuple(waveform.shape)}"
            )

        original_length = waveform.shape[-1]
        _, t = waveform.shape
        input_seconds = t / float(self.sample_rate)

        effective_single_pass = min(
            self.one_time_decode_length,
            self.max_single_pass_seconds
        )

        decode_do_segment = t > int(self.sample_rate * effective_single_pass)

        logger.info(
            "%s inference started: device=%s, input_samples=%d, input_sec=%.2f, "
            "effective_single_pass=%d sec, segmented=%s",
            self.model_name,
            self.device,
            t,
            input_seconds,
            effective_single_pass,
            decode_do_segment,
        )

        if not decode_do_segment:
            logger.info(
                "%s single-pass inference started: len=%d samples (%.2f sec)",
                self.model_name,
                t,
                input_seconds,
            )

            single_start = time.perf_counter()
            outputs = self._run_model_inference(waveform)
            single_elapsed = time.perf_counter() - single_start

            if outputs.ndim == 1:
                outputs = outputs.unsqueeze(0)

            total_elapsed = time.perf_counter() - start_total
            logger.info(
                "%s single-pass inference finished in %.3f sec, output_shape=%s, total=%.3f sec",
                self.model_name,
                single_elapsed,
                tuple(outputs.shape),
                total_elapsed,
            )
            return outputs[..., :original_length]

        window = int(self.sample_rate * self.segment_window_seconds)
        stride = int(self.sample_rate * self.segment_stride_seconds)
        give_up_length = max((window - stride) // 2, 0)

        padded = waveform
        pad_added = 0

        if t < window:
            pad_added = window - t
            padded = F.pad(padded, (0, pad_added))
            logger.info(
                "%s padded short input: original=%d, pad_added=%d, new_len=%d",
                self.model_name,
                t,
                pad_added,
                padded.shape[-1],
            )
        else:
            remainder = (t - window) % stride
            if remainder != 0:
                pad_added = stride - remainder
                padded = F.pad(padded, (0, pad_added))
                logger.info(
                    "%s padded for segmentation alignment: original=%d, remainder=%d, "
                    "pad_added=%d, new_len=%d",
                    self.model_name,
                    t,
                    remainder,
                    pad_added,
                    padded.shape[-1],
                )

        _, total_len = padded.shape
        total_seconds = total_len / float(self.sample_rate)
        num_segments = max(0, ((total_len - window) // stride) + 1)

        logger.info(
            "%s segmented decode: total_len=%d samples (%.2f sec), "
            "window=%d samples (%.2f sec), stride=%d samples (%.2f sec), "
            "give_up_length=%d, num_segments=%d, pad_added=%d",
            self.model_name,
            total_len,
            total_seconds,
            window,
            window / float(self.sample_rate),
            stride,
            stride / float(self.sample_rate),
            give_up_length,
            num_segments,
            pad_added,
        )

        outputs = torch.zeros(total_len, device=self.device, dtype=torch.float32)

        current_idx = 0
        segment_idx = 0

        while current_idx + window <= total_len:
            segment_idx += 1
            seg_start_sec = current_idx / float(self.sample_rate)
            seg_end_sec = (current_idx + window) / float(self.sample_rate)

            logger.info(
                "%s segment %d/%d started: samples=[%d:%d], sec=[%.2f:%.2f]",
                self.model_name,
                segment_idx,
                num_segments,
                current_idx,
                current_idx + window,
                seg_start_sec,
                seg_end_sec,
            )

            tmp_input = padded[:, current_idx:current_idx + window]

            seg_start = time.perf_counter()
            tmp_output = self._run_model_inference(tmp_input)
            seg_elapsed = time.perf_counter() - seg_start

            if tmp_output.ndim == 2:
                tmp_output = tmp_output.squeeze(0)

            logger.info(
                "%s segment %d/%d finished in %.3f sec, output_shape=%s",
                self.model_name,
                segment_idx,
                num_segments,
                seg_elapsed,
                tuple(tmp_output.shape),
            )

            if give_up_length == 0:
                outputs[current_idx:current_idx + window] = tmp_output
            else:
                if current_idx == 0:
                    outputs[current_idx:current_idx + window - give_up_length] = tmp_output[:-give_up_length]
                elif current_idx + window >= total_len:
                    outputs[current_idx + give_up_length:current_idx + window] = tmp_output[give_up_length:]
                else:
                    outputs[current_idx + give_up_length:current_idx + window - give_up_length] = tmp_output[give_up_length:-give_up_length]

            current_idx += stride

        total_elapsed = time.perf_counter() - start_total
        logger.info(
            "%s segmented inference complete in %.3f sec",
            self.model_name,
            total_elapsed,
        )

        enhanced = outputs.unsqueeze(0)
        return enhanced[..., :original_length]
