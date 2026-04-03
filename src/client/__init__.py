"""
Пакет client - клиентская часть приложения SpeechEQ.

Содержит основные компоненты для обработки видео и аудио, управления очередью задач,
а также UI-логику и экраны приложения.
"""

from .video_queue import AudioCleanupTask, PriorityTaskQueue, TaskStatus
from .audio_processor import AudioSegment, AudioProcessor
from .video_processor import VideoProcessor
from .processing_manager import ProcessingManager
from processing.core.settings import ProcessingSettings
from .config import FFMPEG_CONFIG, QUEUE_CONFIG, AUDIO_CONFIG
from .workers.processing_worker import ProcessingWorker

from .core.main_window import MainWindow
from .screens.main_screen import MainScreenLogic
from .screens.connection_screen import ConnectionScreenLogic, ConnectionWorker
from .screens.processing_screen import ProcessingScreenLogic
from .screens.progress_screen import ProgressScreenLogic

__all__ = [
    'AudioCleanupTask',
    'PriorityTaskQueue',
    'TaskStatus',
    'AudioSegment',
    'AudioProcessor',
    'VideoProcessor',
    'ProcessingManager',
    'FFMPEG_CONFIG',
    'QUEUE_CONFIG',
    'AUDIO_CONFIG',
    "ProcessingSettings",
    "MainWindow",
    "MainScreenLogic",
    "ConnectionScreenLogic",
    "ConnectionWorker",
    "ProcessingScreenLogic",
    "ProgressScreenLogic",
    "ProcessingWorker",
]