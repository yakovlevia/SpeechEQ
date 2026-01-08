# src/utils/media_io.py (исправленная функция get_audio_info_directly)
from __future__ import annotations

from pathlib import Path
from typing import Generator, Iterable, Optional, Tuple
import subprocess
import sys
import re

import numpy as np


SUPPORTED_INPUT_EXTS = {".mp4", ".mkv"}


def get_audio_info_directly(path: Path) -> Tuple[int, int]:
    """
    Получаем информацию об аудио напрямую через ffmpeg.
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    # Команда для получения информации (ffmpeg пишет информацию в stderr)
    cmd = [
        'ffmpeg',
        '-i', str(path),
        '-hide_banner',
        '-f', 'null',
        '-'
    ]
    
    # Запускаем и получаем stderr (там вся информация)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Please install ffmpeg first.")
    
    stderr_output = result.stderr
    
    # Ищем информацию об аудио потоке
    sample_rate = None
    channels = None
    
    # Разные паттерны для разных форматов вывода ffmpeg
    patterns = [
        # Паттерн 1: Stream #0:1(eng): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 125 kb/s (default)
        r'Stream.*Audio.* (\d+) Hz.* (\d+) channel',
        r'Stream.*Audio.* (\d+) Hz.*stereo',
        r'Stream.*Audio.* (\d+) Hz.*mono',
        
        # Паттерн 2: Audio: aac (LC), 48000 Hz, stereo, fltp, 125 kb/s
        r'Audio:.* (\d+) Hz.* (\d+) channel',
        r'Audio:.* (\d+) Hz.*stereo',
        r'Audio:.* (\d+) Hz.*mono',
        
        # Паттерн 3: Просто числа
        r'(\d+) Hz.* (\d+) channel',
        r'(\d+) Hz.*stereo',
        r'(\d+) Hz.*mono',
    ]
    
    for line in stderr_output.split('\n'):
        line_lower = line.lower()
        if 'audio' in line_lower or 'hz' in line_lower:
            # Пробуем разные паттерны
            for pattern in patterns:
                match = re.search(pattern, line_lower, re.IGNORECASE)
                if match:
                    try:
                        # Извлекаем sample rate
                        if sample_rate is None:
                            for group in match.groups():
                                if group and group.isdigit() and len(group) >= 4:  # Частота дискретизации обычно >= 8000
                                    sample_rate = int(group)
                                    break
                        
                        # Извлекаем количество каналов
                        if channels is None:
                            if 'stereo' in line_lower:
                                channels = 2
                            elif 'mono' in line_lower:
                                channels = 1
                            else:
                                # Ищем число каналов в группах
                                for group in match.groups():
                                    if group and group.isdigit() and 1 <= int(group) <= 16:
                                        channels = int(group)
                                        break
                        
                        # Если нашли оба значения, выходим
                        if sample_rate is not None and channels is not None:
                            break
                            
                    except (ValueError, AttributeError):
                        continue
            
            if sample_rate is not None and channels is not None:
                break
    
    # Если не нашли, используем значения по умолчанию
    if sample_rate is None:
        print(f"Warning: Could not detect sample rate for {path}, using default 48000 Hz")
        sample_rate = 48000
    
    if channels is None:
        print(f"Warning: Could not detect channels for {path}, using default 2 channels")
        channels = 2
    
    return sample_rate, channels


def read_audio_chunks(
    path: Path,
    block_size: int,
    target_sr: Optional[int] = None,
    target_channels: Optional[int] = None,
) -> Tuple[int, int, Iterable[np.ndarray]]:
    """
    Унифицированное чтение входа: ТОЛЬКО mp4/mkv.
    Декодирование аудио идёт через ffmpeg в raw float32 (f32le) и читается чанками.
    """
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_INPUT_EXTS:
        raise ValueError(f"Unsupported input extension: {ext}. Supported: mp4, mkv")
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Получаем информацию об аудио
    src_sr, src_ch = get_audio_info_directly(path)
    out_sr = int(target_sr) if target_sr is not None else src_sr
    out_ch = int(target_channels) if target_channels is not None else src_ch

    print(f"Processing: {path}")
    print(f"  Source: {src_sr} Hz, {src_ch} channels")
    print(f"  Target: {out_sr} Hz, {out_ch} channels")

    # Команда ffmpeg для декодирования аудио
    cmd = [
        'ffmpeg',
        '-i', str(path),
        '-f', 'f32le',          # формат вывода: raw float32 little-endian
        '-acodec', 'pcm_f32le', # кодек
        '-ac', str(out_ch),     # количество каналов
        '-ar', str(out_sr),     # частота дискретизации
        '-vn',                  # без видео
        '-hide_banner',         # скрыть баннер
        '-loglevel', 'error',   # только ошибки
        'pipe:1'                # вывод в stdout
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Please install ffmpeg first.")
    except Exception as e:
        raise RuntimeError(f"Failed to start ffmpeg for {path}: {e}")

    bytes_per_sample = 4  # float32
    frame_bytes = out_ch * bytes_per_sample
    chunk_bytes_target = block_size * frame_bytes

    def gen() -> Generator[np.ndarray, None, None]:
        leftover = b""
        
        try:
            while True:
                # Читаем данные
                try:
                    data = process.stdout.read(chunk_bytes_target)
                except (IOError, OSError):
                    data = b""
                
                if not data:
                    # EOF: отдаём хвост, кратный размеру кадра
                    if leftover:
                        usable = (len(leftover) // frame_bytes) * frame_bytes
                        if usable > 0:
                            buf = leftover[:usable]
                            arr = np.frombuffer(buf, dtype=np.float32)
                            if out_ch > 1:
                                arr = arr.reshape(-1, out_ch)
                            yield arr
                    break

                leftover += data

                while len(leftover) >= chunk_bytes_target:
                    buf = leftover[:chunk_bytes_target]
                    leftover = leftover[chunk_bytes_target:]
                    arr = np.frombuffer(buf, dtype=np.float32)
                    if out_ch > 1:
                        arr = arr.reshape(-1, out_ch)
                    yield arr
        finally:
            # Завершаем процесс
            try:
                process.stdout.close()
                process.stderr.close()
            except:
                pass
            
            # Ждем завершения
            process.wait()

    return out_sr, out_ch, gen()