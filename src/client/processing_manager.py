"""
Менеджер для управления очередью и обработкой видео задач.

Обеспечивает асинхронную обработку видеофайлов с поддержкой:
- Приоритетной очереди задач
- Параллельной обработки с ограничением по количеству
- Приостановки, возобновления и отмены отдельных задач
- Сбора статистики по состоянию очереди
"""
import asyncio
from typing import Optional, List, Dict
import logging
from pathlib import Path

from .video_queue import AudioCleanupTask, PriorityTaskQueue, TaskStatus
from .video_processor import VideoProcessor
from .config import FFMPEG_CONFIG, QUEUE_CONFIG

logger = logging.getLogger(__name__)


class ProcessingManager:
    """
    Менеджер для управления очередью и обработкой видео задач.
    """

    def __init__(self):
        self.task_queue = PriorityTaskQueue()
        
        self.max_concurrent_videos = QUEUE_CONFIG.get("max_concurrent_videos", 3)
        self._processing_semaphore = asyncio.Semaphore(self.max_concurrent_videos)
        
        self.max_concurrent_segments = QUEUE_CONFIG.get("audio_queue_max_size", 500)
        self._segment_semaphore = asyncio.Semaphore(self.max_concurrent_segments)
        
        self.video_processor = VideoProcessor(
            ffmpeg_path=FFMPEG_CONFIG["ffmpeg_path"],
            ffprobe_path=FFMPEG_CONFIG["ffprobe_path"],
            segment_semaphore=self._segment_semaphore,
            max_concurrent_segments=self.max_concurrent_segments,
        )
        
        self._is_processing = False
        self._processing_task: Optional[asyncio.Task] = None
        self._active_tasks: Dict[str, asyncio.Task] = {}
        
        self._global_pause_event = asyncio.Event()
        self._global_pause_event.set()

        self._all_tasks: Dict[str, AudioCleanupTask] = {}
        self._tasks_lock = asyncio.Lock()
        
        self._task_start_times: Dict[str, float] = {}
        self._stats_update_task: Optional[asyncio.Task] = None

    async def add_video_task(self, task: AudioCleanupTask) -> None:
        """
        Добавляет задачу в очередь.
        
        Args:
            task: Задача для добавления
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
            logger.info(f"Задача добавлена: {task.input_path} (ID: {task.task_id[:12]}..., приоритет={task.priority})")

    async def get_task(self, task_id: str) -> Optional[AudioCleanupTask]:
        """Возвращает задачу по ID."""
        async with self._tasks_lock:
            return self._all_tasks.get(task_id)

    async def get_all_tasks(self) -> List[AudioCleanupTask]:
        """Возвращает все задачи."""
        async with self._tasks_lock:
            return list(self._all_tasks.values())

    async def start_processing(self) -> None:
        """Запускает обработку очереди."""
        if self._is_processing:
            logger.warning("Обработка уже запущена")
            return

        self._is_processing = True
        logger.info(f"Запуск обработки видео (макс. параллельно: {self.max_concurrent_videos})")

        self._processing_task = asyncio.create_task(self._process_queue())
        self._stats_update_task = asyncio.create_task(self._update_stats_periodically())

        try:
            await self._processing_task
        finally:
            self._is_processing = False

    async def stop_processing(self) -> None:
        """Останавливает обработку очереди."""
        self._is_processing = False

        if self._stats_update_task and not self._stats_update_task.done():
            self._stats_update_task.cancel()
            try:
                await self._stats_update_task
            except asyncio.CancelledError:
                pass

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                logger.info("Обработка очереди остановлена")

        if self._active_tasks:
            logger.info(f"Отмена {len(self._active_tasks)} активных задач")
            for task_obj in self._active_tasks.values():
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
            task_id: ID задачи

        Returns:
            True если задача приостановлена
        """
        async with self._tasks_lock:
            task = self._all_tasks.get(task_id)
            if not task:
                logger.warning(f"Задача не найдена: {task_id}")
                return False

            success = await task.pause()
            if success:
                await self.task_queue.update_task_priority(task)
                logger.info(f"Задача {task_id[:12]}... приостановлена, приоритет={task.priority} сохранён")
            return success

    async def resume_task(self, task_id: str) -> bool:
        """
        Возобновляет задачу.

        Args:
            task_id: ID задачи

        Returns:
            True если задача возобновлена
        """
        async with self._tasks_lock:
            task = self._all_tasks.get(task_id)
            if not task:
                logger.warning(f"Задача не найдена: {task_id}")
                return False

            current_status = task.get_status_sync()
            if current_status != TaskStatus.PAUSED:
                logger.warning(f"Задача {task_id[:12]}... не приостановлена, статус: {current_status}")
                return False

            success = await task.resume()
            if success:
                await self.task_queue.update_task_priority(task)
                logger.info(f"Задача {task_id[:12]}... возобновлена, приоритет={task.priority} сохранён")
            return success

    async def cancel_task(self, task_id: str) -> bool:
        """
        Отменяет задачу.

        Args:
            task_id: ID задачи

        Returns:
            True если задача отменена
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
                self._active_tasks.pop(task_id, None)
                logger.info(f"Активная задача {task_id[:12]}... отменена и удалена из активных")

            return await task.cancel()

    async def check_global_pause(self) -> None:
        """Проверяет глобальную паузу."""
        await self._global_pause_event.wait()

    async def process_video(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает видео задачу.
        
        Args:
            task: Задача для обработки
        """
        start_time = asyncio.get_event_loop().time()
        self._task_start_times[task.task_id] = start_time
        
        try:
            logger.info(f"Начата обработка видео: {Path(task.input_path).name} (ID: {task.task_id[:12]}...)")
            await task.set_status(TaskStatus.PROCESSING)
            await self.video_processor.process_video(task, self)

            if not task.is_cancelled() and task.get_status_sync() != TaskStatus.PAUSED:
                await task.set_status(TaskStatus.COMPLETED)
                logger.info(f"Завершена обработка видео: {Path(task.input_path).name}")

        except asyncio.CancelledError:
            logger.info(f"Обработка видео отменена: {Path(task.input_path).name}")
            await task.set_status(TaskStatus.CANCELLED)
            raise
        except Exception as e:
            logger.exception(f"Ошибка обработки видео {Path(task.input_path).name}: {e}")
            await task.set_status(TaskStatus.FAILED)
            raise
        finally:
            self._task_start_times.pop(task.task_id, None)

    async def _process_video_with_semaphore(self, task: AudioCleanupTask) -> None:
        """
        Обрабатывает видео с использованием централизованного семафора.
        
        Args:
            task: Задача для обработки
        """
        if task.task_id in self._active_tasks:
            logger.warning(f"Задача {task.task_id[:12]}... уже в активных, пропускаем")
            return
        
        logger.debug(f"Задача {task.task_id[:12]}... ожидает слот (приоритет={task.priority})")
        
        async with self._processing_semaphore:
            logger.debug(f"Задача {task.task_id[:12]}... получила слот. Активно: {len(self._active_tasks)}/{self.max_concurrent_videos}")
            
            if task.task_id in self._active_tasks:
                logger.warning(f"Задача {task.task_id[:12]}... уже активна, пропускаем")
                return
            
            task_obj = asyncio.create_task(self.process_video(task))
            self._active_tasks[task.task_id] = task_obj

            try:
                await task_obj
            except asyncio.CancelledError:
                logger.info(f"Задача {task.task_id[:12]}... отменена во время выполнения")
            finally:
                self._active_tasks.pop(task.task_id, None)
                logger.debug(f"Задача {task.task_id[:12]}... завершена. Активных: {len(self._active_tasks)}/{self.max_concurrent_videos}")

    async def _process_queue(self) -> None:
        """Внутренний метод для непрерывной обработки очереди."""
        logger.info(f"Процессор очереди запущен (макс. параллельно: {self.max_concurrent_videos})")

        while self._is_processing:
            try:
                await self.check_global_pause()

                # Очищаем завершённые задачи
                completed = [tid for tid, t in self._active_tasks.items() if t.done()]
                for tid in completed:
                    self._active_tasks.pop(tid, None)

                available_slots = self.max_concurrent_videos - len(self._active_tasks)
                if available_slots <= 0:
                    await asyncio.sleep(0.5)
                    continue

                task = await self.task_queue.get_highest_priority_task()
                if task is None:
                    await asyncio.sleep(0.2)
                    continue

                if task.task_id in self._active_tasks:
                    logger.warning(f"Задача {task.task_id[:12]}... уже запущена, пропускаем")
                    continue

                if task.status == TaskStatus.PAUSED:
                    logger.info(f"Задача {task.task_id[:12]}... приостановлена, возвращаем в очередь")
                    await self.task_queue.return_task(task)
                    continue

                if task.status in [TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    logger.debug(f"Задача {task.task_id[:12]}... в статусе {task.status.value}, пропускаем")
                    continue

                if task.status == TaskStatus.RESUMING:
                    await task.set_processing_from_resuming()

                logger.info(f"Задача {task.task_id[:12]}... (приоритет={task.priority}) отправляется. Свободно слотов: {available_slots}")
                asyncio.create_task(self._process_video_with_semaphore(task))
                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                logger.info("Процессор очереди остановлен")
                break
            except Exception as e:
                logger.exception(f"Ошибка в процессоре очереди: {e}")
                await asyncio.sleep(0.5)

        logger.info("Процессор очереди завершён")

    async def _update_stats_periodically(self) -> None:
        """Периодически обновляет статистику для мониторинга."""
        while self._is_processing:
            try:
                stats = await self.get_queue_stats()
                logger.debug(f"Статистика: активно={stats['active_tasks']}, "
                             f"очередь={stats['queue_size']}, "
                             f"пауза={stats['paused_tasks']}, "
                             f"свободно слотов={stats['available_slots']}")
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка при обновлении статистики: {e}")
                await asyncio.sleep(5)

    async def get_queue_stats(self) -> dict:
        """
        Возвращает статистику очереди.
        
        Returns:
            Словарь со статистикой
        """
        async with self._tasks_lock:
            tasks = list(self._all_tasks.values())
            queue_size = 0
            processing_count = 0
            paused_count = 0
            completed_count = 0
            cancelled_count = 0
            failed_count = 0
            resuming_count = 0
            post_processing_count = 0

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
                elif status == TaskStatus.RESUMING:
                    resuming_count += 1
                elif status == TaskStatus.POST_PROCESSING:
                    post_processing_count += 1

            active_count = processing_count + post_processing_count
            available_slots = self.max_concurrent_videos - active_count

            return {
                "queue_size": queue_size,
                "active_tasks": active_count,
                "paused_tasks": paused_count,
                "completed_tasks": completed_count,
                "cancelled_tasks": cancelled_count,
                "failed_tasks": failed_count,
                "resuming_tasks": resuming_count,
                "post_processing_tasks": post_processing_count,
                "max_concurrent": self.max_concurrent_videos,
                "available_slots": max(0, available_slots),
                "total_tasks": len(tasks),
            }

    async def clear_finished_tasks(self) -> int:
        """
        Очищает завершённые задачи.
        
        Returns:
            Количество удаленных задач
        """
        async with self._tasks_lock:
            tasks_to_remove = [
                task_id for task_id, task in self._all_tasks.items()
                if task.get_status_sync() in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ]

            for task_id in tasks_to_remove:
                task = self._all_tasks[task_id]
                await self.task_queue.remove_task(task)
                del self._all_tasks[task_id]
                self._active_tasks.pop(task_id, None)

            logger.info(f"Очищено {len(tasks_to_remove)} завершённых/отменённых задач")
            return len(tasks_to_remove)

    async def get_video_info(self, video_path: str) -> tuple[float, int]:
        """
        Получает информацию о видео.
        
        Args:
            video_path: Путь к видео
            
        Returns:
            Кортеж (длительность, количество сегментов)
        """
        # TODO: в VideoProcessor нет метода get_video_info, возможно, нужно реализовать
        return await self.video_processor.get_video_info(video_path)
    
    def get_semaphore_stats(self) -> dict:
        """
        Возвращает статистику по семафорам.
        
        Returns:
            Словарь со статистикой семафоров
        """
        return {
            "video_semaphore": {
                "max": self.max_concurrent_videos,
                "current_usage": len(self._active_tasks),
                "available": self.max_concurrent_videos - len(self._active_tasks)
            },
            "segment_semaphore": {
                "max": self.max_concurrent_segments,
                "current_value": getattr(self._segment_semaphore, '_value', 'unknown')
            }
        }