# src\client\processing_manager.py
import asyncio
from typing import Optional
import logging

from .video_queue import AudioCleanupTask, PriorityTaskQueue
from .video_processor import VideoProcessor
from .config import FFMPEG_CONFIG, QUEUE_CONFIG

logger = logging.getLogger(__name__)


class ProcessingManager:
    """
    Менеджер для управления очередью и обработкой видео задач.
    
    Координирует работу очереди задач и видеопроцессора.
    
    Attributes:
        task_queue (PriorityTaskQueue): Приоритетная очередь задач.
        video_processor (VideoProcessor): Процессор для обработки видео.
        _is_processing (bool): Флаг активности обработки.
        _processing_task (Optional[asyncio.Task]): Активная задача обработки.
    """
    
    def __init__(self):
        self.task_queue = PriorityTaskQueue()
        self.video_processor = VideoProcessor(
            ffmpeg_path=FFMPEG_CONFIG["ffmpeg_path"],
            ffprobe_path=FFMPEG_CONFIG["ffprobe_path"],
            max_concurrent_segments=QUEUE_CONFIG["audio_queue_max_size"],
        )
        self._is_processing = False
        self._processing_task: Optional[asyncio.Task] = None
    
    def add_video_task(self, task: AudioCleanupTask) -> None:
        """
        Добавляет задачу в очередь обработки.
        
        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        self.task_queue.add_task(task)
        logger.info(f"Задача добавлена в очередь: {task.input_path}")
    
    async def start_processing(self) -> None:
        """
        Запускает обработку задач из очереди.
        
        Note:
            Если обработка уже запущена, выводит предупреждение.
        """
        if self._is_processing:
            logger.warning("Обработка уже запущена")
            return
        
        self._is_processing = True
        logger.info("Запуск обработки видео")
        
        self._processing_task = asyncio.create_task(self._process_queue())
        
        try:
            await self._processing_task
        finally:
            self._is_processing = False
    
    async def stop_processing(self) -> None:
        """
        Останавливает обработку задач.
        
        Note:
            Корректно завершает активные задачи.
        """
        self._is_processing = False
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                logger.info("Обработка остановлена")
    
    async def _process_queue(self) -> None:
        """
        Внутренний метод для непрерывной обработки очереди.
        
        Note:
            Работает в цикле, пока включен флаг _is_processing.
            Обрабатывает задачи по приоритету.
            Выводит подробные логи о ходе выполнения.
        """
        logger.info("Процессор очереди запущен (daemon mode)")

        while self._is_processing:
            try:
                if self.task_queue.is_empty():
                    await asyncio.sleep(0.5)
                    continue

                task = self.task_queue.get_highest_priority_task()
                logger.info(f"Начата обработка: {task.input_path}")

                await self.video_processor.process_video(task)

                logger.info(f"Завершена обработка: {task.input_path}")

            except asyncio.CancelledError:
                logger.info("Процессор очереди остановлен")
                break
            except Exception as e:
                logger.exception(f"Ошибка обработки задачи: {e}")

        logger.info("Процессор очереди завершён")
