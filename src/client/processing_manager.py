import asyncio
from typing import Optional, Set, List, Dict
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
        _paused_tasks (Dict[str, AudioCleanupTask]): Приостановленные задачи.
        _paused_events (Dict[str, asyncio.Event]): События для приостановки.
        _cancelled_tasks (Set[str]): Множество отменённых задач (по input_path).
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
        

        self._paused_tasks: Dict[str, AudioCleanupTask] = {}
        self._paused_events: Dict[str, asyncio.Event] = {}
        self._cancelled_tasks: Set[str] = set()
    
    def add_video_task(self, task: AudioCleanupTask) -> None:
        """
        Добавляет задачу в очередь обработки.
        
        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        if task.input_path in self._cancelled_tasks:
            logger.warning(f"Задача {task.input_path} была отменена, не добавляем")
            return

        if task.input_path in self._paused_tasks:
            logger.info(f"Задача {task.input_path} была приостановлена, добавляем с высоким приоритетом")
            task.priority = 1
            del self._paused_tasks[task.input_path]
        
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

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                logger.info("Обработка очереди остановлена")

        if self._active_tasks:
            logger.info(f"Отмена {len(self._active_tasks)} активных задач обработки видео")
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()

            try:
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
            except asyncio.CancelledError:
                logger.info("Все активные задачи обработки видео остановлены")
            finally:
                self._active_tasks.clear()
    
    async def process_video(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает одно видео.
        
        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        try:
            logger.info(f"Начата обработка видео: {task.input_path}")
            if task.input_path in self._cancelled_tasks:
                logger.info(f"Задача {task.input_path} была отменена, пропускаем")
                return

            if task.input_path in self._paused_tasks:
                self._paused_events[task.input_path] = asyncio.Event()

            video_task = asyncio.create_task(
                self.video_processor.process_video(task, self)
            )
            self._active_tasks.add(video_task)
            
            try:
                await video_task
                logger.info(f"Завершена обработка видео: {task.input_path}")
            finally:
                self._active_tasks.discard(video_task)
                if task.input_path in self._paused_events:
                    del self._paused_events[task.input_path]
                
        except Exception as e:
            logger.error(f"Ошибка обработки видео {task.input_path}: {e}")
            raise
        except asyncio.CancelledError:
            logger.info(f"Обработка видео отменена: {task.input_path}")
            raise
    
    async def check_paused(self, input_path: str) -> None:
        """
        Проверяет, приостановлена ли задача, и ждёт если да.
        
        Args:
            input_path (str): Путь к видеофайлу.
        """
        while input_path in self._paused_tasks:
            logger.debug(f"Задача {input_path} приостановлена, ожидание...")
            if input_path in self._paused_events:
                await self._paused_events[input_path].wait()
            else:
                self._paused_events[input_path] = asyncio.Event()
                await self._paused_events[input_path].wait()
    
    async def _process_video_with_semaphore(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает видео с учетом ограничения параллелизма.
        
        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        async with self._processing_semaphore:
            await self.process_video(task)
    
    async def _process_queue(self) -> None:
        """
        Внутренний метод для непрерывной обработки очереди.
        
        Note:
            Работает в цикле, пока включен флаг _is_processing.
            Обрабатывает задачи по приоритету, с ограничением параллелизма.
            Учитывает приостановленные задачи.
        """
        logger.info(f"Процессор очереди запущен (макс. параллельно: {self.max_concurrent_videos})")

        while self._is_processing:
            try:
                if self.task_queue.is_empty():
                    if not self._active_tasks:
                        logger.debug("Очередь пуста, ожидание новых задач...")
                        await asyncio.sleep(1.0)
                    else:
                        await asyncio.sleep(0.5)
                    continue

                if len(self._active_tasks) >= self.max_concurrent_videos:
                    logger.debug(f"Достигнут лимит параллельных задач ({self.max_concurrent_videos}), ожидание...")
                    await asyncio.sleep(0.5)
                    continue

                task = self.task_queue.get_highest_priority_task()

                if task.input_path in self._cancelled_tasks:
                    logger.info(f"Задача {task.input_path} была отменена, пропускаем")
                    continue

                if task.input_path in self._paused_tasks:
                    logger.debug(f"Задача приостановлена, не должна быть в очереди: {task.input_path}")
                    continue

                asyncio.create_task(
                    self._process_video_with_semaphore(task)
                )
                
                logger.info(f"Задача запущена. Активных задач: {len(self._active_tasks)}/{self.max_concurrent_videos}")

            except IndexError:
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                logger.info("Процессор очереди остановлен")
                break
            except Exception as e:
                logger.exception(f"Ошибка в процессоре очереди: {e}")
                await asyncio.sleep(1.0)

        logger.info("Ожидание завершения активных задач...")
        if self._active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=30.0
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                logger.warning("Таймаут ожидания завершения активных задач")
        
        logger.info("Процессор очереди завершён")
    
    def pause_task(self, input_path: str) -> bool:
        """
        Приостанавливает задачу.
        
        Args:
            input_path (str): Путь к видеофайлу.
        
        Returns:
            bool: True если задача приостановлена, False если не найдена или уже отменена.
        """
        if input_path in self._cancelled_tasks:
            logger.warning(f"Нельзя приостановить отменённую задачу: {input_path}")
            return False
        
        if input_path in self._paused_tasks:
            logger.warning(f"Задача уже приостановлена: {input_path}")
            return False

        found_in_queue = False
        for task in list(self.task_queue._set):
            if task.input_path == input_path:
                self._paused_tasks[input_path] = task
                self._paused_events[input_path] = asyncio.Event()
                self.task_queue.remove_task(task)
                found_in_queue = True
                logger.info(f"Задача приостановлена и удалена из очереди: {input_path}")
                break

        if not found_in_queue and input_path in self.video_processor._processing_tasks:
            self._paused_tasks[input_path] = self.video_processor._processing_tasks[input_path]
            self._paused_events[input_path] = asyncio.Event()
            logger.info(f"Задача приостановлена (выполняющаяся): {input_path}")
            return True
        elif not found_in_queue:
            logger.warning(f"Задача не найдена для приостановки: {input_path}")
            return False
        
        return True
    
    def resume_task(self, input_path: str) -> bool:
        """
        Возобновляет приостановленную задачу.
        
        Args:
            input_path (str): Путь к видеофайлу.
        
        Returns:
            bool: True если задача возобновлена, False если не найдена или отменена.
        """
        if input_path in self._cancelled_tasks:
            logger.warning(f"Нельзя возобновить отменённую задачу: {input_path}")
            return False
        
        if input_path not in self._paused_tasks:
            logger.warning(f"Задача не была приостановлена: {input_path}")
            return False

        if input_path in self._paused_events:
            self._paused_events[input_path].set()
            del self._paused_events[input_path]

        task = self._paused_tasks[input_path]
        task.priority = 1
        self.task_queue.add_task(task)

        del self._paused_tasks[input_path]
        
        logger.info(f"Задача возобновлена: {input_path}")
        return True
    
    def cancel_task(self, input_path: str) -> bool:
        """
        Отменяет задачу.
        
        Args:
            input_path (str): Путь к видеофайлу.
        
        Returns:
            bool: True если задача отменена, False если не найдена.
        """
        self._cancelled_tasks.add(input_path)
        if input_path in self._paused_tasks:
            del self._paused_tasks[input_path]

        if input_path in self._paused_events:
            self._paused_events[input_path].set()
            del self._paused_events[input_path]

        for task in list(self.task_queue._set):
            if task.input_path == input_path:
                self.task_queue.remove_task(task)
                logger.info(f"Задача отменена и удалена из очереди: {input_path}")
                return True

        logger.info(f"Задача помечена как отменённая: {input_path}")
        return True
    
    def get_paused_tasks(self) -> List[str]:
        """Возвращает список приостановленных задач"""
        return list(self._paused_tasks.keys())
    
    def get_cancelled_tasks(self) -> List[str]:
        """Возвращает список отменённых задач"""
        return list(self._cancelled_tasks)
    
    def is_task_cancelled(self, input_path: str) -> bool:
        """Проверяет, отменена ли задача"""
        return input_path in self._cancelled_tasks
    
    def get_queue_stats(self) -> dict:
        """
        Получает статистику по очереди и активным задачам.
        
        Returns:
            dict: Словарь со статистикой:
                - queue_size: Количество задач в очереди
                - active_tasks: Количество активных задач
                - paused_tasks: Количество приостановленных задач
                - cancelled_tasks: Количество отменённых задач
                - max_concurrent: Максимальное количество параллельных задач
                - available_slots: Доступные слоты для обработки
        """
        return {
            "queue_size": len(self.task_queue),
            "active_tasks": len(self._active_tasks),
            "paused_tasks": len(self._paused_tasks),
            "cancelled_tasks": len(self._cancelled_tasks),
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