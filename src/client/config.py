# src/client/config.py
import os
from pathlib import Path

# Конфигурация путей к ffmpeg
FFMPEG_CONFIG = {
    "ffmpeg_path": os.environ.get("FFMPEG_PATH", "ffmpeg"),
    "ffprobe_path": os.environ.get("FFPROBE_PATH", "ffprobe"),
}

# Конфигурация очередей
QUEUE_CONFIG = {
    "audio_queue_max_size": 500,
    "max_concurrent_videos": 3,
}

# Конфигурация аудио обработки
AUDIO_CONFIG = {
    "segment_duration": 30,   # сегмент 30 секунд
    "overlap_duration": 1,    # перекрытие при нарезке 1 секунда
    "merge_overlap": 0.5,     # перекрытие при сборке аудио
    "sample_rate": 44100,     
}

# Пути к папкам
PATHS = {
    "hidden_video_dir": ".video_no_audio",  # Имя скрытой папки для видео без аудио
    "temp_dir": Path("/tmp/video_processor"),  # Временная папка
    "audio_segments_dir": "audio_segments",  # Папка для сегментов аудио
    "processed_audio_dir": "processed_audio",  # Папка для обработанного аудио
}