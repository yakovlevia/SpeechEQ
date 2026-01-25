# src/client/__init__.py
from .video_queue import AudioCleanupTask, PriorityTaskQueue
from .audio_processor import AudioSegment, AudioProcessor
from .video_processor import VideoProcessor
from .processing_manager import ProcessingManager
from processing.core.settings import ProcessingSettings
from .config import FFMPEG_CONFIG, QUEUE_CONFIG, AUDIO_CONFIG, PATHS

__all__ = [
    'AudioCleanupTask',
    'PriorityTaskQueue',
    'AudioSegment',
    'AudioProcessor',
    'VideoProcessor',
    'ProcessingManager',
    'FFMPEG_CONFIG',
    'QUEUE_CONFIG',
    'AUDIO_CONFIG',
    'PATHS',
    "ProcessingSettings"
]