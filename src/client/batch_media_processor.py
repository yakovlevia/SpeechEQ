# src/client/batch_media_processor.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence
import tempfile
import subprocess

import numpy as np
import soundfile as sf

from processing.engine import ProcessingEngine, StreamInfo
from utils.media_io import read_audio_chunks, SUPPORTED_INPUT_EXTS


@dataclass(frozen=True)
class ProcessResult:
    input_path: Path
    output_audio_path: Path
    output_video_path: Path  # Новое поле для видео
    sample_rate: int
    channels: int


class BatchMediaProcessor:
    """
    Читает mp4/mkv чанками -> отправляет чанки в engine -> пишет очищенное аудио в WAV 
    -> объединяет с видео в выходной файл.
    """

    def __init__(
        self,
        engine: ProcessingEngine,
        block_size: int = 65536,
        out_subtype: str = "PCM_16",
        target_sr: Optional[int] = None,
        target_channels: Optional[int] = None,
        video_codec: str = "copy",  # Копировать видео или перекодировать
        audio_codec: str = "aac",  # Кодек для аудио в выходном видео
        audio_bitrate: str = "192k",  # Битрейт аудио
    ):
        self.engine = engine
        self.block_size = int(block_size)
        self.out_subtype = out_subtype
        self.target_sr = target_sr
        self.target_channels = target_channels
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.audio_bitrate = audio_bitrate

    def process_many(self, input_paths: Sequence[str | Path], output_dir: str | Path) -> List[ProcessResult]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: List[ProcessResult] = []
        for p in input_paths:
            results.append(self.process_one(Path(p), output_dir))
        return results

    def process_one(self, input_path: Path, output_dir: Path) -> ProcessResult:
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Получаем информацию о файле
        ext = input_path.suffix.lower()
        if ext not in SUPPORTED_INPUT_EXTS:
            raise ValueError(f"Unsupported input extension: {ext}. Supported: mp4, mkv")

        # Создаем временные файлы
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Обрабатываем аудио во временный WAV файл
            wav_path = tmp_path / f"{input_path.stem}_clean.wav"
            sr, ch = self._process_audio_to_wav(input_path, wav_path)
            
            # Создаем выходное видео с обработанным аудио
            output_video_path = output_dir / f"{input_path.stem}_clean{ext}"
            self._create_video_with_audio(input_path, wav_path, output_video_path)
            
            # Также сохраняем аудио отдельно (опционально)
            output_audio_path = output_dir / f"{input_path.stem}_clean.wav"
            if output_audio_path != wav_path:
                import shutil
                shutil.copy2(wav_path, output_audio_path)

        return ProcessResult(
            input_path=input_path,
            output_audio_path=output_audio_path,
            output_video_path=output_video_path,
            sample_rate=sr,
            channels=ch,
        )

    def _process_audio_to_wav(self, input_path: Path, wav_path: Path) -> tuple[int, int]:
        """Обрабатывает аудио и сохраняет во временный WAV файл"""
        sr, ch, chunks = read_audio_chunks(
            input_path,
            block_size=self.block_size,
            target_sr=self.target_sr,
            target_channels=self.target_channels,
        )

        stream_info = StreamInfo(sample_rate=sr, num_channels=ch)

        with sf.SoundFile(
            str(wav_path),
            mode="w",
            samplerate=sr,
            channels=ch,
            subtype=self.out_subtype,
        ) as fout:
            for y in self.engine.process_stream(chunks, stream_info):
                # soundfile ожидает (N, C)
                if y.ndim == 1:
                    y = y[:, None]
                if y.dtype != np.float32:
                    y = y.astype(np.float32, copy=False)
                fout.write(y)

        return sr, ch

    def _create_video_with_audio(self, input_video: Path, audio_wav: Path, output_video: Path) -> None:
        """
        Создает видеофайл с оригинальным видео и обработанным аудио
        """
        # Команда ffmpeg для копирования видео и замены аудио
        cmd = [
            'ffmpeg',
            '-i', str(input_video),  # Входное видео
            '-i', str(audio_wav),    # Обработанное аудио
            '-c:v', self.video_codec,  # Видеокодек
            '-c:a', self.audio_codec,  # Аудиокодек
            '-b:a', self.audio_bitrate,  # Битрейт аудио
            '-map', '0:v:0',  # Берем видео из первого потока
            '-map', '1:a:0',  # Берем аудио из второго потока
            '-shortest',  # Обрезать по самой короткой дорожке
            '-y',  # Перезаписывать без подтверждения
            str(output_video)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Video created: {output_video}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating video: {e}")
            print(f"stderr: {e.stderr}")
            raise RuntimeError(f"Failed to create video: {e}")