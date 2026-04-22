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

from src.client.video_queue import AudioCleanupTask, PriorityTaskQueue, TaskStatus
from src.client.video_processor import VideoProcessor
from src.client.config import FFMPEG_CONFIG, QUEUE_CONFIG

logger = logging.getLogger(__name__)


class ProcessingManager:
    """Менеджер для управления очередью и обработкой видео задач.

    Координирует выполнение задач очистки аудио, управляет пулом воркеров,
    отслеживает статусы задач и предоставляет статистику.
    """

    def __init__(self) -> None:
        """Инициализация менеджера обработки."""
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

    async def is_processing_active(self) -> bool:
        """Проверяет, активен ли процесс обработки очереди.

        Returns:
            bool: True, если обработка запущена, иначе False.
        """
        return self._is_processing

    async def restart_processing(self) -> None:
        """Перезапускает обработку очереди, если она не активна."""
        if not self._is_processing:
            logger.info("Перезапуск обработки очереди...")
            self._is_processing = True
            self._processing_task = asyncio.create_task(self._process_queue())
            self._stats_update_task = asyncio.create_task(self._update_stats_periodically())
            logger.info("Обработка очереди перезапущена")
        else:
            logger.debug("Обработка очереди уже активна")

    async def add_video_task(self, task: AudioCleanupTask) -> None:
        """Добавляет новую задачу в очередь обработки.

        Args:
            task: Экземпляр AudioCleanupTask для добавления.
        """
        async with self._tasks_lock:
            if task.task_id in self._all_tasks:
                logger.warning(f"Задача {task.task_id} уже существует")
                return
            await task.set_status(TaskStatus.PENDING)
            self._all_tasks[task.task_id] = task
            await self.task_queue.add_task(task)
            logger.info(
                f"Задача добавлена: {Path(task.input_path).name} "
                f"(ID: {task.task_id[:12]}..., приоритет={task.priority})"
            )

    async def get_task(self, task_id: str) -> Optional[AudioCleanupTask]:
        """Получает задачу по идентификатору.

        Args:
            task_id: Уникальный идентификатор задачи.

        Returns:
            AudioCleanupTask или None, если задача не найдена.
        """
        async with self._tasks_lock:
            return self._all_tasks.get(task_id)

    async def get_all_tasks(self) -> List[AudioCleanupTask]:
        """Возвращает список всех известных задач.

        Returns:
            List[AudioCleanupTask]: Копия списка всех задач.
        """
        async with self._tasks_lock:
            return list(self._all_tasks.values())

    async def start_processing(self) -> None:
        """Запускает основной цикл обработки очереди."""
        if self._is_processing:
            logger.warning("Обработка уже запущена")
            return
        self._is_processing = True
        logger.info(f"Запуск обработки (макс. параллельно: {self.max_concurrent_videos})")
        self._processing_task = asyncio.create_task(self._process_queue())
        self._stats_update_task = asyncio.create_task(self._update_stats_periodically())
        try:
            await self._processing_task
        finally:
            self._is_processing = False

    async def stop_processing(self) -> None:
        """Останавливает обработку очереди и фоновые задачи."""
        self._is_processing = False
        
        if self._stats_update_task and not self._stats_update_task.done():
            self._stats_update_task.cancel()
            try:
                await asyncio.wait_for(self._stats_update_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
                
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await asyncio.wait_for(self._processing_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.info("Обработка очереди остановлена")

    async def fail_all_active_tasks(self, reason: str = "Потеря соединения с сервером") -> int:
        """Помечает все активные задачи как неудачные.

        Args:
            reason: Причина сбоя для записи в статус задачи.

        Returns:
            int: Количество помеченных задач.
        """
        async with self._tasks_lock:
            failed_count = 0
            for task_id, task in self._all_tasks.items():
                status = task.get_status_sync()
                if status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
                    await task.set_status(TaskStatus.FAILED, reason)
                    failed_count += 1
                    logger.info(f"Задача {task_id[:12]}... помечена как ошибочная: {reason}")
            
            self._is_processing = False
            for task_id, active_task in list(self._active_tasks.items()):
                if not active_task.done():
                    active_task.cancel()
            return failed_count

    async def fail_remote_tasks(self, reason: str = "Потеря соединения с сервером") -> int:
        """Помечает как ошибочные только задачи с удалённым обработчиком.

        Args:
            reason: Причина сбоя для записи в статус задачи.

        Returns:
            int: Количество помеченных удалённых задач.
        """
        async with self._tasks_lock:
            failed_count = 0
            remote_task_ids = []
            
            for task_id, task in self._all_tasks.items():
                status = task.get_status_sync()
                if status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
                    continue

                is_remote = False
                if task.handler:
                    handler_class = task.handler.__class__.__name__
                    if handler_class == "GRPCAudioHandler":
                        is_remote = True
                    elif hasattr(task.handler, 'connected') and hasattr(task.handler, 'server_address'):
                        is_remote = True

                if is_remote:
                    await task.set_status(TaskStatus.FAILED, reason)
                    failed_count += 1
                    remote_task_ids.append(task_id)
                    logger.info(f"Удалённая задача {task_id[:12]}... помечена как ошибочная: {reason}")
                else:
                    logger.debug(f"Локальная задача {task_id[:12]}... пропущена")

            self._is_processing = False
            for task_id, active_task in list(self._active_tasks.items()):
                if task_id in remote_task_ids and not active_task.done():
                    active_task.cancel()
                    logger.info(f"Активная удалённая задача {task_id[:12]}... отменена")
            return failed_count

    async def cancel_remote_tasks(self) -> int:
        """Отменяет только задачи с удалённым обработчиком.

        Returns:
            int: Количество отменённых удалённых задач.
        """
        async with self._tasks_lock:
            cancelled_count = 0
            remote_task_ids = []
            
            for task_id, task in list(self._all_tasks.items()):
                status = task.get_status_sync()
                if status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
                    continue

                is_remote = False
                if task.handler:
                    handler_class = task.handler.__class__.__name__
                    if handler_class == "GRPCAudioHandler":
                        is_remote = True
                    elif hasattr(task.handler, 'connected') and hasattr(task.handler, 'server_address'):
                        is_remote = True

                if is_remote:
                    await self.task_queue.remove_task(task)
                    if await task.cancel():
                        cancelled_count += 1
                        remote_task_ids.append(task_id)
                        logger.info(f"Удалённая задача {task_id[:12]}... отменена")
                else:
                    logger.debug(f"Локальная задача {task_id[:12]}... пропущена")

            for task_id, active_task in list(self._active_tasks.items()):
                if task_id in remote_task_ids and not active_task.done():
                    active_task.cancel()
                    self._active_tasks.pop(task_id, None)
            return cancelled_count

    async def pause_task(self, task_id: str) -> bool:
        """Приостанавливает выполнение задачи.

        Args:
            task_id: Идентификатор задачи для приостановки.

        Returns:
            bool: True если задача успешно приостановлена, иначе False.
        """
        async with self._tasks_lock:
            task = self._all_tasks.get(task_id)
            if not task:
                logger.warning(f"Задача не найдена: {task_id}")
                return False
            success = await task.pause()
            if success:
                await self.task_queue.update_task_priority(task)
                logger.info(f"Задача {task_id[:12]}... приостановлена")
            return success

    async def resume_task(self, task_id: str) -> bool:
        """Возобновляет выполнение приостановленной задачи.

        Args:
            task_id: Идентификатор задачи для возобновления.

        Returns:
            bool: True если задача успешно возобновлена, иначе False.
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
                logger.info(f"Задача {task_id[:12]}... возобновлена")
            return success

    async def cancel_task(self, task_id: str) -> bool:
        """Отменяет задачу и удаляет её из активных.

        Args:
            task_id: Идентификатор задачи для отмены.

        Returns:
            bool: Результат операции отмены.
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
                logger.info(f"Активная задача {task_id[:12]}... отменена")
            return await task.cancel()

    async def check_global_pause(self) -> None:
        """Ожидает снятия глобальной паузы обработки."""
        await self._global_pause_event.wait()

    async def process_video(self, task: AudioCleanupTask) -> None:
        """Обрабатывает видеофайл в рамках задачи.

        Args:
            task: Задача содержащая параметры обработки.
        """
        start_time = asyncio.get_event_loop().time()
        self._task_start_times[task.task_id] = start_time
        try:
            logger.info(f"Начата обработка: {Path(task.input_path).name} (ID: {task.task_id[:12]}...)")
            await task.set_status(TaskStatus.PROCESSING)
            await self.video_processor.process_video(task, self)
            
            if task.get_status_sync() == TaskStatus.FAILED:
                logger.info(f"Задача {task.task_id[:12]}... завершена с ошибкой")
            elif not task.is_cancelled() and task.get_status_sync() != TaskStatus.PAUSED:
                await task.set_status(TaskStatus.COMPLETED)
                logger.info(f"Обработка завершена: {Path(task.input_path).name}")
                
        except asyncio.CancelledError:
            logger.info(f"Обработка отменена: {Path(task.input_path).name}")
            if task.get_status_sync() != TaskStatus.FAILED:
                await task.set_status(TaskStatus.CANCELLED)
            raise
        except ConnectionError as e:
            logger.error(f"Ошибка соединения при обработке {Path(task.input_path).name}: {e}")
            if task.get_status_sync() != TaskStatus.FAILED:
                await task.set_status(TaskStatus.FAILED, str(e))
        except Exception as e:
            logger.exception(f"Ошибка обработки {Path(task.input_path).name}: {e}")
            if task.get_status_sync() != TaskStatus.FAILED:
                await task.set_status(TaskStatus.FAILED, str(e))
            raise
        finally:
            self._task_start_times.pop(task.task_id, None)

    async def _process_video_with_semaphore(self, task: AudioCleanupTask) -> None:
        """Запускает обработку задачи с учётом лимита параллелизма.

        Args:
            task: Задача для обработки.
        """
        if task.task_id in self._active_tasks:
            logger.warning(f"Задача {task.task_id[:12]}... уже в активных, пропускаем")
            return
        if task.status == TaskStatus.FAILED:
            logger.debug(f"Задача {task.task_id[:12]}... в статусе FAILED, пропускаем")
            return

        logger.debug(f"Задача {task.task_id[:12]}... ожидает слот (приоритет={task.priority})")
        async with self._processing_semaphore:
            logger.debug(f"Задача {task.task_id[:12]}... получила слот. Активно: {len(self._active_tasks)}/{self.max_concurrent_videos}")
            
            if task.task_id in self._active_tasks or task.status == TaskStatus.FAILED:
                logger.debug(f"Задача {task.task_id[:12]}... уже обработана или в статусе FAILED")
                return

            task_obj = asyncio.create_task(self.process_video(task))
            self._active_tasks[task.task_id] = task_obj
            try:
                await task_obj
            except asyncio.CancelledError:
                logger.info(f"Задача {task.task_id[:12]}... отменена во время выполнения")
            except Exception as e:
                logger.error(f"Задача {task.task_id[:12]}... завершилась с ошибкой: {e}")
            finally:
                self._active_tasks.pop(task.task_id, None)
                logger.debug(f"Задача {task.task_id[:12]}... завершена. Активных: {len(self._active_tasks)}/{self.max_concurrent_videos}")

    async def _process_queue(self) -> None:
        """Основной цикл обработки очереди задач."""
        logger.info(f"Процессор очереди запущен (макс. параллельно: {self.max_concurrent_videos})")
        while self._is_processing:
            try:
                await self.check_global_pause()
                
                # Очистка завершённых задач из активных
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
                    logger.warning(f"Задача {task.task_id[:12]}... уже запущена")
                    continue
                if task.status == TaskStatus.FAILED:
                    logger.debug(f"Задача {task.task_id[:12]}... в статусе FAILED")
                    continue
                if task.status == TaskStatus.PAUSED:
                    logger.info(f"Задача {task.task_id[:12]}... приостановлена, возвращаем в очередь")
                    await self.task_queue.return_task(task)
                    continue
                if task.status in [TaskStatus.CANCELLED, TaskStatus.COMPLETED]:
                    logger.debug(f"Задача {task.task_id[:12]}... в статусе {task.status.value}")
                    continue
                
                # Проверка PENDING/RESUMING для корректного попадания новых задач в обработку
                if task.status in (TaskStatus.PENDING, TaskStatus.RESUMING):
                    if task.status == TaskStatus.RESUMING:
                        await task.set_processing_from_resuming()
                    logger.info(
                        f"Задача {task.task_id[:12]}... (приоритет={task.priority}) отправляется. "
                        f"Свободно слотов: {available_slots}"
                    )
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
        """Фоновая задача периодического обновления статистики."""
        while self._is_processing:
            try:
                stats = await self.get_queue_stats()
                logger.debug(
                    f"Статистика: активно={stats['active_tasks']}, очередь={stats['queue_size']}, "
                    f"пауза={stats['paused_tasks']}, свободно={stats['available_slots']}"
                )
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка при обновлении статистики: {e}")
                await asyncio.sleep(5)

    async def get_queue_stats(self) -> dict:
        """Собирает текущую статистику по очереди задач.

        Returns:
            dict: Словарь со статистикой очередей и задач.
        """
        async with self._tasks_lock:
            tasks = list(self._all_tasks.values())
            queue_size = processing_count = paused_count = completed_count = 0
            cancelled_count = failed_count = resuming_count = post_processing_count = 0
            
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
        """Удаляет завершённые, отменённые и неудачные задачи из памяти.

        Returns:
            int: Количество удалённых задач.
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
            logger.info(f"Очищено {len(tasks_to_remove)} завершённых задач")
            return len(tasks_to_remove)

    async def get_video_info(self, video_path: str) -> tuple[float, int]:
        """Получает техническую информацию о видеофайле.

        Args:
            video_path: Путь к видеофайлу.

        Returns:
            tuple[float, int]: Длительность в секундах и количество сегментов.
        """
        duration = await self.video_processor.audio_processor.get_video_duration_fast(video_path)
        total_segments = await self.video_processor.calculate_total_segments(video_path)
        return duration, total_segments

    def get_semaphore_stats(self) -> dict:
        """Возвращает статистику использования семафоров.

        Returns:
            dict: Статус видео- и сегмент-семафоров.
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