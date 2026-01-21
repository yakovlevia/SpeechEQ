# src/client/video_queue.py
import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class AudioCleanupTask:
    """Класс для хранения информации об очистке аудио с видео"""
    priority: int = field(compare=False)
    
    input_path: str = field(compare=False)
    output_path: str = field(compare=False)
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
        """Увеличить количество очищенных сегментов"""
        if self.total_segments > 0:
            self.cleaned_segments = min(self.cleaned_segments + segments, self.total_segments)
        else:
            self.cleaned_segments += segments
    
    def update_progress(self, cleaned_segments: int) -> None:
        """Обновить количество очищенных сегментов"""
        if self.total_segments > 0:
            self.cleaned_segments = min(cleaned_segments, self.total_segments)
        else:
            self.cleaned_segments = cleaned_segments
    
    def set_total_segments(self, total_segments: int) -> None:
        """Установить общее количество сегментов"""
        self.total_segments = max(0, total_segments)
        if self.cleaned_segments > self.total_segments:
            self.cleaned_segments = self.total_segments
    
    def get_progress_percentage(self) -> float:
        """Получить процент выполнения"""
        if self.total_segments == 0:
            return 0.0 if self.cleaned_segments == 0 else 100.0
        return (self.cleaned_segments / self.total_segments) * 100
    
    def is_completed(self) -> bool:
        """Проверить, завершена ли задача"""
        if self.total_segments == 0:
            return False
        return self.cleaned_segments >= self.total_segments


class PriorityTaskQueue:
    """Класс для работы с приоритетной очередью задач"""
    
    def __init__(self):
        self._heap = []
        self._set = set()
    
    def add_task(self, task: AudioCleanupTask) -> None:
        """Добавить задачу в очередь"""
        if task not in self._set:
            heapq.heappush(self._heap, (-task.priority, task))
            self._set.add(task)
    
    def get_highest_priority_task(self) -> AudioCleanupTask:
        """Получить задачу с наивысшим приоритетом"""
        if not self._heap:
            raise IndexError("Очередь пуста")
        
        priority, task = heapq.heappop(self._heap)
        self._set.remove(task)
        
        return task
    
    def peek_highest_priority(self) -> AudioCleanupTask:
        """Посмотреть задачу с наивысшим приоритетом без удаления"""
        if not self._heap:
            raise IndexError("Очередь пуста")
        
        priority, task = self._heap[0]
        return task
    
    def remove_task(self, task: AudioCleanupTask) -> bool:
        """Удалить конкретную задачу из очереди"""
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