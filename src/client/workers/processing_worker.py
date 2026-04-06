"""
Рабочий класс для обработки видео в отдельном потоке.

Управляет асинхронной обработкой задач, мониторингом статуса и прогресса,
а также передачей сигналов в UI-поток через Qt-сигналы.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Set, List, Any
from PySide6.QtCore import QObject, Signal, Slot

from client.video_queue import TaskStatus

logger = logging.getLogger(__name__)


class ProcessingWorker(QObject):
    """Выполняет обработку видео задач в отдельном потоке с asyncio циклом."""

    task_added = Signal(str, str, str, int)
    task_status_changed = Signal(str, str)
    task_progress = Signal(str, int, int)
    task_duration = Signal(str, float, str)
    task_finished = Signal(str, bool, str)
    queue_stats_updated = Signal(dict)
    task_started = Signal(str)
    progress_updated = Signal(str, int, int)

    def __init__(self, processing_manager: Any) -> None:
        """
        Инициализирует рабочий поток обработки.

        Args:
            processing_manager: Менеджер обработки задач.

        Raises:
            Exception: При ошибках инициализации.
        """
        super().__init__()
        self.processing_manager = processing_manager
        self._running: bool = True
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        self._started_emitted: Set[str] = set()
        self._finished_emitted: Set[str] = set()
        self._last_progress: Dict[str, int] = {}
        self._last_status: Dict[str, str] = {}

    def setup_asyncio(self) -> None:
        """Настраивает и запускает цикл asyncio в текущем потоке."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logger.info("Рабочий поток: asyncio инициализирован")

            self._main_task = self._loop.create_task(self._main_processing_loop())
            self._monitor_task = self._loop.create_task(self._monitor_tasks())
            self._stats_task = self._loop.create_task(self._update_stats())
            self._loop.run_forever()

        except Exception as e:
            logger.error(f"Ошибка инициализации asyncio: {e}")
        finally:
            self._cleanup_loop()

    def _cleanup_loop(self) -> None:
        """Очищает ресурсы цикла asyncio."""
        if self._loop and self._loop.is_running():
            pending = asyncio.all_tasks(self._loop)

            if pending:
                logger.info(f"Рабочий поток: отмена {len(pending)} задач")
                for task in pending:
                    task.cancel()

                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            self._loop.stop()
            self._loop.close()
            logger.info("Рабочий поток: цикл asyncio очищен")

    @Slot(list)
    def add_tasks(self, tasks: List[Any]) -> None:
        """
        Добавляет задачи в очередь.

        Args:
            tasks: Список объектов AudioCleanupTask для добавления в очередь обработки.

        Raises:
            RuntimeError: Если asyncio цикл не инициализирован.
        """
        if not self._loop:
            logger.error("Рабочий поток: asyncio не инициализирован")
            return

        asyncio.run_coroutine_threadsafe(
            self._add_tasks_async(tasks),
            self._loop
        )

    async def _add_tasks_async(self, tasks: List[Any]) -> None:
        """
        Асинхронно добавляет задачи в менеджер обработки.

        Args:
            tasks: Список объектов AudioCleanupTask для добавления.

        Raises:
            Exception: При ошибках добавления задачи.
        """
        for task in tasks:
            await self.processing_manager.add_video_task(task)
            self.task_added.emit(task.task_id, task.input_path, task.output_path, task.total_segments)

            if task.duration > 0:
                self.task_duration.emit(task.task_id, task.duration, task.duration_formatted)

            logger.info(f"Добавлена задача: {task.input_path} (ID: {task.task_id}, сегментов: {task.total_segments})")

    @Slot(str)
    def pause_task(self, task_id: str) -> None:
        """
        Приостанавливает выполнение задачи.

        Args:
            task_id: Уникальный идентификатор задачи для приостановки.

        Raises:
            RuntimeError: Если asyncio цикл не инициализирован.
        """
        if not self._loop:
            return

        asyncio.run_coroutine_threadsafe(
            self._pause_task_async(task_id),
            self._loop
        )

    async def _pause_task_async(self, task_id: str) -> None:
        """
        Асинхронно приостанавливает задачу.

        Args:
            task_id: Уникальный идентификатор задачи для приостановки.
        """
        success = await self.processing_manager.pause_task(task_id)
        if success:
            self.task_status_changed.emit(task_id, TaskStatus.PAUSED.value)
            logger.info(f"Задача приостановлена: {task_id}")

    @Slot(str)
    def resume_task(self, task_id: str) -> None:
        """
        Возобновляет выполнение приостановленной задачи.

        Args:
            task_id: Уникальный идентификатор задачи для возобновления.

        Raises:
            RuntimeError: Если asyncio цикл не инициализирован.
        """
        if not self._loop:
            return

        asyncio.run_coroutine_threadsafe(
            self._resume_task_async(task_id),
            self._loop
        )

    async def _resume_task_async(self, task_id: str) -> None:
        """
        Асинхронно возобновляет задачу.

        Args:
            task_id: Уникальный идентификатор задачи для возобновления.
        """
        success = await self.processing_manager.resume_task(task_id)
        if success:
            logger.info(f"Задача возобновлена: {task_id}")
            if task_id in self._started_emitted:
                self._started_emitted.remove(task_id)
            if task_id in self._last_progress:
                del self._last_progress[task_id]

    @Slot(list)
    def cancel_tasks(self, task_ids: List[str]) -> None:
        """
        Отменяет выполнение задач.

        Args:
            task_ids: Список уникальных идентификаторов задач для отмены.

        Raises:
            RuntimeError: Если asyncio цикл не инициализирован.
        """
        if not self._loop:
            return

        asyncio.run_coroutine_threadsafe(
            self._cancel_tasks_async(task_ids),
            self._loop
        )

    async def _cancel_tasks_async(self, task_ids: List[str]) -> None:
        """
        Асинхронно отменяет задачи.

        Args:
            task_ids: Список уникальных идентификаторов задач для отмены.
        """
        for task_id in task_ids:
            success = await self.processing_manager.cancel_task(task_id)
            if success:
                self.task_status_changed.emit(task_id, TaskStatus.CANCELLED.value)
                self._emit_task_finished(task_id, False, "Отменено пользователем")
                logger.info(f"Задача отменена: {task_id}")

    @Slot()
    def cancel_all_tasks(self) -> None:
        """
        Отменяет все активные задачи (вызывается из UI при отключении от сервера).
        """
        if not self._loop:
            logger.error("Рабочий поток: asyncio не инициализирован")
            return

        asyncio.run_coroutine_threadsafe(
            self._cancel_all_tasks_async(),
            self._loop
        )

    async def _cancel_all_tasks_async(self) -> None:
        """
        Асинхронно отменяет ТОЛЬКО задачи, использующие удалённый обработчик.

        Raises:
            Exception: При ошибках отмены задач.
        """
        try:
            cancelled_count = await self.processing_manager.cancel_remote_tasks()
            logger.info(f"Отменено {cancelled_count} удалённых задач при отключении пользователя")
        except Exception as e:
            logger.error(f"Ошибка при отмене удалённых задач: {e}")

    @Slot()
    def restart_processing(self) -> None:
        """Перезапускает обработку очереди."""
        if not self._loop:
            logger.error("Рабочий поток: asyncio не инициализирован")
            return

        asyncio.run_coroutine_threadsafe(
            self._restart_processing_async(),
            self._loop
        )

    async def _restart_processing_async(self) -> None:
        """
        Асинхронно перезапускает обработку очереди.

        Raises:
            Exception: При ошибках перезапуска.
        """
        try:
            if not await self.processing_manager.is_processing_active():
                logger.info("Перезапуск обработки очереди...")
                asyncio.create_task(self.processing_manager.start_processing())
                logger.info("Обработка очереди перезапущена")
            else:
                logger.debug("Обработка очереди уже активна")
        except Exception as e:
            logger.error(f"Ошибка при перезапуске обработки: {e}")

    async def _main_processing_loop(self) -> None:
        """Главный цикл обработки задач. Запускает менеджер обработки."""
        logger.info("Рабочий поток: главный цикл запущен")

        try:
            await self.processing_manager.start_processing()
        except asyncio.CancelledError:
            logger.info("Рабочий поток: главный цикл отменён")
        except Exception as e:
            logger.error(f"Ошибка в главном цикле: {e}")
        finally:
            logger.info("Рабочий поток: главный цикл завершен")

    def _emit_task_started(self, task_id: str) -> None:
        """
        Отправляет сигнал о начале задачи, если он ещё не был отправлен.

        Args:
            task_id: Уникальный идентификатор задачи.
        """
        if task_id not in self._started_emitted:
            self._started_emitted.add(task_id)
            self.task_started.emit(task_id)
            logger.debug(f"Отправлен сигнал task_started: {task_id}")

    def _emit_task_finished(self, task_id: str, success: bool, message: str) -> None:
        """
        Отправляет сигнал о завершении задачи, если он ещё не был отправлен.

        Args:
            task_id: Уникальный идентификатор задачи.
            success: Флаг успешного выполнения задачи.
            message: Сообщение о результате выполнения.
        """
        if task_id not in self._finished_emitted:
            self._finished_emitted.add(task_id)
            self.task_finished.emit(task_id, success, message)
            logger.info(f"Отправлен сигнал task_finished: {task_id}, success={success}")

    async def _monitor_tasks(self) -> None:
        """Мониторит статус и прогресс задач, отправляет соответствующие сигналы."""
        while self._running:
            try:
                tasks = await self.processing_manager.get_all_tasks()
                for task in tasks:
                    status = task.get_status_sync()
                    current, total, percent = task.get_progress_sync()

                    self.task_status_changed.emit(task.task_id, status.value)

                    if status in (TaskStatus.PROCESSING, TaskStatus.POST_PROCESSING):
                        if status == TaskStatus.PROCESSING:
                            self._emit_task_started(task.task_id)

                        if total > 0:
                            self.task_progress.emit(task.task_id, current, total)
                            self.progress_updated.emit(task.task_id, current, total)
                    elif status == TaskStatus.RESUMING:
                        self._emit_task_started(task.task_id)
                        logger.debug(f"Задача {task.task_id} возобновляется")
                    else:
                        if self._last_status.get(task.task_id) != status.value:
                            logger.debug(f"Задача {task.task_id} в статусе {status.value}")
                            self._last_status[task.task_id] = status.value

                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в мониторе задач: {e}")
                await asyncio.sleep(1)

    async def _update_stats(self) -> None:
        """Периодически обновляет и отправляет статистику очереди."""
        while self._running:
            try:
                stats = await self.processing_manager.get_queue_stats()
                self.queue_stats_updated.emit(stats)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка при обновлении статистики: {e}")
                await asyncio.sleep(2)

    def stop(self) -> None:
        """Останавливает рабочий поток и освобождает ресурсы."""
        logger.info("Рабочий поток: остановка...")
        self._running = False

        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._shutdown_async(),
                self._loop
            )

            try:
                future.result(timeout=5.0)
            except TimeoutError:
                logger.warning("Рабочий поток: таймаут при остановке")
            except Exception as e:
                logger.error(f"Рабочий поток: ошибка при остановке: {e}")

            self._loop.call_soon_threadsafe(self._loop.stop)

    async def _shutdown_async(self) -> None:
        """
        Асинхронно завершает работу всех задач и отменяет корутины.

        Raises:
            Exception: При ошибках завершения задач.
        """
        logger.info("Рабочий поток: асинхронное завершение...")

        await self.processing_manager.stop_processing()

        await asyncio.sleep(0.5)

        tasks_to_cancel: List[asyncio.Task] = []

        if self._main_task and not self._main_task.done():
            tasks_to_cancel.append(self._main_task)

        if self._monitor_task and not self._monitor_task.done():
            tasks_to_cancel.append(self._monitor_task)

        if self._stats_task and not self._stats_task.done():
            tasks_to_cancel.append(self._stats_task)

        if hasattr(self.processing_manager, '_active_tasks'):
            for task in self.processing_manager._active_tasks.values():
                if not task.done():
                    tasks_to_cancel.append(task)

        if tasks_to_cancel:
            logger.info(f"Отмена {len(tasks_to_cancel)} задач рабочего потока")
            for task in tasks_to_cancel:
                task.cancel()

            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning("Таймаут при отмене задач рабочего потока")

        logger.info("Рабочий поток: асинхронное завершение выполнено")