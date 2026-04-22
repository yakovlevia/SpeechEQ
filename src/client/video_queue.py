"""
Модуль для управления задачами обработки аудио.

Содержит классы задачи (AudioCleanupTask) и приоритетной очереди
(PriorityTaskQueue) для асинхронной обработки видеофайлов.
"""
import heapq
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import asyncio
import uuid
import logging

from src.processing.handlers.base import AudioHandler
from src.processing.core.settings import ProcessingSettings

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
    """Задача на очистку аудио из видео.

    Attributes:
        task_id: Уникальный идентификатор задачи.
        priority: Приоритет задачи (меньшее значение = выше приоритет).
        input_path: Путь к исходному видеофайлу.
        output_path: Путь для сохранения результата.
        handler: Обработчик аудио для очистки.
        handler_settings: Настройки обработчика.
        total_segments: Общее количество аудио-сегментов.
        cleaned_segments: Количество уже обработанных сегментов.
        status: Текущий статус задачи.
        duration: Длительность видео в секундах.
        duration_formatted: Человекочитаемый формат длительности.
        error_message: Текст ошибки (если статус FAILED).
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
    error_message: str = ""

    _pause_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False, compare=False)
    _cancelled: bool = field(default=False, repr=False, compare=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Инициализация после создания: активирует событие паузы."""
        self._pause_event.set()

    def __hash__(self) -> int:
        """Хеш по task_id для использования в множествах и словарях."""
        return hash(self.task_id)

    def __eq__(self, other: Any) -> bool:
        """Сравнение задач по идентификатору."""
        if not isinstance(other, AudioCleanupTask):
            return False
        return self.task_id == other.task_id

    def __lt__(self, other: Any) -> bool:
        """Сравнение для heapq: по приоритету, затем по task_id.

        Меньший priority = более высокий приоритет в очереди.
        """
        if not isinstance(other, AudioCleanupTask):
            return NotImplemented
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.task_id < other.task_id

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Форматирует длительность в человекочитаемый вид.

        Args:
            seconds: Длительность в секундах.

        Returns:
            str: Формат "MM:SS" или "HH:MM:SS", или "--:--" при нуле.
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
        """Устанавливает длительность видео и её форматированное представление.

        Args:
            duration: Длительность в секундах.
        """
        async with self._lock:
            self.duration = duration
            self.duration_formatted = self.format_duration(duration)

    async def wait_if_paused(self) -> bool:
        """Ожидает снятия паузы или отмены задачи.

        Returns:
            bool: False если задача отменена, True если можно продолжать.
        """
        async with self._lock:
            if self._cancelled:
                return False
        await self._pause_event.wait()
        async with self._lock:
            return not self._cancelled

    def is_paused(self) -> bool:
        """Проверяет, приостановлена ли задача.

        Returns:
            bool: True если статус PAUSED.
        """
        return self.status == TaskStatus.PAUSED

    async def pause(self) -> bool:
        """Приостанавливает выполнение задачи.

        Возвращает успех только если задача в статусе PROCESSING/POST_PROCESSING.

        Returns:
            bool: True если приостановка успешна.
        """
        async with self._lock:
            if self.status not in (TaskStatus.PROCESSING, TaskStatus.POST_PROCESSING):
                logger.warning(
                    f"Задача {self.task_id[:12]}... не может быть приостановлена: {self.status.value}"
                )
                return False
            if self._cancelled:
                return False
            self.status = TaskStatus.PAUSED
            self._pause_event.clear()
            logger.info(f"Задача {self.task_id[:12]}... приостановлена")
            return True

    async def should_exit(self) -> bool:
        """Проверяет, нужно ли прекратить обработку задачи.

        Returns:
            bool: True если задача отменена или приостановлена.
        """
        async with self._lock:
            return self._cancelled or self.status == TaskStatus.PAUSED

    async def resume(self) -> bool:
        """Возобновляет выполнение приостановленной задачи.

        Returns:
            bool: True если возобновление успешно.
        """
        async with self._lock:
            if self.status != TaskStatus.PAUSED:
                logger.warning(
                    f"Задача {self.task_id[:12]}... не приостановлена, текущий статус: {self.status.value}"
                )
                return False
            if self._cancelled:
                logger.warning(f"Задача {self.task_id[:12]}... отменена")
                return False
            self.status = TaskStatus.RESUMING
            self._pause_event.set()
            logger.info(f"Задача {self.task_id[:12]}... возобновлена")
            return True

    async def set_post_processing(self) -> bool:
        """Переключает задачу в статус постобработки.

        Возвращает успех только если текущий статус — PROCESSING.

        Returns:
            bool: True если переход выполнен.
        """
        async with self._lock:
            if self.status != TaskStatus.PROCESSING:
                logger.warning(
                    f"Задача {self.task_id[:12]}... не может перейти в POST_PROCESSING: {self.status.value}"
                )
                return False
            if self._cancelled:
                return False
            self.status = TaskStatus.POST_PROCESSING
            logger.info(f"Задача {self.task_id[:12]}... перешла в постобработку")
            return True

    async def set_processing_from_resuming(self) -> bool:
        """Переключает задачу из RESUMING обратно в PROCESSING.

        Returns:
            bool: True если статус изменён.
        """
        async with self._lock:
            if self.status != TaskStatus.RESUMING:
                logger.warning(
                    f"Задача {self.task_id[:12]}... не в статусе RESUMING: {self.status.value}"
                )
                return False
            self.status = TaskStatus.PROCESSING
            logger.info(f"Задача {self.task_id[:12]}... возобновила обработку")
            return True

    async def cancel(self) -> bool:
        """Отменяет задачу, если она ещё не завершена.

        Returns:
            bool: True если отмена успешна.
        """
        async with self._lock:
            if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
                return False
            self._cancelled = True
            self.status = TaskStatus.CANCELLED
            self.error_message = ""
            self._pause_event.set()
            logger.info(f"Задача {self.task_id[:12]}... отменена")
            return True

    def is_cancelled(self) -> bool:
        """Проверяет флаг отмены задачи.

        Returns:
            bool: True если задача отменена.
        """
        return self._cancelled

    async def increment_progress(self, segments: int = 1) -> None:
        """Увеличивает счётчик обработанных сегментов.

        Args:
            segments: Количество сегментов для добавления (по умолчанию 1).
        """
        async with self._lock:
            if self.total_segments > 0:
                self.cleaned_segments = min(
                    self.cleaned_segments + segments, self.total_segments
                )
            else:
                self.cleaned_segments += segments

    async def update_progress(self, cleaned_segments: int) -> None:
        """Устанавливает абсолютное значение обработанных сегментов.

        Args:
            cleaned_segments: Новое значение счётчика.
        """
        async with self._lock:
            if self.total_segments > 0:
                self.cleaned_segments = min(cleaned_segments, self.total_segments)
            else:
                self.cleaned_segments = cleaned_segments

    async def set_total_segments(self, total_segments: int) -> None:
        """Устанавливает общее количество сегментов.

        Корректирует cleaned_segments если он превышает новый total.

        Args:
            total_segments: Новое общее количество.
        """
        async with self._lock:
            self.total_segments = max(0, total_segments)
            if self.cleaned_segments > self.total_segments:
                self.cleaned_segments = self.total_segments

    async def get_progress_percentage(self) -> float:
        """Вычисляет процент выполнения задачи.

        Returns:
            float: Процент от 0.0 до 100.0.
        """
        async with self._lock:
            if self.total_segments == 0:
                return 0.0 if self.cleaned_segments == 0 else 100.0
            return (self.cleaned_segments / self.total_segments) * 100

    async def set_status(self, status: TaskStatus, error_message: str = "") -> None:
        """Устанавливает новый статус задачи.

        Автоматически управляет событием паузы и сообщением об ошибке.

        Args:
            status: Новый статус из TaskStatus.
            error_message: Текст ошибки (обязателен для статуса FAILED).
        """
        async with self._lock:
            old_status = self.status
            self.status = status

            if error_message:
                self.error_message = error_message
            elif status == TaskStatus.FAILED and not self.error_message:
                self.error_message = "Неизвестная ошибка"
            elif status != TaskStatus.FAILED:
                self.error_message = ""

            # Управление событием паузы в зависимости от статуса
            if status in (
                TaskStatus.PROCESSING,
                TaskStatus.RESUMING,
                TaskStatus.POST_PROCESSING,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
            ):
                self._pause_event.set()
            elif status == TaskStatus.PAUSED:
                self._pause_event.clear()
            elif status == TaskStatus.CANCELLED:
                self._cancelled = True
                self._pause_event.set()

            log_msg = f"Задача {self.task_id[:12]}... статус: {old_status.value} → {status.value}"
            if error_message:
                log_msg += f", ошибка: {error_message}"
            logger.info(log_msg)

    def get_status_sync(self) -> TaskStatus:
        """Возвращает текущий статус без асинхронной блокировки.

        Returns:
            TaskStatus: Текущий статус задачи.
        """
        return self.status

    def get_progress_sync(self) -> tuple[int, int, float]:
        """Возвращает прогресс без асинхронной блокировки.

        Returns:
            tuple: (обработано, всего, процент) или (обработано, 0, 0.0) если всего=0.
        """
        if self.total_segments == 0:
            return (self.cleaned_segments, 0, 0.0)
        percent = (self.cleaned_segments / self.total_segments) * 100
        return (self.cleaned_segments, self.total_segments, percent)

    def get_error_message(self) -> str:
        """Возвращает сообщение об ошибке.

        Returns:
            str: Текст ошибки или пустая строка.
        """
        return self.error_message


