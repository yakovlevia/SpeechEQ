import logging
import time
import numpy as np
import torch
import torch.nn.functional as F

from src.processing.ml.base_clearervoice import BaseClearerVoiceMethod
from src.processing.ml.clearervoice_models.mossformer_gan.generator import MossFormerGAN_SE_16K

logger = logging.getLogger(__name__)


class MossFormerGANSE16KMethod(BaseClearerVoiceMethod):
    """
    Локальный inference для MossFormerGAN_SE_16K.

    - грузится один раз при старте
    - использует спектральный decode
    - режет длинный сигнал на сегменты
    - содержит подробное логирование для оценки времени
    """

    def __init__(self, preload: bool = True):
        super().__init__(
            model_filename="MossFormerGAN_SE_16K.pt",
            config_filename="MossFormerGAN_SE_16K.yaml",
            preload=preload,
        )

        if self.device.type == "cuda":
            self.max_single_pass_seconds = 10
        else:
            self.max_single_pass_seconds = 3

        logger.info(
            "%s initialized: device=%s, sample_rate=%d, decode_window=%d sec, "
            "one_time_decode_length=%d sec, max_single_pass_seconds=%d sec",
            self.model_name,
            self.device,
            self.sample_rate,
            self.decode_window,
            self.one_time_decode_length,
            self.max_single_pass_seconds,
        )

    @property
    def model_name(self) -> str:
        return "MossFormerGAN_SE_16K"

    def _build_model(self):
        args = self._get_args()
        wrapper = MossFormerGAN_SE_16K(args)
        return wrapper.model

    def _enhance_tensor(self, waveform: torch.Tensor) -> torch.Tensor:
        start_total = time.perf_counter()

        if waveform.ndim != 2 or waveform.shape[0] != 1:
            raise ValueError(
                f"{self.model_name}: ожидается waveform формы [1, T], получено {tuple(waveform.shape)}"
            )

        original_length = waveform.shape[-1]
        _, t = waveform.shape
        input_seconds = t / float(self.sample_rate)

        window = int(self.sample_rate * self.decode_window)
        stride = int(window * 0.75)

        effective_single_pass = min(
            self.one_time_decode_length,
            self.max_single_pass_seconds
        )
        decode_do_segment = t > int(self.sample_rate * effective_single_pass)

        logger.info(
            "%s inference started: device=%s, input_samples=%d, input_sec=%.2f, "
            "window=%d, stride=%d, effective_single_pass=%d sec, segmented=%s",
            self.model_name,
            self.device,
            t,
            input_seconds,
            window,
            stride,
            effective_single_pass,
            decode_do_segment,
        )

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
        elif t < window + stride:
            pad_added = window + stride - t
            padded = F.pad(padded, (0, pad_added))
            logger.info(
                "%s padded medium input: original=%d, pad_added=%d, new_len=%d",
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

        logger.info(
            "%s ready for inference: total_len=%d samples (%.2f sec), original_len=%d",
            self.model_name,
            total_len,
            total_seconds,
            t,
        )

        if decode_do_segment:
            outputs = torch.zeros(total_len, device=self.device, dtype=torch.float32)
            give_up_length = (window - stride) // 2
            current_idx = 0

            num_segments = max(0, ((total_len - window) // stride) + 1)

            logger.info(
                "%s segmented decode: num_segments=%d, give_up_length=%d",
                self.model_name,
                num_segments,
                give_up_length,
            )

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
                tmp_output = self._decode_one_audio(tmp_input).squeeze(0)
                seg_elapsed = time.perf_counter() - seg_start

                logger.info(
                    "%s segment %d/%d finished in %.3f sec, output_shape=%s",
                    self.model_name,
                    segment_idx,
                    num_segments,
                    seg_elapsed,
                    tuple(tmp_output.shape),
                )

                if current_idx == 0:
                    outputs[current_idx:current_idx + window - give_up_length] = tmp_output[:-give_up_length]
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

        logger.info(
            "%s single-pass inference started: padded_len=%d samples (%.2f sec)",
            self.model_name,
            total_len,
            total_len / float(self.sample_rate),
        )

        single_start = time.perf_counter()
        enhanced = self._decode_one_audio(padded)
        single_elapsed = time.perf_counter() - single_start

        logger.info(
            "%s single-pass inference finished in %.3f sec, output_shape=%s",
            self.model_name,
            single_elapsed,
            tuple(enhanced.shape),
        )

        total_elapsed = time.perf_counter() - start_total
        logger.info(
            "%s inference complete in %.3f sec",
            self.model_name,
            total_elapsed,
        )

        return enhanced[..., :original_length]

    def _decode_one_audio(self, inputs: torch.Tensor) -> torch.Tensor:
        decode_start = time.perf_counter()

        input_len = inputs.size(-1)

        nframe = int(np.ceil(input_len / self.win_inc))
        padded_len = nframe * self.win_inc
        padding_len = padded_len - input_len

        if padding_len > 0:
            if padding_len <= inputs.size(-1):
                inputs = torch.cat([inputs, inputs[:, :padding_len]], dim=-1)
            else:
                repeat_times = int(np.ceil(padding_len / inputs.size(-1)))
                extra = inputs.repeat(1, repeat_times)[:, :padding_len]
                inputs = torch.cat([inputs, extra], dim=-1)

        c = torch.sqrt(inputs.size(-1) / torch.sum(inputs ** 2.0, dim=-1))
        inputs = torch.transpose(inputs, 0, 1)
        inputs = torch.transpose(inputs * c, 0, 1)

        stft_start = time.perf_counter()
        inputs_spec = self._stft(inputs, center=True)
        inputs_spec = inputs_spec.to(torch.float32)
        stft_elapsed = time.perf_counter() - stft_start

        compress_start = time.perf_counter()
        inputs_spec = self._power_compress(inputs_spec).permute(0, 1, 3, 2)
        compress_elapsed = time.perf_counter() - compress_start

        model_start = time.perf_counter()
        out_list = self.model(inputs_spec)
        pred_real = out_list[0].permute(0, 1, 3, 2)
        pred_imag = out_list[1].permute(0, 1, 3, 2)
        model_elapsed = time.perf_counter() - model_start

        istft_start = time.perf_counter()
        pred_spec_uncompress = self._power_uncompress(pred_real, pred_imag).squeeze(1)
        outputs = self._istft(pred_spec_uncompress, slen=None, center=False)
        istft_elapsed = time.perf_counter() - istft_start

        outputs = outputs.squeeze(0) / c
        outputs = outputs[:input_len]

        total_elapsed = time.perf_counter() - decode_start

        logger.debug(
            "%s decode_one_audio: input_len=%d, stft=%.3f sec, compress=%.3f sec, "
            "model=%.3f sec, istft=%.3f sec, total=%.3f sec",
            self.model_name,
            input_len,
            stft_elapsed,
            compress_elapsed,
            model_elapsed,
            istft_elapsed,
            total_elapsed,
        )

        return outputs.unsqueeze(0)

    def _window_tensor(self, device: torch.device) -> torch.Tensor:
        if self.win_type == "hamming":
            return torch.hamming_window(self.win_len, periodic=False, device=device)
        if self.win_type == "hanning":
            return torch.hann_window(self.win_len, periodic=False, device=device)
        raise ValueError(f"{self.model_name}: неподдерживаемый win_type={self.win_type}")

    def _stft(self, x: torch.Tensor, center: bool = False) -> torch.Tensor:
        """
        Современный безопасный вариант:
        - используем return_complex=True
        - затем приводим к старому формату [..., 2] через view_as_real
        """
        window = self._window_tensor(x.device)

        x_complex = torch.stft(
            x,
            n_fft=self.fft_len,
            hop_length=self.win_inc,
            win_length=self.win_len,
            center=center,
            window=window,
            return_complex=True,
        )

        return torch.view_as_real(x_complex)

    def _istft(
        self,
        x: torch.Tensor,
        slen=None,
        center: bool = False,
    ) -> torch.Tensor:
        """
        Принимает:
        - либо real-view tensor [..., 2]
        - либо complex tensor
        """
        window = self._window_tensor(x.device)

        if not torch.is_complex(x):
            x = torch.view_as_complex(x.contiguous())

        return torch.istft(
            x,
            n_fft=self.fft_len,
            hop_length=self.win_inc,
            win_length=self.win_len,
            window=window,
            center=center,
            normalized=False,
            onesided=None,
            length=slen,
            return_complex=False,
        )

    def _power_compress(self, x: torch.Tensor) -> torch.Tensor:
        real = x[..., 0]
        imag = x[..., 1]
        spec = torch.complex(real, imag)
        mag = torch.abs(spec)
        phase = torch.angle(spec)
        mag = mag ** 0.3
        real_compress = mag * torch.cos(phase)
        imag_compress = mag * torch.sin(phase)
        return torch.stack([real_compress, imag_compress], dim=1)

    def _power_uncompress(self, real: torch.Tensor, imag: torch.Tensor) -> torch.Tensor:
        spec = torch.complex(real, imag)
        mag = torch.abs(spec)
        phase = torch.angle(spec)
        mag = mag ** (1.0 / 0.3)
        real_uncompress = mag * torch.cos(phase)
        imag_uncompress = mag * torch.sin(phase)
        return torch.stack([real_uncompress, imag_uncompress], dim=-1)
