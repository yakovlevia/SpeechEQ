import heapq
from dataclasses import dataclass, field
from typing import Any
from processing.handlers.base import AudioHandler
from processing.core.settings import ProcessingSettings


@dataclass(order=True)
class AudioCleanupTask:
    """
    Задача на очистку аудио из видео.
    
    Attributes:
        priority (int): Приоритет задачи (чем выше, тем важнее).
        input_path (str): Путь к исходному видеофайлу.
        output_path (str): Путь для сохранения обработанного видео.
        handler (AudioHandler): Обработчик аудио для применения эффектов.
        handler_settings (AudioHandlerSettings): Настройки обработчика.
        total_segments (int): Общее количество аудио сегментов.
        cleaned_segments (int): Количество обработанных сегментов.
    """
    priority: int = field(compare=False)

    input_path: str = field(compare=False)
    output_path: str = field(compare=False)

    handler: AudioHandler = field(compare=False, default=None)
    handler_settings: ProcessingSettings = field(
        compare=False,
        default_factory=ProcessingSettings
    )

    total_segments: int = field(compare=False, default=0)
    cleaned_segments: int = field(compare=False, default=0)
    
    _counter: int = field(init=False, compare=True, default_factory=lambda: AudioCleanupTask._get_counter())
    _counter_instance = 0
    
    @staticmethod
    def _get_counter() -> int:
        AudioCleanupTask._counter_instance += 1
        return AudioCleanupTask._counter_instance
    
    def __hash__(self) -> int:
        return hash((self.input_path, self.output_path, self.priority, self._counter))
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AudioCleanupTask):
            return False
        return (self.input_path == other.input_path and 
                self.output_path == other.output_path and 
                self.priority == other.priority and 
                self._counter == other._counter)
    
    def increment_progress(self, segments: int = 1) -> None:
        """
        Увеличивает счетчик обработанных сегментов.
        
        Args:
            segments (int, optional): Количество сегментов для добавления.
                По умолчанию 1.
        """
        if self.total_segments > 0:
            self.cleaned_segments = min(self.cleaned_segments + segments, self.total_segments)
        else:
            self.cleaned_segments += segments
    
    def update_progress(self, cleaned_segments: int) -> None:
        """
        Обновляет счетчик обработанных сегментов.
        
        Args:
            cleaned_segments (int): Новое количество обработанных сегментов.
        """
        if self.total_segments > 0:
            self.cleaned_segments = min(cleaned_segments, self.total_segments)
        else:
            self.cleaned_segments = cleaned_segments
    
    def set_total_segments(self, total_segments: int) -> None:
        """
        Устанавливает общее количество сегментов.
        
        Args:
            total_segments (int): Общее количество сегментов в видео.
        """
        self.total_segments = max(0, total_segments)
        if self.cleaned_segments > self.total_segments:
            self.cleaned_segments = self.total_segments
    
    def get_progress_percentage(self) -> float:
        """
        Рассчитывает процент выполнения задачи.
        
        Returns:
            float: Процент выполнения от 0.0 до 100.0.
        """
        if self.total_segments == 0:
            return 0.0 if self.cleaned_segments == 0 else 100.0
        return (self.cleaned_segments / self.total_segments) * 100
    
    def is_completed(self) -> bool:
        """
        Проверяет, завершена ли задача.
        
        Returns:
            bool: True если все сегменты обработаны, иначе False.
        """
        if self.total_segments == 0:
            return False
        return self.cleaned_segments >= self.total_segments


class PriorityTaskQueue:
    """
    Приоритетная очередь для управления задачами обработки.
    
    Реализует min-heap для эффективного извлечения задач
    с наивысшим приоритетом.
    
    Attributes:
        _heap (list): Внутренняя структура кучи.
        _set (set): Множество для быстрой проверки наличия задач.
    """
    
    def __init__(self):
        self._heap = []
        self._set = set()
    
    def add_task(self, task: AudioCleanupTask) -> None:
        """
        Добавляет задачу в очередь.
        
        Args:
            task (AudioCleanupTask): Задача для добавления.
        
        Note:
            Игнорирует дубликаты задач.
        """
        if task not in self._set:
            heapq.heappush(self._heap, (-task.priority, task))
            self._set.add(task)
    
    def get_highest_priority_task(self) -> AudioCleanupTask:
        """
        Извлекает задачу с наивысшим приоритетом.
        
        Returns:
            AudioCleanupTask: Задача с максимальным приоритетом.
        
        Raises:
            IndexError: Если очередь пуста.
        """
        if not self._heap:
            raise IndexError("Очередь пуста")
        
        priority, task = heapq.heappop(self._heap)
        self._set.remove(task)
        
        return task
    
    def peek_highest_priority(self) -> AudioCleanupTask:
        """
        Просматривает задачу с наивысшим приоритетом без удаления.
        
        Returns:
            AudioCleanupTask: Задача с максимальным приоритетом.
        
        Raises:
            IndexError: Если очередь пуста.
        """
        if not self._heap:
            raise IndexError("Очередь пуста")
        
        priority, task = self._heap[0]
        return task
    
    def remove_task(self, task: AudioCleanupTask) -> bool:
        """
        Удаляет конкретную задачу из очереди.
        
        Args:
            task (AudioCleanupTask): Задача для удаления.
        
        Returns:
            bool: True если задача была удалена, False если не найдена.
        """
        if task in self._set:
            self._set.remove(task)
            return True
        return False
    
    def __len__(self) -> int:
        return len(self._set)
    
    def __contains__(self, task: AudioCleanupTask) -> bool:
        return task in self._set
    
    def is_empty(self) -> bool:
        return len(self._set) == 0