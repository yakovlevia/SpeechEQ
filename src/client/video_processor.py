"""
Основной класс для асинхронной обработки видеофайлов.

Координирует извлечение аудио, параллельную обработку сегментов,
сборку очищенного аудио и финальную склейку с видеодорожкой.
"""
import asyncio
import os
import json
import shutil
from typing import Dict, Any, List, Optional
import logging
import numpy as np
from scipy.io import wavfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from src.client.video_queue import AudioCleanupTask, TaskStatus
from src.client.audio_processor import AudioProcessor, AudioSegment
from src.client.config import AUDIO_CONFIG

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Основной класс для асинхронной обработки видеофайлов.

    Отвечает за полный цикл обработки:
    - Извлечение и сегментация аудио
    - Параллельная очистка сегментов через обработчик
    - Сборка сегментов с учётом overlap
    - Склейка очищенного аудио с оригинальным видео
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        max_concurrent_segments: int = 500,
        segment_semaphore: Optional[asyncio.Semaphore] = None
    ) -> None:
        """Инициализация процессора видео.

        Args:
            ffmpeg_path: Путь к исполняемому файлу ffmpeg.
            ffprobe_path: Путь к исполняемому файлу ffprobe.
            max_concurrent_segments: Максимальное количество параллельно
                обрабатываемых аудио-сегментов.
            segment_semaphore: Опциональный внешний семафор для контроля
                параллелизма. Если не передан — создаётся внутренний.
        """
        self.max_concurrent_segments = max_concurrent_segments
        if segment_semaphore is not None:
            self.segment_semaphore = segment_semaphore
            logger.info(f"Используется внешний семафор (макс={max_concurrent_segments})")
        else:
            self.segment_semaphore = asyncio.Semaphore(self.max_concurrent_segments)
            logger.info(f"Создан внутренний семафор (макс={max_concurrent_segments})")

        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.audio_processor = AudioProcessor(ffmpeg_path)

        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._audio_segments: Dict[str, List[AudioSegment]] = {}
        self._processed_segments: Dict[str, List[AudioSegment]] = {}

        # Отдельные executors:
        # - CPU-heavy задачи (ML/DSP обработка сегментов)
        # - I/O задачи (запись wav, списков, файловые операции)
        self._cpu_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="speecheq-cpu"
        )
        self._io_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="speecheq-io"
        )
        logger.info("Созданы executors: cpu_workers=1, io_workers=2")

    async def calculate_total_segments(self, video_path: str) -> int:
        """Рассчитывает ожидаемое количество аудио-сегментов для видео.

        Args:
            video_path: Путь к видеофайлу.

        Returns:
            int: Расчётное количество сегментов, или 1000 при ошибке.
        """
        try:
            duration = await self.audio_processor.get_video_duration_fast(video_path)
            if duration <= 0:
                return 1000
            segment_duration = AUDIO_CONFIG["segment_duration"]
            overlap_duration = AUDIO_CONFIG["overlap_duration"]
            step = max(segment_duration - overlap_duration, 1)
            total_segments = max(1, int(np.ceil((duration - overlap_duration) / step)))
            logger.info(
                f"Видео {Path(video_path).name}: длительность {duration:.1f}s, "
                f"сегментов ~{total_segments}"
            )
            return total_segments
        except Exception as e:
            logger.error(f"Ошибка при расчёте количества сегментов: {e}")
            return 1000

    async def set_post_processing_status(self, task: AudioCleanupTask) -> None:
        """Переключает задачу в статус постобработки.

        Args:
            task: Задача для обновления статуса.
        """
        await task.set_status(TaskStatus.POST_PROCESSING)
        logger.info(f"Задача {task.task_id[:12]}... перешла в постобработку")

    async def cancel_processing_by_path(self, video_path: str) -> bool:
        """Отменяет обработку видео по пути.

        Args:
            video_path: Путь к видеофайлу.

        Returns:
            bool: True если задача найдена и отменена, иначе False.
        """
        task = self._processing_tasks.get(video_path)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Обработка отменена: {video_path}")
                return True
        return False

    def _get_task_dirs(self, task: AudioCleanupTask):
        """Создаёт и возвращает пути к рабочим директориям задачи.

        Args:
            task: Задача, для которой создаются директории.

        Returns:
            tuple: Кортеж с путями (video_output_dir, video_output_path,
                   audio_dir, clean_audio_dir, tmp_audio_dir).
        """
        input_path = Path(task.input_path)
        video_name = input_path.stem
        video_ext = input_path.suffix
        output_parent = Path(task.output_path).parent
        base_dir = output_parent

        video_output_dir = base_dir / ".video"
        audio_dir = base_dir / ".audio" / task.task_id
        clean_audio_dir = audio_dir / "clean"
        tmp_audio_dir = audio_dir / "tmp"

        for directory in [video_output_dir, audio_dir, clean_audio_dir, tmp_audio_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        video_output_path = video_output_dir / f"{task.task_id}_noaudio{video_ext}"
        return video_output_dir, video_output_path, audio_dir, clean_audio_dir, tmp_audio_dir

    async def process_video(self, task: AudioCleanupTask, manager=None) -> None:
        """Основной метод обработки видеофайла.

        Координирует все этапы: извлечение аудио, параллельную очистку
        сегментов, сборку и финальную склейку с видео.

        Args:
            task: Задача обработки с параметрами и обработчиком.
            manager: Опциональный ProcessingManager для координации.
        """
        video_output_path = None
        pending_tasks: set[asyncio.Task] = set()

        try:
            logger.info(f"Начало обработки: {Path(task.input_path).name} (ID: {task.task_id[:12]}...)")

            if not os.path.exists(task.input_path):
                raise FileNotFoundError(f"Файл не найден: {task.input_path}")

            if manager:
                await manager.check_global_pause()

            if task.is_cancelled():
                logger.info(f"Задача отменена до начала: {task.input_path}")
                return

            await task.set_status(TaskStatus.PROCESSING)

            if task.handler.__class__.__name__ == "GRPCAudioHandler" and not getattr(task.handler, 'connected', True):
                logger.error("Нет подключения к серверу обработки")
                raise ConnectionError("Нет подключения к серверу обработки")

            if task.is_cancelled():
                return

            if task.duration <= 0:
                duration = await self.audio_processor.get_video_duration_fast(task.input_path)
                await task.set_duration(duration)
            else:
                duration = task.duration

            if task.is_cancelled():
                return

            if task.total_segments > 0:
                total_segments = task.total_segments
                logger.info(f"Используются предвычисленные сегменты: {total_segments}")
            else:
                total_segments = await self.calculate_total_segments(task.input_path)
                await task.set_total_segments(total_segments)

            logger.info(
                f"Видео {Path(task.input_path).name}: {duration:.1f}s, "
                f"сегментов: {total_segments}, обработано ранее: {task.cleaned_segments}"
            )

            _, video_output_path, audio_dir, clean_audio_dir, tmp_audio_dir = self._get_task_dirs(task)

            if task.is_cancelled():
                return

            existing_segments = set()
            segments_list_path = clean_audio_dir / "segments_list.txt"
            if segments_list_path.exists():
                try:
                    with open(segments_list_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            wav_file = line.strip().replace("file '", "").replace("'", "")
                            if wav_file:
                                existing_segments.add(wav_file)
                    logger.info(f"Найдено {len(existing_segments)} уже обработанных сегментов")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить список сегментов: {e}")

            # ------------------------------------------------------------------
            # 1. ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА АУДИО-СЕГМЕНТОВ
            # ------------------------------------------------------------------
            segment_count = len(existing_segments)
            segments_list: list[str] = list(existing_segments)

            if segment_count > 0:
                await task.update_progress(segment_count)
                logger.info(f"Прогресс восстановлен: {segment_count}/{total_segments}")

            async for segment in self.audio_processor.extract_audio_segments(
                video_path=task.input_path,
                segment_duration=AUDIO_CONFIG["segment_duration"],
                overlap_duration=AUDIO_CONFIG["overlap_duration"],
                sample_rate=AUDIO_CONFIG["sample_rate"],
                task_id=task.task_id,
            ):
                if await task.should_exit():
                    await self._cancel_pending_tasks(
                        pending_tasks,
                        segments_list_path,
                        segments_list,
                        task.input_path
                    )
                    return

                if manager:
                    await manager.check_global_pause()

                if task.handler.__class__.__name__ == "GRPCAudioHandler" and not getattr(task.handler, 'connected', True):
                    logger.error("Потеряно соединение с сервером обработки")
                    raise ConnectionError("Потеряно соединение с сервером обработки")

                segment_filename = f"{task.task_id}_segment_{segment.segment_id:04d}.wav"
                if segment_filename in existing_segments:
                    logger.debug(f"Сегмент {segment.segment_id} уже обработан")
                    continue

                seg_task = asyncio.create_task(
                    self._process_segment_limited(
                        segment,
                        task.handler,
                        task.handler_settings,
                        task.task_id
                    )
                )
                pending_tasks.add(seg_task)

                # Периодически забираем уже завершившиеся задачи
                done, pending_tasks = await asyncio.wait(
                    pending_tasks,
                    timeout=0.05,
                    return_when=asyncio.FIRST_COMPLETED
                )

                if done:
                    segment_count = await self._consume_finished_tasks(
                        finished_tasks=done,
                        task=task,
                        manager=manager,
                        clean_audio_dir=clean_audio_dir,
                        segments_list_path=segments_list_path,
                        segments_list=segments_list,
                        total_segments=total_segments,
                        segment_count=segment_count,
                    )

            # ------------------------------------------------------------------
            # ДОЖИДАЕМСЯ ВСЕХ ОСТАВШИХСЯ ЗАДАЧ И СОХРАНЯЕМ ИХ РЕЗУЛЬТАТЫ
            # ------------------------------------------------------------------
            if pending_tasks:
                logger.info(
                    f"Ожидание завершения оставшихся задач сегментов: {len(pending_tasks)}"
                )

                while pending_tasks:
                    done, pending_tasks = await asyncio.wait(
                        pending_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    segment_count = await self._consume_finished_tasks(
                        finished_tasks=done,
                        task=task,
                        manager=manager,
                        clean_audio_dir=clean_audio_dir,
                        segments_list_path=segments_list_path,
                        segments_list=segments_list,
                        total_segments=total_segments,
                        segment_count=segment_count,
                    )


            logger.info(f"Всего обработано сегментов: {segment_count}")

            if segment_count == 0:
                raise RuntimeError("Не было обработано ни одного аудио-сегмента")

            if segment_count != total_segments:
                logger.warning(
                    f"Расчётное ({total_segments}) и фактическое ({segment_count}) "
                    f"количество сегментов не совпадают"
                )
                await task.set_total_segments(segment_count)

            if await task.should_exit():
                await self._save_segments_list_safe(
                    segments_list_path,
                    segments_list,
                    task.input_path
                )
                return

            # ------------------------------------------------------------------
            # 2. ПЕРЕХОД В СТАТУС ПОСТОБРАБОТКИ
            # ------------------------------------------------------------------
            await self.set_post_processing_status(task)

            if await task.should_exit():
                return

            # ------------------------------------------------------------------
            # 3. СОХРАНЕНИЕ ВИДЕО БЕЗ АУДИО
            # ------------------------------------------------------------------
            logger.info("Сохранение видео без аудиодорожки")
            await self._save_video_without_audio(task.input_path, str(video_output_path))

            # ------------------------------------------------------------------
            # 4. СОХРАНЕНИЕ СПИСКА СЕГМЕНТОВ
            # ------------------------------------------------------------------
            if segments_list:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    self._io_executor,
                    lambda: self._write_segments_list(segments_list_path, segments_list)
                )

            if await task.should_exit():
                return

            # ------------------------------------------------------------------
            # 5. СБОРКА НОВОГО АУДИО
            # ------------------------------------------------------------------
            assembled_audio_path = await self.assemble_audio(
                task=task,
                audio_dir=clean_audio_dir,
                segment_duration=AUDIO_CONFIG["segment_duration"],
                overlap_duration=AUDIO_CONFIG["overlap_duration"],
            )

            if task.total_segments > 0:
                await task.update_progress(task.total_segments)
                logger.info("Прогресс обновлён до 100% после сборки аудио")

            if await task.should_exit():
                return

            # ------------------------------------------------------------------
            # 6. СКЛЕЙКА НОВОГО АУДИО С ВИДЕО
            # ------------------------------------------------------------------
            await self.merge_audio_with_video(
                task=task,
                video_without_audio=str(video_output_path),
                assembled_audio_path=assembled_audio_path
            )

            if task.total_segments > 0:
                await task.update_progress(task.total_segments)
                logger.info(f"Финальный прогресс: {task.cleaned_segments}/{task.total_segments}")

            logger.info(f"Обработка завершена: {Path(task.input_path).name}, сегментов: {segment_count}")

        except ConnectionError as e:
            logger.error(f"Ошибка соединения при обработке {Path(task.input_path).name}: {e}")
            if task.get_status_sync() != TaskStatus.FAILED:
                await task.set_status(TaskStatus.FAILED, str(e))
        except asyncio.CancelledError:
            logger.info(f"Обработка отменена: {Path(task.input_path).name}")
            await self._cancel_pending_tasks(
                pending_tasks,
                segments_list_path if 'segments_list_path' in locals() else None,
                segments_list if 'segments_list' in locals() else None,
                task.input_path
            )
            raise
        except Exception as e:
            logger.exception(f"Ошибка при обработке {Path(task.input_path).name}: {e}")
            if task.get_status_sync() != TaskStatus.FAILED:
                await task.set_status(TaskStatus.FAILED, str(e))
            raise
        finally:
            await self._cleanup_temp_files(video_output_path, task)


    async def _consume_finished_tasks(
        self,
        finished_tasks: set[asyncio.Task],
        task: AudioCleanupTask,
        manager,
        clean_audio_dir: Path,
        segments_list_path: Path,
        segments_list: list[str],
        total_segments: int,
        segment_count: int,
    ) -> int:
        """
        Забирает завершённые задачи сегментов, сохраняет их на диск
        и обновляет прогресс.

        Args:
            finished_tasks: Набор завершённых asyncio.Task.
            task: Текущая видео-задача.
            manager: ProcessingManager или None.
            clean_audio_dir: Папка для сохранения очищенных сегментов.
            segments_list_path: Путь к segments_list.txt.
            segments_list: Список имён сохранённых сегментов.
            total_segments: Общее количество сегментов.
            segment_count: Текущее количество уже сохранённых сегментов.

        Returns:
            int: Обновлённый segment_count.
        """
        for finished in finished_tasks:
            if await task.should_exit():
                await self._save_segments_list_safe(
                    segments_list_path,
                    segments_list,
                    task.input_path
                )
                return segment_count

            if manager:
                await manager.check_global_pause()

            if (
                task.handler.__class__.__name__ == "GRPCAudioHandler"
                and not getattr(task.handler, "connected", True)
            ):
                logger.error("Потеряно соединение с сервером обработки")
                raise ConnectionError("Потеряно соединение с сервером обработки")

            processed_segment = finished.result()

            await self._save_processed_segment(
                processed_segment,
                clean_audio_dir,
                task.task_id,
                segments_list
            )

            segment_count += 1
            await task.increment_progress()

            if segment_count % 10 == 0:
                logger.info(f"Обработано сегментов: {segment_count}/{total_segments}")

        return segment_count

    async def _cancel_pending_tasks(
        self,
        pending_tasks: set[asyncio.Task],
        segments_list_path: Optional[Path],
        segments_list: Optional[list[str]],
        input_path: str
    ) -> None:
        """Отменяет ожидающие задачи и сохраняет прогресс.

        Args:
            pending_tasks: Набор активных задач сегментов.
            segments_list_path: Путь к файлу списка сегментов.
            segments_list: Список имён обработанных сегментов.
            input_path: Путь к исходному видео для логирования.
        """
        for t in pending_tasks:
            if not t.done():
                t.cancel()
        if pending_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending_tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут при отмене задач для {Path(input_path).name}")
        if segments_list and segments_list_path:
            await self._save_segments_list_safe(segments_list_path, segments_list, input_path)

    async def _save_segments_list_safe(
        self,
        segments_list_path: Path,
        segments_list: list[str],
        input_path: str
    ) -> None:
        """Безопасно сохраняет список сегментов с обработкой ошибок.

        Args:
            segments_list_path: Путь к файлу списка.
            segments_list: Список имён файлов сегментов.
            input_path: Путь к видео для логирования.
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self._io_executor,
                lambda: self._write_segments_list(segments_list_path, segments_list)
            )
            logger.info("Список сегментов сохранён")
        except Exception as e:
            logger.warning(f"Не удалось сохранить список сегментов: {e}")

    async def _cleanup_temp_files(self, video_output_path: Optional[Path], task: AudioCleanupTask) -> None:
        """Удаляет временные файлы после обработки.

        Args:
            video_output_path: Путь к временному видео без аудио.
            task: Задача, содержащая пути для очистки.
        """
        if video_output_path and video_output_path.exists():
            try:
                video_output_path.unlink()
                logger.info(f"Удалено временное видео: {video_output_path.name}")
            except Exception as e:
                logger.warning(f"Не удалось удалить {video_output_path}: {e}")
        try:
            audio_dir_path = Path(task.output_path).parent / ".audio" / task.task_id
            if audio_dir_path.exists():
                shutil.rmtree(audio_dir_path)
                logger.info(f"Удалена временная папка: {audio_dir_path.name}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временную папку с аудио: {e}")

    async def assemble_audio(
        self,
        task: AudioCleanupTask,
        audio_dir: Path,
        segment_duration: float = None,
        overlap_duration: float = None
    ) -> Path:
        """Собирает итоговое аудио из обработанных сегментов."""
        if segment_duration is None:
            segment_duration = AUDIO_CONFIG["segment_duration"]

        if overlap_duration is None:
            overlap_duration = AUDIO_CONFIG["overlap_duration"]

        segments_list_path = audio_dir / "segments_list.txt"

        if not segments_list_path.exists():
            raise FileNotFoundError(f"Список сегментов не найден: {segments_list_path}")

        with open(segments_list_path, "r", encoding="utf-8") as f:
            segment_files = [
                line.strip().replace("file '", "").replace("'", "")
                for line in f.readlines()
            ]

        if not segment_files:
            raise RuntimeError("Нет сегментов для сборки аудио")

        segment_files.sort(key=lambda x: int(Path(x).stem.split("_")[-1]))

        logger.info(
            f"Сборка аудио: {len(segment_files)} сегментов, overlap={overlap_duration}s"
        )

        sr, first_audio = wavfile.read(audio_dir / segment_files[0])
        first_audio = first_audio.astype(np.float32) / 32767.0

        overlap_samples = int(overlap_duration * sr)
        segment_samples = int(segment_duration * sr)
        step_samples = segment_samples - overlap_samples

        if task.duration > 0:
            total_samples = int(task.duration * sr)
        else:
            total_samples = step_samples * (len(segment_files) - 1) + len(first_audio)

        logger.info(f"Финальный размер аудио: {total_samples} сэмплов")

        result_audio = np.zeros(total_samples, dtype=np.float32)

        fade_out = np.linspace(1.0, 0.0, overlap_samples, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, overlap_samples, dtype=np.float32)

        for i, seg_file in enumerate(segment_files):
            sr_seg, seg_data = wavfile.read(audio_dir / seg_file)

            if sr_seg != sr:
                raise ValueError(
                    f"Несовпадающий sample_rate в сегменте {i}: {sr_seg} != {sr}"
                )

            seg_data = seg_data.astype(np.float32) / 32767.0

            start = i * step_samples
            end = start + len(seg_data)

            if end > total_samples:
                seg_data = seg_data[: total_samples - start]
                end = total_samples

            if i == 0:
                result_audio[start:end] = seg_data
                continue

            overlap_start = start
            overlap_end = min(start + overlap_samples, total_samples)

            actual_overlap = overlap_end - overlap_start

            if actual_overlap > 0:
                result_audio[overlap_start:overlap_end] = (
                    result_audio[overlap_start:overlap_end] * fade_out[:actual_overlap]
                    + seg_data[:actual_overlap] * fade_in[:actual_overlap]
                )

            remainder_start = overlap_end
            remainder_len = len(seg_data) - actual_overlap

            if remainder_len > 0:
                result_audio[remainder_start:remainder_start + remainder_len] = seg_data[actual_overlap:]

        result_audio_int16 = np.clip(result_audio * 32767, -32768, 32767).astype(np.int16)

        output_wav_path = audio_dir.parent / f"{task.task_id}_assembled.wav"

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._io_executor,
            lambda: wavfile.write(output_wav_path, sr, result_audio_int16)
        )

        for seg_file in segment_files:
            try:
                (audio_dir / seg_file).unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить сегмент {seg_file}: {e}")

        logger.info(
            f"Аудио собрано: {output_wav_path.name}, "
            f"длительность={len(result_audio_int16)/sr:.2f}с"
        )

        return output_wav_path

    async def merge_audio_with_video(
        self,
        task: AudioCleanupTask,
        video_without_audio: str,
        assembled_audio_path: Path
    ) -> None:
        """Склеивает очищенное аудио с видеодорожкой.

        Args:
            task: Задача с путём для вывода.
            video_without_audio: Путь к видео без аудиодорожки.
            assembled_audio_path: Путь к собранному очищенному аудио.
        """
        output_path = Path(task.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path, "-i", video_without_audio, "-i", str(assembled_audio_path),
            "-c:v", "copy", "-c:a", "aac",
            "-map", "0:v:0", "-map", "1:a:0", "-y", str(output_path)
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg при склейке: {stderr.decode()}")

        try:
            assembled_audio_path.unlink()
        except Exception as e:
            logger.warning(f"Не удалось удалить временное аудио {assembled_audio_path.name}: {e}")

        logger.info(f"Аудио успешно склеено с видео: {output_path.name}")

    async def _save_processed_segment(
        self,
        processed_segment: AudioSegment,
        audio_dir: Path,
        task_id: str,
        segments_list: list[str]
    ) -> None:
        """Сохраняет обработанный аудио-сегмент на диск.

        Args:
            processed_segment: Обработанный сегмент с аудио-данными.
            audio_dir: Директория для сохранения.
            task_id: Идентификатор задачи для именования файла.
            segments_list: Список для добавления имени сохранённого файла.
        """
        wav_filename = f"{task_id}_segment_{processed_segment.segment_id:04d}.wav"
        wav_path = audio_dir / wav_filename
        audio_data = processed_segment.audio_data

        if audio_data.dtype != np.int16:
            audio_data = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)

        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(
                    self._io_executor,
                    lambda: wavfile.write(wav_path, processed_segment.sample_rate, audio_data)
                ),
                timeout=60.0
            )
            segments_list.append(wav_filename)
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при сохранении сегмента {wav_filename}")
            raise
        finally:
            # Освобождение памяти
            del processed_segment.audio_data
            del audio_data

    async def _process_segment_limited(
        self,
        segment: AudioSegment,
        handler,
        handler_settings,
        task_id: str = None
    ) -> AudioSegment:
        """Обрабатывает сегмент с ограничением параллелизма.

        Args:
            segment: Аудио-сегмент для обработки.
            handler: Обработчик для очистки аудио.
            handler_settings: Настройки обработчика.
            task_id: Опциональный идентификатор задачи.

        Returns:
            AudioSegment: Обработанный аудио-сегмент.
        """
        async with self.segment_semaphore:
            loop = asyncio.get_running_loop()
            processed = await loop.run_in_executor(
                self._cpu_executor,
                self.audio_processor.process_audio_segment,
                segment,
                handler,
                handler_settings
            )
            if task_id:
                processed.task_id = task_id + "_processed"
            return processed

    def _write_segments_list(self, path: Path, segments_list: List[str]) -> None:
        """Записывает список сегментов в файл для восстановления прогресса.

        Args:
            path: Путь к файлу списка.
            segments_list: Список имён файлов сегментов.
        """
        with open(path, 'w', encoding='utf-8') as f:
            for wav_file in segments_list:
                f.write(f"file '{wav_file}'\n")

    async def _extract_metadata(self, video_path: str) -> Dict[str, Any]:
        """Извлекает метаданные видео через ffprobe.

        Args:
            video_path: Путь к видеофайлу.

        Returns:
            dict: Словарь с метаданными видео.
        """
        cmd = [
            self.ffprobe_path, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffprobe: {stderr.decode()}")
        return json.loads(stdout.decode())

    async def _save_video_without_audio(self, input_path: str, output_path: str) -> None:
        """Сохраняет копию видео без аудиодорожки.

        Args:
            input_path: Путь к исходному видео.
            output_path: Путь для сохранения видео без аудио.
        """
        cmd = [self.ffmpeg_path, "-i", input_path, "-an", "-c:v", "copy", "-y", str(output_path)]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg: {stderr.decode()}")

    async def process_multiple_videos(self, tasks: list[AudioCleanupTask], max_concurrent: int = 3) -> None:
        """Обрабатывает несколько видео с ограничением параллелизма.

        Args:
            tasks: Список задач для обработки.
            max_concurrent: Максимальное количество параллельных обработок.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(task: AudioCleanupTask):
            async with semaphore:
                return await self.process_video(task)

        processing_tasks = [
            asyncio.create_task(process_with_semaphore(task)) for task in tasks
        ]
        for i, task_obj in enumerate(tasks):
            self._processing_tasks[task_obj.input_path] = processing_tasks[i]

        try:
            await asyncio.gather(*processing_tasks)
        finally:
            for task_obj in tasks:
                self._processing_tasks.pop(task_obj.input_path, None)

    async def cancel_processing(self, input_path: str) -> bool:
        """Отменяет обработку конкретного видео.

        Args:
            input_path: Путь к видео для отмены.

        Returns:
            bool: True если задача найдена и отменена.
        """
        task = self._processing_tasks.get(input_path)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Обработка отменена: {Path(input_path).name}")
                return True
        return False

    def get_processing_status(self) -> Dict[str, str]:
        """Возвращает статусы всех активных обработок.

        Returns:
            dict: Словарь {путь_к_видео: статус}.
        """
        status = {}
        for input_path, task in self._processing_tasks.items():
            if task.done():
                status[input_path] = "failed" if task.exception() else "completed"
            elif task.cancelled():
                status[input_path] = "cancelled"
            else:
                status[input_path] = "processing"
        return status

    def get_audio_segments(self, video_path: str) -> List[AudioSegment]:
        """Возвращает извлечённые аудио-сегменты для видео.

        Args:
            video_path: Путь к видеофайлу.

        Returns:
            List[AudioSegment]: Список сегментов или пустой список.
        """
        return self._audio_segments.get(video_path, [])

    def get_processed_segments(self, video_path: str) -> List[AudioSegment]:
        """Возвращает обработанные аудио-сегменты для видео.

        Args:
            video_path: Путь к видеофайлу.

        Returns:
            List[AudioSegment]: Список обработанных сегментов или пустой список.
        """
        return self._processed_segments.get(video_path, [])

    def shutdown_executors(self) -> None:
        """Корректно завершает внутренние executors."""
        try:
            self._cpu_executor.shutdown(wait=False, cancel_futures=False)
        except Exception as e:
            logger.warning(f"Ошибка остановки CPU executor: {e}")

        try:
            self._io_executor.shutdown(wait=False, cancel_futures=False)
        except Exception as e:
            logger.warning(f"Ошибка остановки IO executor: {e}")
