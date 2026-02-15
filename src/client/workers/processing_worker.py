#!/usr/bin/env python3
"""
Рабочий поток для обработки видео
"""
import asyncio
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class ProcessingWorker(QObject):
    """Рабочий класс для обработки видео в отдельном потоке"""

    progress_updated = Signal(str, int, int)
    task_finished = Signal(str, bool, str)
    task_started = Signal(str)

    def __init__(self, processing_manager):
        super().__init__()
        self.processing_manager = processing_manager
        self._running = True
        self._loop = None
        self._tasks = []
        self._processing = False
        self._main_task = None
    
    def setup_asyncio(self):
        """Настройка asyncio для потока (вызывается при запуске потока)"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logger.info("Рабочий поток: asyncio инициализирован")
            self._main_task = self._loop.create_task(self._main_processing_loop())
            self._loop.run_forever()
            
        except Exception as e:
            logger.error(f"Ошибка инициализации asyncio: {e}")
        finally:
            self._cleanup_loop()
    
    def _cleanup_loop(self):
        """Очистка цикла asyncio"""
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
    
    def process_tasks(self, tasks):
        """Запуск обработки задач (вызывается из главного потока)"""
        if not self._loop:
            logger.error("Рабочий поток: asyncio не инициализирован")
            return

        self._tasks.extend(tasks)
        logger.info(f"Рабочий поток: добавлено {len(tasks)} задач в очередь")
        if not self._processing:
            asyncio.run_coroutine_threadsafe(
                self._process_next_task(),
                self._loop
            )
    
    async def _main_processing_loop(self):
        """Главный цикл обработки задач"""
        logger.info("Рабочий поток: главный цикл запущен")
        
        try:
            while self._running:
                if self._tasks and not self._processing:
                    self._processing = True
                    await self._process_next_task()
                else:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Рабочий поток: главный цикл отменён")
        finally:
            logger.info("Рабочий поток: главный цикл завершен")
    
    async def _process_next_task(self):
        """Обработка следующей задачи из очереди"""
        if not self._tasks:
            self._processing = False
            return
        
        task = self._tasks.pop(0)
        
        try:
            logger.info(f"Рабочий поток: начало обработки {Path(task.input_path).name}")
            
            self.task_started.emit(task.input_path)
            await self.processing_manager.process_video(task)
            self.task_finished.emit(
                task.input_path, 
                True, 
                f"Успешно обработан: {Path(task.output_path).name}"
            )
            logger.info(f"Рабочий поток: завершена {Path(task.input_path).name}")
            
        except asyncio.CancelledError:
            logger.info(f"Рабочий поток: отмена {Path(task.input_path).name}")
            self.task_finished.emit(task.input_path, False, "Отменено пользователем")
        except Exception as e:
            logger.error(f"Рабочий поток: ошибка {Path(task.input_path).name}: {e}")
            self.task_finished.emit(task.input_path, False, str(e))
        finally:
            self._processing = False
            if self._tasks and self._running:
                self._loop.create_task(self._process_next_task())
    
    async def cancel_task(self, input_path: str):
        """Отмена конкретной задачи"""
        self._tasks = [t for t in self._tasks if t.input_path != input_path]
        try:
            await self.processing_manager.video_processor.cancel_processing_by_path(input_path)
            logger.info(f"Рабочий поток: задача отменена {input_path}")
        except Exception as e:
            logger.error(f"Рабочий поток: ошибка при отмене {input_path}: {e}")
    
    def stop(self):
        """Остановка рабочего потока"""
        logger.info("Рабочий поток: остановка...")
        self._running = False
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._shutdown_async(),
                self._loop
            )

            try:
                future.result(timeout=3.0)
            except TimeoutError:
                logger.warning("Рабочий поток: таймаут при остановке")
            except Exception as e:
                logger.error(f"Рабочий поток: ошибка при остановке: {e}")

            self._loop.call_soon_threadsafe(self._loop.stop)
    
    async def _shutdown_async(self):
        """Асинхронное завершение работы"""
        logger.info("Рабочий поток: асинхронное завершение...")
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass

        tasks = [t for t in asyncio.all_tasks(self._loop) 
                if t is not asyncio.current_task()]

        if tasks:
            logger.info(f"Рабочий поток: отмена {len(tasks)} задач")
            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)