class PriorityTaskQueue:
    """Приоритетная очередь для управления задачами обработки.

    Реализует очередь на основе heapq с поддержкой:
    - Добавления задач с приоритетом
    - Получения задачи с наивысшим приоритетом
    - Обновления приоритета и удаления задач
    - Фильтрации по статусу при выборке
    """

    def __init__(self) -> None:
        """Инициализация пустой очереди."""
        self._heap: list[AudioCleanupTask] = []
        self._tasks_by_id: dict[str, AudioCleanupTask] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task: AudioCleanupTask) -> None:
        """Добавляет задачу в очередь.

        Если задача с таким task_id уже существует — добавление игнорируется.

        Args:
            task: Задача для добавления.
        """
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                logger.warning(f"Задача {task.task_id[:12]}... уже в очереди")
                return
            heapq.heappush(self._heap, task)
            self._tasks_by_id[task.task_id] = task
            logger.debug(f"Задача {task.task_id[:12]}... добавлена в очередь (приоритет={task.priority})")

    async def get_highest_priority_task(self) -> Optional[AudioCleanupTask]:
        """Извлекает задачу с наивысшим приоритетом, доступную для запуска.

        Исключает задачи со статусами COMPLETED, CANCELLED, FAILED, PAUSED,
        а также уже обрабатываемые (PROCESSING, POST_PROCESSING).
        Задачи в статусе RESUMING получают небольшой бонус к приоритету.

        Returns:
            AudioCleanupTask или None, если доступных задач нет.
        """
        async with self._lock:
            available_tasks = []
            for task in self._tasks_by_id.values():
                if task.status in (
                    TaskStatus.CANCELLED,
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.PAUSED,
                    TaskStatus.PROCESSING,
                    TaskStatus.POST_PROCESSING,
                ):
                    continue
                if task.status in (TaskStatus.PENDING, TaskStatus.RESUMING):
                    available_tasks.append(task)

            if not available_tasks:
                return None

            # RESUMING-задачи получают приоритетный бонус
            def effective_priority(t: AudioCleanupTask) -> float:
                return t.priority - 0.5 if t.status == TaskStatus.RESUMING else t.priority

            available_tasks.sort(key=effective_priority)
            best = available_tasks[0]

            # Удаляем выбранную задачу из кучи
            self._heap = [t for t in self._heap if t.task_id != best.task_id]
            heapq.heapify(self._heap)

            logger.debug(
                f"Выбрана задача {best.task_id[:12]}... приоритет={best.priority}, статус={best.status.value}"
            )
            return best

    async def return_task(self, task: AudioCleanupTask) -> None:
        """Возвращает задачу обратно в очередь.

        Используется при приостановке или ошибке для повторной обработки.

        Args:
            task: Задача для возврата.
        """
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                heapq.heappush(self._heap, task)
                logger.debug(f"Задача {task.task_id[:12]}... возвращена в очередь")

    async def update_task_priority(self, task: AudioCleanupTask) -> None:
        """Пересобирает очередь с учётом изменённого приоритета задачи.

        Args:
            task: Задача с обновлённым приоритетом.
        """
        async with self._lock:
            if task.task_id not in self._tasks_by_id:
                return
            self._heap = list(self._tasks_by_id.values())
            heapq.heapify(self._heap)
            logger.debug(f"Приоритет задачи {task.task_id[:12]}... обновлён")

    async def remove_task(self, task: AudioCleanupTask) -> bool:
        """Удаляет задачу из очереди.

        Args:
            task: Задача для удаления.

        Returns:
            bool: True если задача найдена и удалена.
        """
        async with self._lock:
            if task.task_id in self._tasks_by_id:
                del self._tasks_by_id[task.task_id]
                self._heap = [t for t in self._heap if t.task_id != task.task_id]
                heapq.heapify(self._heap)
                logger.debug(f"Задача {task.task_id[:12]}... удалена из очереди")
                return True
            return False

    async def get_task(self, task_id: str) -> Optional[AudioCleanupTask]:
        """Получает задачу по идентификатору.

        Args:
            task_id: Идентификатор задачи.

        Returns:
            AudioCleanupTask или None.
        """
        async with self._lock:
            return self._tasks_by_id.get(task_id)

    async def get_all_tasks(self) -> list[AudioCleanupTask]:
        """Возвращает копию списка всех задач в очереди.

        Returns:
            list[AudioCleanupTask]: Список задач.
        """
        async with self._lock:
            return list(self._tasks_by_id.values())

    async def __len__(self) -> int:
        """Возвращает количество задач в очереди.

        Returns:
            int: Количество задач.
        """
        async with self._lock:
            return len(self._tasks_by_id)

    async def is_empty(self) -> bool:
        """Проверяет, пуста ли очередь.

        Returns:
            bool: True если задач нет.
        """
        async with self._lock:
            return len(self._tasks_by_id) == 0