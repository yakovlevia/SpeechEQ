"""
Модуль для управления задачами обработки аудио.
Содержит классы задачи (AudioCleanupTask) и приоритетной очереди (PriorityTaskQueue).
"""
import heapq
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import asyncio
import uuid
from processing.handlers.base import AudioHandler
from processing.core.settings import ProcessingSettings
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Статусы задачи обработки видео."""
    PENDING = "pending"
    PROCESSING = "processing"
    RESUMING = "resuming"
    POST_PROCESSING = "post_processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class AudioCleanupTask:
    """
    Задача на очистку аудио из видео.

    Attributes:
        task_id (str): Уникальный идентификатор задачи.
        priority (int): Приоритет (чем меньше, тем выше).
        input_path (str): Путь к исходному видеофайлу.
        output_path (str): Путь для сохранения обработанного видео.
        handler (AudioHandler): Обработчик аудио.
        handler_settings (ProcessingSettings): Настройки обработчика.
        total_segments (int): Общее количество аудио сегментов.
        cleaned_segments (int): Количество обработанных сегментов.
        status (TaskStatus): Текущий статус.
        duration (float): Длительность видео в секундах.
        duration_formatted (str): Отформатированная длительность.
        _pause_event (asyncio.Event): Событие для приостановки.
        _cancelled (bool): Флаг отмены.
        _lock (asyncio.Lock): Блокировка для потокобезопасности.
    """

    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    priority: int = 1
    input_path: str = ""
    output_path: str = ""
    handler: Optional[AudioHandler] = None
    handler_settings: ProcessingSettings = field(default_factory=ProcessingSettings)
    total_segments: int = 0
    cleaned_segments: int = 0
    status: TaskStatus = TaskStatus.PENDING
    duration: float = 0.0
    duration_formatted: str = "--:--"

    _pause_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False, compare=False)
    _cancelled: bool = field(default=False, repr=False, compare=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)

    def __post_init__(self):
        self._pause_event.set()

    def __hash__(self) -> int:
        return hash(self.task_id)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AudioCleanupTask):
            return False
        return self.task_id == other.task_id

    def __lt__(self, other: Any) -> bool:
        """Сравнение по приоритету для heapq (меньше priority = выше приоритет)."""
        if not isinstance(other, AudioCleanupTask):
            return NotImplemented
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.task_id < other.task_id

    def format_duration(self, seconds: float) -> str:
        """Форматирует длительность в MM:SS или HH:MM:SS."""
        if seconds <= 0:
            return "--:--"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    async def set_duration(self, duration: float) -> None:
        async with self._lock:
            self.duration = duration
            self.duration_formatted = self.format_duration(duration)

    async def wait_if_paused(self) -> bool:
        async with self._lock:
            if self._cancelled:
                return False
        await self._pause_event.wait()
        async with self._lock:
            return not self._cancelled

    def is_paused(self) -> bool:
        return self.status == TaskStatus.PAUSED

    async def pause(self) -> bool:
        async with self._lock:
            if self.status not in (TaskStatus.PROCESSING, TaskStatus.POST_PROCESSING):
                logger.warning(f"Задача {self.task_id[:12]}... не в статусе PROCESSING/POST_PROCESSING: {self.status}")
                return False
            if self._cancelled:
                return False
            self.status = TaskStatus.PAUSED
            self._pause_event.clear()
            logger.info(f"Задача {self.task_id[:12]}... приостановлена")
            return True

    async def should_exit(self) -> bool:
        async with self._lock:
            return self._cancelled or self.status == TaskStatus.PAUSED

    async def resume(self) -> bool:
        async with self._lock:
            logger.info(f"resume() для задачи {self.task_id[:12]}..., статус={self.status.value}")
            if self.status != TaskStatus.PAUSED:
                logger.warning(f"Задача {self.task_id[:12]}... не приостановлена: {self.status}")
                return False
            if self._cancelled:
                logger.warning(f"Задача {self.task_id[:12]}... отменена")
                return False
            self.status = TaskStatus.RESUMING
            self._pause_event.set()
            logger.info(f"Задача {self.task_id[:12]}... возобновлена, приоритет={self.priority}")
            return True

    async def set_post_processing(self) -> bool:
        async with self._lock:
            if self.status != TaskStatus.PROCESSING:
                logger.warning(f"Задача {self.task_id[:12]}... не в PROCESSING для перехода в POST_PROCESSING")
                return False
            if self._cancelled:
                return False
            self.status = TaskStatus.POST_PROCESSING
            logger.info(f"Задача {self.task_id[:12]}... перешла в POST_PROCESSING")
            return True

    async def set_processing_from_resuming(self) -> bool:
        async with self._lock:
            if self.status != TaskStatus.RESUMING:
                logger.warning(f"Задача {self.task_id[:12]}... не в статусе RESUMING")
                return False
            self.status = TaskStatus.PROCESSING
            logger.info(f"Задача {self.task_id[:12]}... перешла из RESUMING в PROCESSING")
            return True

    async def cancel(self) -> bool:
        async with self._lock:
            if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
                return False
            self._cancelled = True
            self.status = TaskStatus.CANCELLED
            self._pause_event.set()
            return True

    def is_cancelled(self) -> bool:
        return self._cancelled

    async def increment_progress(self, segments: int = 1) -> None:
        async with self._lock:
            if self.total_segments > 0:
                self.cleaned_segments = min(self.cleaned_segments + segments, self.total_segments)
            else:
                self.cleaned_segments += segments

    async def update_progress(self, cleaned_segments: int) -> None:
        async with self._lock:
            if self.total_segments > 0:
                self.cleaned_segments = min(cleaned_segments, self.total_segments)
            else:
                self.cleaned_segments = cleaned_segments

    async def set_total_segments(self, total_segments: int) -> None:
        async with self._lock:
            self.total_segments = max(0, total_segments)
            if self.cleaned_segments > self.total_segments:
                self.cleaned_segments = self.total_segments

    async def get_progress_percentage(self) -> float:
        async with self._lock:
            if self.total_segments == 0:
                return 0.0 if self.cleaned_segments == 0 else 100.0
            return (self.cleaned_segments / self.total_segments) * 100

    async def set_status(self, status: TaskStatus) -> None:
        async with self._lock:
            self.status = status
            if status == TaskStatus.PROCESSING:
                self._pause_event.set()
            elif status == TaskStatus.PAUSED:
                self._pause_event.clear()
            elif status in (TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._cancelled = (status == TaskStatus.CANCELLED)
                self._pause_event.set()
            elif status in (TaskStatus.RESUMING, TaskStatus.POST_PROCESSING):
                self._pause_event.set()

    def get_status_sync(self) -> TaskStatus:
        return self.status

    def get_progress_sync(self) -> tuple[int, int, float]:
        if self.total_segments == 0:
            return (self.cleaned_segments, 0, 0.0)
        percent = (self.cleaned_segments / self.total_segments) * 100
        return (self.cleaned_segments, self.total_segments, percent)


class PriorityTaskQueue:
    """Приоритетная очередь для управления задачами обработки."""
    
    def __init__(self):
        self._heap = []
        self._tasks_by_id: dict[str, AudioCleanupTask] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task: AudioCleanupTask) -> None:
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                logger.warning(f"Задача {task.task_id[:12]}... уже существует")
                return
            heapq.heappush(self._heap, task)
            self._tasks_by_id[task.task_id] = task

    async def get_highest_priority_task(self) -> Optional[AudioCleanupTask]:
        async with self._lock:
            available_tasks = []
            for task in self._tasks_by_id.values():
                # Завершённые и отменённые не берём
                if task.status in (TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED):
                    continue
                # Приостановленные не запускаем
                if task.status == TaskStatus.PAUSED:
                    continue
                # Активные задачи не выбираем повторно
                if task.status in (TaskStatus.PROCESSING, TaskStatus.POST_PROCESSING):
                    continue
                # Доступны только PENDING и RESUMING
                if task.status in (TaskStatus.PENDING, TaskStatus.RESUMING):
                    available_tasks.append(task)

            if not available_tasks:
                return None

            def effective_priority(t):
                return t.priority - 0.5 if t.status == TaskStatus.RESUMING else t.priority

            available_tasks.sort(key=effective_priority)
            best = available_tasks[0]

            # Удаляем из кучи
            self._heap = [t for t in self._heap if t.task_id != best.task_id]
            heapq.heapify(self._heap)

            logger.debug(f"Выбрана задача {best.task_id[:12]}... приоритет={best.priority}, статус={best.status.value}")
            return best

    async def return_task(self, task: AudioCleanupTask) -> None:
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                heapq.heappush(self._heap, task)

    async def update_task_priority(self, task: AudioCleanupTask) -> None:
        async with self._lock:
            if task.task_id not in self._tasks_by_id:
                return
            self._heap = list(self._tasks_by_id.values())
            heapq.heapify(self._heap)

    async def remove_task(self, task: AudioCleanupTask) -> bool:
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                del self._tasks_by_id[task.task_id]
                self._heap = [t for t in self._heap if t.task_id != task.task_id]
                heapq.heapify(self._heap)
                return True
            return False

    async def get_task(self, task_id: str) -> Optional[AudioCleanupTask]:
        async with self._lock:
            return self._tasks_by_id.get(task_id)

    async def get_all_tasks(self) -> list[AudioCleanupTask]:
        async with self._lock:
            return list(self._tasks_by_id.values())

    async def __len__(self) -> int:
        async with self._lock:
            return len(self._tasks_by_id)

    async def is_empty(self) -> bool:
        async with self._lock:
            return len(self._tasks_by_id) == 0