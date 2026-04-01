"""
Модуль для управления задачами обработки аудио.

Содержит классы для представления задач обработки видео (AudioCleanupTask)
и приоритетной очереди для управления этими задачами (PriorityTaskQueue).
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
        priority (int): Приоритет задачи (чем выше, тем важнее).
        input_path (str): Путь к исходному видеофайлу.
        output_path (str): Путь для сохранения обработанного видео.
        handler (AudioHandler): Обработчик аудио для применения эффектов.
        handler_settings (ProcessingSettings): Настройки обработчика.
        total_segments (int): Общее количество аудио сегментов.
        cleaned_segments (int): Количество обработанных сегментов.
        status (TaskStatus): Текущий статус задачи.
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
        """Инициализация после создания. Устанавливает событие паузы."""
        self._pause_event.set()

    def __hash__(self) -> int:
        """Возвращает хэш на основе task_id."""
        return hash(self.task_id)

    def __eq__(self, other: Any) -> bool:
        """Сравнивает задачи по task_id."""
        if not isinstance(other, AudioCleanupTask):
            return False
        return self.task_id == other.task_id

    def __lt__(self, other: Any) -> bool:
        """
        Сравнивает задачи по приоритету для использования в heapq.

        Args:
            other (Any): Другая задача для сравнения.

        Returns:
            bool: True если текущая задача имеет более высокий приоритет.

        Note:
            Выше приоритет = меньше число в куче (для heapq).
        """
        if not isinstance(other, AudioCleanupTask):
            return NotImplemented
        return self.priority > other.priority

    def format_duration(self, seconds: float) -> str:
        """
        Форматирует длительность в MM:SS или HH:MM:SS.

        Args:
            seconds (float): Длительность в секундах.

        Returns:
            str: Отформатированная строка длительности.
        """
        if seconds <= 0:
            return "--:--"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    async def set_duration(self, duration: float) -> None:
        """
        Устанавливает длительность видео.

        Args:
            duration (float): Длительность в секундах.
        """
        async with self._lock:
            self.duration = duration
            self.duration_formatted = self.format_duration(duration)

    async def wait_if_paused(self) -> bool:
        """
        Ожидает, если задача приостановлена.

        Returns:
            bool: True если задача не отменена, False если отменена.
        """
        async with self._lock:
            if self._cancelled:
                return False

        await self._pause_event.wait()

        async with self._lock:
            return not self._cancelled

    async def pause(self) -> bool:
        """
        Приостанавливает задачу.

        Returns:
            bool: True если приостановлено успешно.
        """
        async with self._lock:
            if self.status != TaskStatus.PROCESSING:
                return False
            if self._cancelled:
                return False

            self.status = TaskStatus.PAUSED
            self._pause_event.clear()
            return True

    async def resume(self) -> bool:
        """
        Возобновляет задачу.

        Returns:
            bool: True если возобновлено успешно.
        """
        async with self._lock:
            logger.info(f"resume() вызван для задачи {self.task_id}, текущий статус={self.status.value}")

            if self.status != TaskStatus.PAUSED:
                logger.warning(f"Задача {self.task_id} не приостановлена, статус: {self.status}")
                return False
            if self._cancelled:
                logger.warning(f"Задача {self.task_id} отменена")
                return False

            self.status = TaskStatus.PROCESSING
            self._pause_event.set()

            logger.info(f"Задача {self.task_id} возобновлена, новый статус={self.status.value}")
            return True

    async def cancel(self) -> bool:
        """
        Отменяет задачу.

        Returns:
            bool: True если отменено успешно.
        """
        async with self._lock:
            if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
                return False

            self._cancelled = True
            self.status = TaskStatus.CANCELLED
            self._pause_event.set()

            return True

    def is_cancelled(self) -> bool:
        """
        Проверяет, отменена ли задача.

        Returns:
            bool: True если задача отменена.
        """
        return self._cancelled

    async def increment_progress(self, segments: int = 1) -> None:
        """
        Увеличивает счетчик обработанных сегментов.

        Args:
            segments (int, optional): Количество сегментов для добавления.
                По умолчанию 1.
        """
        async with self._lock:
            old_value = self.cleaned_segments
            if self.total_segments > 0:
                self.cleaned_segments = min(self.cleaned_segments + segments, self.total_segments)
            else:
                self.cleaned_segments += segments

            logger.debug(f"Задача {self.task_id}: прогресс {old_value} -> {self.cleaned_segments}/{self.total_segments}")

    async def update_progress(self, cleaned_segments: int) -> None:
        """
        Обновляет счетчик обработанных сегментов.

        Args:
            cleaned_segments (int): Новое количество обработанных сегментов.
        """
        async with self._lock:
            if self.total_segments > 0:
                self.cleaned_segments = min(cleaned_segments, self.total_segments)
            else:
                self.cleaned_segments = cleaned_segments

    async def set_total_segments(self, total_segments: int) -> None:
        """
        Устанавливает общее количество сегментов.

        Args:
            total_segments (int): Общее количество сегментов в видео.
        """
        async with self._lock:
            self.total_segments = max(0, total_segments)
            if self.cleaned_segments > self.total_segments:
                self.cleaned_segments = self.total_segments

    async def get_progress_percentage(self) -> float:
        """
        Рассчитывает процент выполнения задачи.

        Returns:
            float: Процент выполнения от 0.0 до 100.0.
        """
        async with self._lock:
            if self.total_segments == 0:
                return 0.0 if self.cleaned_segments == 0 else 100.0
            return (self.cleaned_segments / self.total_segments) * 100

    async def set_status(self, status: TaskStatus) -> None:
        """
        Устанавливает статус задачи.

        Args:
            status (TaskStatus): Новый статус.
        """
        async with self._lock:
            self.status = status
            if status == TaskStatus.PROCESSING:
                self._pause_event.set()
            elif status == TaskStatus.PAUSED:
                self._pause_event.clear()
            elif status in [TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                self._cancelled = (status == TaskStatus.CANCELLED)
                self._pause_event.set()

    def get_status_sync(self) -> TaskStatus:
        """
        Синхронное получение статуса (только для чтения).

        Returns:
            TaskStatus: Текущий статус задачи.
        """
        return self.status

    def get_progress_sync(self) -> tuple[int, int, float]:
        """
        Синхронное получение прогресса.

        Returns:
            tuple[int, int, float]: (обработано, всего, процент)
        """
        if self.total_segments == 0:
            return (self.cleaned_segments, 0, 0.0)
        percent = (self.cleaned_segments / self.total_segments) * 100
        return (self.cleaned_segments, self.total_segments, percent)


class PriorityTaskQueue:
    """
    Приоритетная очередь для управления задачами обработки.

    Attributes:
        _heap (list): Внутренняя структура кучи (приоритет, задача).
        _tasks_by_id (dict): Словарь задач по ID.
        _lock (asyncio.Lock): Блокировка для потокобезопасности.
    """

    def __init__(self):
        """
        Инициализирует пустую приоритетную очередь.
        """
        self._heap = []
        self._tasks_by_id: dict[str, AudioCleanupTask] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task: AudioCleanupTask) -> None:
        """
        Добавляет задачу в очередь.

        Args:
            task (AudioCleanupTask): Задача для добавления.
        """
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                logger.warning(f"Задача {task.task_id} уже существует в очереди")
                return
            heapq.heappush(self._heap, (task.priority, task))
            self._tasks_by_id[task.task_id] = task
            logger.debug(f"Задача {task.task_id} добавлена в очередь, размер очереди: {len(self._heap)}")

    async def get_highest_priority_task(self) -> Optional[AudioCleanupTask]:
        """
        Извлекает задачу с наивысшим приоритетом.

        Returns:
            Optional[AudioCleanupTask]: Задача с максимальным приоритетом или None.
        """
        async with self._lock:
            while self._heap:
                priority, task = heapq.heappop(self._heap)
                if task.task_id not in self._tasks_by_id:
                    continue
                if task.status in [TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    del self._tasks_by_id[task.task_id]
                    continue
                return task
            return None

    async def remove_task(self, task: AudioCleanupTask) -> bool:
        """
        Удаляет задачу из очереди.

        Args:
            task (AudioCleanupTask): Задача для удаления.

        Returns:
            bool: True если задача была удалена.
        """
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                del self._tasks_by_id[task.task_id]
                self._heap = [(p, t) for p, t in self._heap if t.task_id != task.task_id]
                heapq.heapify(self._heap)
                return True
            return False

    async def get_task(self, task_id: str) -> Optional[AudioCleanupTask]:
        """
        Получает задачу по ID.

        Args:
            task_id (str): Идентификатор задачи.

        Returns:
            Optional[AudioCleanupTask]: Задача или None, если не найдена.
        """
        async with self._lock:
            return self._tasks_by_id.get(task_id)

    async def get_all_tasks(self) -> list[AudioCleanupTask]:
        """
        Получает все задачи из очереди.

        Returns:
            list[AudioCleanupTask]: Список всех задач.
        """
        async with self._lock:
            return list(self._tasks_by_id.values())

    async def __len__(self) -> int:
        """Возвращает количество задач в очереди."""
        async with self._lock:
            return len(self._tasks_by_id)

    async def is_empty(self) -> bool:
        """
        Проверяет, пуста ли очередь.

        Returns:
            bool: True если очередь пуста.
        """
        async with self._lock:
            return len(self._tasks_by_id) == 0