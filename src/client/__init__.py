"""
Пакет client - клиентская часть приложения SpeechEQ.

Содержит основные компоненты для обработки видео и аудио, управления очередью задач,
а также UI-логику и экраны приложения.
"""

from src.client.video_queue import AudioCleanupTask, PriorityTaskQueue, TaskStatus
from src.client.audio_processor import AudioSegment, AudioProcessor
from src.client.video_processor import VideoProcessor
from src.client.processing_manager import ProcessingManager
from src.processing.core.settings import ProcessingSettings
from src.client.config import FFMPEG_CONFIG, QUEUE_CONFIG, AUDIO_CONFIG
from src.client.workers.processing_worker import ProcessingWorker

from src.client.core.main_window import MainWindow
from src.client.screens.main_screen import MainScreenLogic
from src.client.screens.connection_screen import ConnectionScreenLogic, ConnectionWorker
from src.client.screens.processing_screen import ProcessingScreenLogic
from src.client.screens.progress_screen import ProgressScreenLogic

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