"""
Менеджер для управления очередью и обработкой видео задач.

Обеспечивает асинхронную обработку видеофайлов с поддержкой:
- Приоритетной очереди задач
- Параллельной обработки с ограничением по количеству
- Приостановки, возобновления и отмены отдельных задач
- Сбора статистики по состоянию очереди
"""
import asyncio
from typing import Optional, Set, List, Dict
import logging
from pathlib import Path

from .video_queue import AudioCleanupTask, PriorityTaskQueue, TaskStatus
from .video_processor import VideoProcessor
from .config import FFMPEG_CONFIG, QUEUE_CONFIG

logger = logging.getLogger(__name__)


class ProcessingManager:
    """
    Менеджер для управления очередью и обработкой видео задач.

    Attributes:
        task_queue (PriorityTaskQueue): Очередь задач с приоритетами
        video_processor (VideoProcessor): Процессор для обработки видео
        max_concurrent_videos (int): Максимальное количество одновременно обрабатываемых видео
        _is_processing (bool): Флаг активной обработки
        _processing_task (Optional[asyncio.Task]): Задача основного цикла обработки
        _active_tasks (Dict[str, asyncio.Task]): Активные задачи обработки (task_id -> task)
        _processing_semaphore (asyncio.Semaphore): Семафор для ограничения параллелизма
        _global_pause_event (asyncio.Event): Событие для глобальной паузы
        _all_tasks (Dict[str, AudioCleanupTask]): Хранилище всех задач (task_id -> task)
        _tasks_lock (asyncio.Lock): Блокировка для потокобезопасного доступа к хранилищу
    """

    def __init__(self):
        """
        Инициализирует менеджер обработки.
        """
        self.task_queue = PriorityTaskQueue()
        self.video_processor = VideoProcessor(
            ffmpeg_path=FFMPEG_CONFIG["ffmpeg_path"],
            ffprobe_path=FFMPEG_CONFIG["ffprobe_path"],
            max_concurrent_segments=QUEUE_CONFIG["audio_queue_max_size"],
        )
        self.max_concurrent_videos = QUEUE_CONFIG.get("max_concurrent_videos", 3)
        self._is_processing = False
        self._processing_task: Optional[asyncio.Task] = None
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._processing_semaphore = asyncio.Semaphore(self.max_concurrent_videos)

        self._global_pause_event = asyncio.Event()
        self._global_pause_event.set()

        self._all_tasks: Dict[str, AudioCleanupTask] = {}
        self._tasks_lock = asyncio.Lock()

    async def add_video_task(self, task: AudioCleanupTask) -> None:
        """
        Добавляет задачу в очередь обработки.

        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        async with self._tasks_lock:
            if task.task_id in self._all_tasks:
                logger.warning(f"Задача {task.task_id} уже существует")
                return

            for existing_task in self._all_tasks.values():
                if existing_task.input_path == task.input_path:
                    logger.warning(f"Задача для файла {task.input_path} уже существует")
                    return

            await task.set_status(TaskStatus.PENDING)
            self._all_tasks[task.task_id] = task
            await self.task_queue.add_task(task)
            logger.info(f"Задача добавлена: {task.input_path} (ID: {task.task_id})")

    async def get_task(self, task_id: str) -> Optional[AudioCleanupTask]:
        """
        Получает задачу по ID.

        Args:
            task_id (str): ID задачи.

        Returns:
            Optional[AudioCleanupTask]: Задача или None, если не найдена.
        """
        async with self._tasks_lock:
            return self._all_tasks.get(task_id)

    async def get_all_tasks(self) -> List[AudioCleanupTask]:
        """
        Получает все задачи.

        Returns:
            List[AudioCleanupTask]: Список всех задач.
        """
        async with self._tasks_lock:
            return list(self._all_tasks.values())

    async def start_processing(self) -> None:
        """Запускает обработку задач из очереди."""
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
        """Останавливает обработку задач."""
        self._is_processing = False

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                logger.info("Обработка очереди остановлена")

        if self._active_tasks:
            logger.info(f"Отмена {len(self._active_tasks)} активных задач")
            for task_id, task_obj in self._active_tasks.items():
                if not task_obj.done():
                    task_obj.cancel()

            try:
                await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
            except asyncio.CancelledError:
                logger.info("Все активные задачи остановлены")
            finally:
                self._active_tasks.clear()

    async def pause_task(self, task_id: str) -> bool:
        """
        Приостанавливает задачу.

        Args:
            task_id (str): ID задачи.

        Returns:
            bool: True если задача приостановлена.
        """
        async with self._tasks_lock:
            task = self._all_tasks.get(task_id)
            if not task:
                logger.warning(f"Задача не найдена: {task_id}")
                return False

            if task.get_status_sync() == TaskStatus.PENDING:
                await self.task_queue.remove_task(task)

            return await task.pause()

    async def resume_task(self, task_id: str) -> bool:
        """
        Возобновляет приостановленную задачу.

        Args:
            task_id (str): ID задачи.

        Returns:
            bool: True если задача возобновлена.
        """
        async with self._tasks_lock:
            task = self._all_tasks.get(task_id)
            if not task:
                logger.warning(f"Задача не найдена: {task_id}")
                return False

            current_status = task.get_status_sync()
            logger.info(f"resume_task: задача {task_id}, текущий статус={current_status.value}, прогресс={task.cleaned_segments}/{task.total_segments}")

            if current_status != TaskStatus.PAUSED:
                logger.warning(f"Задача {task_id} не приостановлена, статус: {current_status}")
                return False

            success = await task.resume()

            if success:
                logger.info(f"Задача возобновлена: {task_id}, статус изменён на PROCESSING, прогресс={task.cleaned_segments}/{task.total_segments}")

            return success

    async def cancel_task(self, task_id: str) -> bool:
        """
        Отменяет задачу.

        Args:
            task_id (str): ID задачи.

        Returns:
            bool: True если задача отменена.
        """
        async with self._tasks_lock:
            task = self._all_tasks.get(task_id)
            if not task:
                logger.warning(f"Задача не найдена: {task_id}")
                return False

            await self.task_queue.remove_task(task)

            active_task = self._active_tasks.get(task_id)
            if active_task and not active_task.done():
                active_task.cancel()

            return await task.cancel()

    async def check_global_pause(self) -> None:
        """Проверяет глобальную паузу."""
        await self._global_pause_event.wait()

    async def process_video(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает одно видео.

        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        try:
            logger.info(f"Начата обработка видео: {task.input_path} (ID: {task.task_id})")

            await task.set_status(TaskStatus.PROCESSING)

            await self.video_processor.process_video(task, self)

            if not task.is_cancelled():
                await task.set_status(TaskStatus.COMPLETED)
                logger.info(f"Завершена обработка видео: {task.input_path}")

        except asyncio.CancelledError:
            logger.info(f"Обработка видео отменена: {task.input_path}")
            await task.set_status(TaskStatus.CANCELLED)
            raise
        except Exception as e:
            logger.exception(f"Ошибка обработки видео {task.input_path}: {e}")
            await task.set_status(TaskStatus.FAILED)
            raise

    async def _process_video_with_semaphore(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает видео с учетом ограничения параллелизма.

        Args:
            task (AudioCleanupTask): Задача на обработку видео.
        """
        async with self._processing_semaphore:
            task_obj = asyncio.create_task(self.process_video(task))
            self._active_tasks[task.task_id] = task_obj

            try:
                await task_obj
            finally:
                self._active_tasks.pop(task.task_id, None)

    async def _process_queue(self) -> None:
        """
        Внутренний метод для непрерывной обработки очереди.
        """
        logger.info(f"Процессор очереди запущен (макс. параллельно: {self.max_concurrent_videos})")

        while self._is_processing:
            try:
                await self.check_global_pause()

                if len(self._active_tasks) >= self.max_concurrent_videos:
                    await asyncio.sleep(0.5)
                    continue

                task = await self.task_queue.get_highest_priority_task()
                if task is None:
                    await asyncio.sleep(0.5)
                    continue

                if task.status in [TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    continue

                asyncio.create_task(self._process_video_with_semaphore(task))
                logger.info(f"Задача запущена: {task.input_path} (ID: {task.task_id}). "
                          f"Активных: {len(self._active_tasks)}/{self.max_concurrent_videos}")

            except asyncio.CancelledError:
                logger.info("Процессор очереди остановлен")
                break
            except Exception as e:
                logger.exception(f"Ошибка в процессоре очереди: {e}")
                await asyncio.sleep(1.0)

        logger.info("Процессор очереди завершён")

    async def get_queue_stats(self) -> dict:
        """
        Получает статистику по очереди и активным задачам.

        Returns:
            dict: Словарь со статистикой (queue_size, active_tasks, paused_tasks,
                  completed_tasks, cancelled_tasks, failed_tasks, max_concurrent, available_slots)
        """
        async with self._tasks_lock:
            tasks = list(self._all_tasks.values())
            queue_size = 0
            processing_count = 0
            paused_count = 0
            completed_count = 0
            cancelled_count = 0
            failed_count = 0

            for task in tasks:
                status = task.get_status_sync()
                if status == TaskStatus.PENDING:
                    queue_size += 1
                elif status == TaskStatus.PROCESSING:
                    processing_count += 1
                elif status == TaskStatus.PAUSED:
                    paused_count += 1
                elif status == TaskStatus.COMPLETED:
                    completed_count += 1
                elif status == TaskStatus.CANCELLED:
                    cancelled_count += 1
                elif status == TaskStatus.FAILED:
                    failed_count += 1

            return {
                "queue_size": queue_size,
                "active_tasks": processing_count,
                "paused_tasks": paused_count,
                "completed_tasks": completed_count,
                "cancelled_tasks": cancelled_count,
                "failed_tasks": failed_count,
                "max_concurrent": self.max_concurrent_videos,
                "available_slots": self.max_concurrent_videos - processing_count,
            }

    async def clear_finished_tasks(self) -> int:
        """
        Удаляет завершённые, ошибочные и отменённые задачи из хранилища.

        Returns:
            int: Количество удаленных задач
        """
        async with self._tasks_lock:
            tasks_to_remove = []

            for task_id, task in self._all_tasks.items():
                status = task.get_status_sync()
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                task = self._all_tasks[task_id]
                await self.task_queue.remove_task(task)
                del self._all_tasks[task_id]
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]

            logger.info(f"Очищено {len(tasks_to_remove)} завершённых/отменённых задач")
            return len(tasks_to_remove)

    async def get_video_info(self, video_path: str) -> tuple[float, int]:
        """
        Получает информацию о видео через видео процессор.

        Args:
            video_path (str): Путь к видеофайлу.

        Returns:
            tuple[float, int]: (длительность в секундах, количество сегментов)
        """
        return await self.video_processor.get_video_info(video_path)