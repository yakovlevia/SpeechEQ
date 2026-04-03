"""
Конфигурационные параметры приложения.

Содержит настройки путей к ffmpeg, параметры очередей,
конфигурацию обработки аудио и пути к директориям.
"""

import os

# Конфигурация путей к ffmpeg
FFMPEG_CONFIG = {
    "ffmpeg_path": os.environ.get("FFMPEG_PATH", "ffmpeg"),
    "ffprobe_path": os.environ.get("FFPROBE_PATH", "ffprobe"),
}

# Конфигурация очередей
QUEUE_CONFIG = {
    "audio_queue_max_size": 500,      # Максимум параллельных сегментов
    "max_concurrent_videos": 3,       # Максимум параллельных видео
}

# Конфигурация аудио обработки
AUDIO_CONFIG = {
    "segment_duration": 30,   # длительность сегмента в секундах
    "overlap_duration": 1,    # перекрытие между сегментами в секундах
    "sample_rate": 16000,     # частота дискретизации 16 кГц
}