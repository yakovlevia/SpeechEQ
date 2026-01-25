# src/client/processing_manager.py
import asyncio
from typing import Optional, Set
import logging

from .video_queue import AudioCleanupTask, PriorityTaskQueue
from .video_processor import VideoProcessor
from .config import FFMPEG_CONFIG, QUEUE_CONFIG

logger = logging.getLogger(__name__)


class ProcessingManager:
    """
    Менеджер для управления очередью и обработкой видео задач.
    
    Координирует работу очереди задач и видеопроцессора.
    Поддерживает параллельную обработку нескольких видео.
    
    Attributes:
        task_queue (PriorityTaskQueue): Приоритетная очередь задач.
        video_processor (VideoProcessor): Процессор для обработки видео.
        max_concurrent_videos (int): Максимальное количество параллельно обрабатываемых видео.
        _is_processing (bool): Флаг активности обработки.
        _processing_task (Optional[asyncio.Task]): Активная задача обработки.
        _active_tasks (Set[asyncio.Task]): Множество активных задач обработки видео.
        _processing_semaphore (asyncio.Semaphore): Семафор для ограничения параллельной обработки видео.
    """
    
    def __init__(self):
        self.task_queue = PriorityTaskQueue()
        self.video_processor = VideoProcessor(
            ffmpeg_path=FFMPEG_CONFIG["ffmpeg_path"],
            ffprobe_path=FFMPEG_CONFIG["ffprobe_path"],
            max_concurrent_segments=QUEUE_CONFIG["audio_queue_max_size"],
        )
        self.max_concurrent_videos = QUEUE_CONFIG.get("max_concurrent_videos", 3)
        self._is_processing = False
        self._processing_task: Optional[asyncio.Task] = None
        self._active_tasks: Set[asyncio.Task] = set()
        self._processing_semaphore = asyncio.Semaphore(self.max_concurrent_videos)
    
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
        logger.info(f"Запуск обработки видео (макс. параллельно: {self.max_concurrent_videos})")
        
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
        
        # Отменяем основную задачу обработки очереди
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                logger.info("Обработка очереди остановлена")
        
        # Отменяем все активные задачи обработки видео
        if self._active_tasks:
            logger.info(f"Отмена {len(self._active_tasks)} активных задач обработки видео")
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()
            
            # Ждем завершения всех задач
            try:
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
            except asyncio.CancelledError:
                logger.info("Все активные задачи обработки видео остановлены")
            finally:
                self._active_tasks.clear()
    
    async def _process_video_with_semaphore(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает видео с учетом ограничения параллелизма.
        
        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        async with self._processing_semaphore:
            try:
                logger.info(f"Начата обработка видео (слот {self._processing_semaphore._value + 1}/{self.max_concurrent_videos}): {task.input_path}")
                await self.video_processor.process_video(task)
                logger.info(f"Завершена обработка видео: {task.input_path}")
            except Exception as e:
                logger.error(f"Ошибка обработки видео {task.input_path}: {e}")
                raise
            except asyncio.CancelledError:
                logger.info(f"Обработка видео отменена: {task.input_path}")
                raise
    
    async def _process_queue(self) -> None:
        """
        Внутренний метод для непрерывной обработки очереди.
        
        Note:
            Работает в цикле, пока включен флаг _is_processing.
            Обрабатывает задачи по приоритету, с ограничением параллелизма.
            Выводит подробные логи о ходе выполнения.
        """
        logger.info(f"Процессор очереди запущен (макс. параллельно: {self.max_concurrent_videos})")

        while self._is_processing:
            try:
                # Проверяем, есть ли задачи в очереди
                if self.task_queue.is_empty():
                    # Если нет активных задач, ждем новую задачу
                    if not self._active_tasks:
                        logger.debug("Очередь пуста, ожидание новых задач...")
                        await asyncio.sleep(1.0)
                    # Если есть активные задачи, просто продолжаем цикл
                    else:
                        await asyncio.sleep(0.5)
                    continue

                # Проверяем, можем ли мы запустить новую задачу (с учетом семафора)
                if len(self._active_tasks) >= self.max_concurrent_videos:
                    logger.debug(f"Достигнут лимит параллельных задач ({self.max_concurrent_videos}), ожидание...")
                    await asyncio.sleep(0.5)
                    continue

                # Получаем задачу с наивысшим приоритетом
                task = self.task_queue.get_highest_priority_task()
                
                # Запускаем обработку видео в отдельной задаче
                video_task = asyncio.create_task(
                    self._process_video_with_semaphore(task)
                )
                
                # Добавляем задачу в множество активных задач
                self._active_tasks.add(video_task)
                
                # Добавляем колбэк для удаления задачи из множества по завершении
                def remove_task(task_to_remove):
                    self._active_tasks.discard(task_to_remove)
                    logger.debug(f"Активных задач: {len(self._active_tasks)}/{self.max_concurrent_videos}")
                
                video_task.add_done_callback(remove_task)
                
                logger.info(f"Задача запущена. Активных задач: {len(self._active_tasks)}/{self.max_concurrent_videos}")

            except IndexError:
                # Очередь пуста
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                logger.info("Процессор очереди остановлен")
                break
            except Exception as e:
                logger.exception(f"Ошибка в процессоре очереди: {e}")
                await asyncio.sleep(1.0)

        # Ждем завершения всех активных задач перед выходом
        logger.info("Ожидание завершения активных задач...")
        if self._active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=30.0  # Таймаут 30 секунд
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                logger.warning("Таймаут ожидания завершения активных задач")
        
        logger.info("Процессор очереди завершён")
    
    def get_queue_stats(self) -> dict:
        """
        Получает статистику по очереди и активным задачам.
        
        Returns:
            dict: Словарь со статистикой:
                - queue_size: Количество задач в очереди
                - active_tasks: Количество активных задач
                - max_concurrent: Максимальное количество параллельных задач
                - available_slots: Доступные слоты для обработки
        """
        return {
            "queue_size": len(self.task_queue),
            "active_tasks": len(self._active_tasks),
            "max_concurrent": self.max_concurrent_videos,
            "available_slots": self.max_concurrent_videos - len(self._active_tasks),
        }
    
    def get_active_tasks_info(self) -> list:
        """
        Получает информацию об активных задачах.
        
        Returns:
            list: Список с информацией об активных задачах
        """
        tasks_info = []
        for task in self._active_tasks:
            try:
                # Получаем имя задачи (если доступно)
                task_name = task.get_name() if hasattr(task, 'get_name') else str(task)
                tasks_info.append({
                    "task": task_name,
                    "done": task.done(),
                    "cancelled": task.cancelled(),
                })
            except:
                pass
        return tasks_info
    
    def set_max_concurrent_videos(self, max_concurrent: int) -> None:
        """
        Устанавливает максимальное количество параллельно обрабатываемых видео.
        
        Args:
            max_concurrent (int): Новое значение максимального количества параллельных задач.
        
        Raises:
            ValueError: Если значение не положительное.
        """
        if max_concurrent <= 0:
            raise ValueError("max_concurrent должно быть положительным числом")
        
        self.max_concurrent_videos = max_concurrent
        self._processing_semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"Установлено максимальное количество параллельных видео: {max_concurrent}")