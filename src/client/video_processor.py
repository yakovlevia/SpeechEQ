"""
Основной класс для асинхронной обработки видеофайлов.
Координирует извлечение аудио, параллельную обработку сегментов,
сборку аудио и склейку с видео.
"""
import asyncio
import os
import json
import numpy as np
import datetime
from scipy.io import wavfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from .video_queue import AudioCleanupTask, TaskStatus
from .audio_processor import AudioProcessor, AudioSegment
from .config import AUDIO_CONFIG

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Основной класс для асинхронной обработки видеофайлов.

    Attributes:
        max_concurrent_segments (int): Максимальное количество параллельных сегментов.
        segment_semaphore (asyncio.Semaphore): Семафор для ограничения параллельной обработки.
        ffmpeg_path (str): Путь к ffmpeg.
        ffprobe_path (str): Путь к ffprobe.
        audio_processor (AudioProcessor): Процессор для работы с аудио.
        _processing_tasks (Dict[str, asyncio.Task]): Активные задачи обработки.
        _audio_segments (Dict[str, List[AudioSegment]]): Кэш извлечённых сегментов.
        _processed_segments (Dict[str, List[AudioSegment]]): Кэш обработанных сегментов.
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        max_concurrent_segments: int = 500,
        segment_semaphore: Optional[asyncio.Semaphore] = None
    ):
        """
        Инициализирует VideoProcessor.

        Args:
            ffmpeg_path (str): Путь к ffmpeg. По умолчанию "ffmpeg".
            ffprobe_path (str): Путь к ffprobe. По умолчанию "ffprobe".
            max_concurrent_segments (int): Максимум параллельных сегментов. По умолчанию 500.
            segment_semaphore (asyncio.Semaphore, optional): Внешний семафор. Если не передан, создаётся новый.
        """
        self.max_concurrent_segments = max_concurrent_segments
        
        if segment_semaphore is not None:
            self.segment_semaphore = segment_semaphore
            logger.info(f"VideoProcessor использует внешний семафор (макс={max_concurrent_segments})")
        else:
            self.segment_semaphore = asyncio.Semaphore(self.max_concurrent_segments)
            logger.info(f"VideoProcessor создал внутренний семафор (макс={max_concurrent_segments})")
            
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.audio_processor = AudioProcessor(ffmpeg_path)
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._audio_segments: Dict[str, List[AudioSegment]] = {}
        self._processed_segments: Dict[str, List[AudioSegment]] = {}

    async def calculate_total_segments(self, video_path: str) -> int:
        """
        Рассчитывает количество аудио сегментов для видео.

        Args:
            video_path (str): Путь к видеофайлу.

        Returns:
            int: Расчётное количество сегментов или 1000 при ошибке.
        """
        try:
            duration = await self.audio_processor.get_video_duration_fast(video_path)
            if duration <= 0:
                return 1000

            segment_duration = AUDIO_CONFIG["segment_duration"]
            overlap_duration = AUDIO_CONFIG["overlap_duration"]
            step = max(segment_duration - overlap_duration, 1)

            total_segments = max(1, int(np.ceil((duration - overlap_duration) / step)))
            logger.info(f"Видео {video_path}: длительность {duration:.1f}s, сегментов ~{total_segments}")
            return total_segments

        except Exception as e:
            logger.error(f"Ошибка при расчёте количества сегментов: {str(e)}")
            return 1000

    async def set_post_processing_status(self, task: AudioCleanupTask) -> None:
        """
        Переводит задачу в статус постобработки перед сборкой видео.

        Args:
            task (AudioCleanupTask): Задача для обновления статуса.
        """
        await task.set_post_processing()
        logger.info(f"Задача {task.task_id[:12]}... перешла в статус постобработки")

    async def cancel_processing_by_path(self, video_path: str) -> bool:
        """
        Отменяет обработку видео по пути.

        Args:
            video_path (str): Путь к видеофайлу.

        Returns:
            bool: True если задача найдена и отменена.
        """
        task = self._processing_tasks.get(video_path)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Обработка видео отменена: {video_path}")
                return True
        return False

    async def process_video(self, task: AudioCleanupTask, manager=None) -> None:
        """
        Асинхронно обрабатывает видео от начала до конца.

        Args:
            task (AudioCleanupTask): Задача для обработки.
            manager (ProcessingManager, optional): Менеджер обработки для проверки глобальной паузы.
        """
        try:
            logger.info(f"Начало обработки видео: {task.input_path}")

            if not os.path.exists(task.input_path):
                raise FileNotFoundError(f"Файл не найден: {task.input_path}")

            if manager:
                await manager.check_global_pause()

            if task.is_cancelled():
                logger.info(f"Задача отменена: {task.input_path}")
                return

            await task.set_status(TaskStatus.PROCESSING)
            
            if task.is_cancelled():
                logger.info(f"Задача отменена после установки статуса: {task.input_path}")
                return

            if task.duration <= 0:
                duration = await self.audio_processor.get_video_duration_fast(task.input_path)
                await task.set_duration(duration)
            else:
                duration = task.duration

            if task.is_cancelled():
                logger.info(f"Задача отменена после получения длительности: {task.input_path}")
                return

            if task.total_segments > 0:
                total_segments = task.total_segments
                logger.info(f"Используем предвычисленные сегменты: {total_segments}")
            else:
                total_segments = await self.calculate_total_segments(task.input_path)
                await task.set_total_segments(total_segments)

            logger.info(
                f"Видео {Path(task.input_path).name}: длительность {duration:.1f}s, "
                f"сегментов: {total_segments}, уже обработано: {task.cleaned_segments}"
            )

            input_path = Path(task.input_path)
            video_name = input_path.stem
            video_ext = input_path.suffix

            output_parent = Path(task.output_path).parent
            base_dir = output_parent

            video_output_dir = base_dir / ".video"
            audio_dir = base_dir / ".audio" / video_name
            clean_audio_dir = audio_dir / "clean"
            tmp_audio_dir = audio_dir / "tmp"

            video_output_dir.mkdir(parents=True, exist_ok=True)
            audio_dir.mkdir(parents=True, exist_ok=True)
            clean_audio_dir.mkdir(parents=True, exist_ok=True)
            tmp_audio_dir.mkdir(parents=True, exist_ok=True)

            video_output_path = video_output_dir / f"{video_name}{video_ext}"

            if task.is_cancelled():
                logger.info(f"Задача отменена перед загрузкой сегментов: {task.input_path}")
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
                    logger.warning(f"Не удалось загрузить список существующих сегментов: {e}")

            # ------------------------------------------------------------------
            # 1. ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА АУДИО СЕГМЕНТОВ
            # ------------------------------------------------------------------

            pending_tasks: set[asyncio.Task] = set()
            segment_count = len(existing_segments)
            segments_list: list[str] = list(existing_segments)

            if segment_count > 0:
                await task.update_progress(segment_count)
                logger.info(f"Восстановлен прогресс: {segment_count}/{total_segments} сегментов")

            loop = asyncio.get_running_loop()

            async for segment in self.audio_processor.extract_audio_segments(
                video_path=task.input_path,
                segment_duration=AUDIO_CONFIG["segment_duration"],
                overlap_duration=AUDIO_CONFIG["overlap_duration"],
                sample_rate=AUDIO_CONFIG["sample_rate"],
            ):
                if await task.should_exit():
                    logger.info(f"Задача приостановлена или отменена: {task.input_path}")
                    for t in pending_tasks:
                        t.cancel()
                    if segments_list:
                        try:
                            await loop.run_in_executor(
                                None,
                                lambda: self._write_segments_list(segments_list_path, segments_list)
                            )
                            logger.info("Список сегментов сохранён")
                        except Exception as e:
                            logger.warning(f"Не удалось сохранить список сегментов: {e}")
                    return

                if manager:
                    await manager.check_global_pause()

                segment_filename = f"{video_name}_segment_{segment.segment_id:04d}.wav"
                if segment_filename in existing_segments:
                    logger.debug(f"Сегмент {segment.segment_id} уже обработан, пропускаем")
                    continue

                seg_task = asyncio.create_task(
                    self._process_segment_limited(
                        segment,
                        task.handler,
                        task.handler_settings
                    )
                )
                pending_tasks.add(seg_task)

                done, pending_tasks = await asyncio.wait(
                    pending_tasks,
                    timeout=0.0,
                    return_when=asyncio.FIRST_COMPLETED
                )

                for finished in done:
                    if await task.should_exit():
                        logger.info(f"Задача приостановлена или отменена после сегмента: {task.input_path}")
                        for t in pending_tasks:
                            t.cancel()
                        if segments_list:
                            try:
                                await loop.run_in_executor(
                                    None,
                                    lambda: self._write_segments_list(segments_list_path, segments_list)
                                )
                                logger.info("Список сегментов сохранён")
                            except Exception as e:
                                logger.warning(f"Не удалось сохранить список сегментов: {e}")
                        return

                    if manager:
                        await manager.check_global_pause()

                    processed_segment = finished.result()
                    await self._save_processed_segment(processed_segment, clean_audio_dir, video_name, segments_list)
                    segment_count += 1
                    await task.increment_progress()

                    if segment_count % 50 == 0:
                        logger.info(f"Сегмент {segment_count} из {task.total_segments} обработан")

            if pending_tasks:
                done, _ = await asyncio.wait(pending_tasks)
                for finished in done:
                    if await task.should_exit():
                        logger.info(f"Задача приостановлена или отменена при финализации: {task.input_path}")
                        if segments_list:
                            try:
                                await loop.run_in_executor(
                                    None,
                                    lambda: self._write_segments_list(segments_list_path, segments_list)
                                )
                            except Exception as e:
                                logger.warning(f"Не удалось сохранить список сегментов: {e}")
                        return

                    if manager:
                        await manager.check_global_pause()

                    processed_segment = finished.result()
                    await self._save_processed_segment(processed_segment, clean_audio_dir, video_name, segments_list)
                    segment_count += 1
                    await task.increment_progress()

            logger.info(f"Фактически обработано {segment_count} сегментов")

            if segment_count == 0:
                raise RuntimeError("Не было обработано ни одного аудио сегмента")

            if segment_count != total_segments:
                logger.warning(
                    f"Расчётное количество сегментов ({total_segments}) "
                    f"не совпало с фактическим ({segment_count})"
                )
                await task.set_total_segments(segment_count)

            if await task.should_exit():
                logger.info(f"Задача приостановлена или отменена перед сборкой: {task.input_path}")
                if segments_list:
                    try:
                        await loop.run_in_executor(
                            None,
                            lambda: self._write_segments_list(segments_list_path, segments_list)
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось сохранить список сегментов: {e}")
                return

            # ------------------------------------------------------------------
            # 2. ПЕРЕХОД В СТАТУС ПОСТОБРАБОТКИ
            # ------------------------------------------------------------------
            await self.set_post_processing_status(task)

            if await task.should_exit():
                logger.info(f"Задача приостановлена или отменена после POST_PROCESSING: {task.input_path}")
                return

            # ------------------------------------------------------------------
            # 3. СОХРАНЕНИЕ ВИДЕО БЕЗ АУДИО
            # ------------------------------------------------------------------
            logger.info("Сохранение видео без аудио")
            await self._save_video_without_audio(task.input_path, video_output_path)

            # ------------------------------------------------------------------
            # 4. СОХРАНЕНИЕ СПИСКА СЕГМЕНТОВ
            # ------------------------------------------------------------------
            if segments_list:
                segments_list_path = clean_audio_dir / "segments_list.txt"
                await loop.run_in_executor(
                    None,
                    lambda: self._write_segments_list(segments_list_path, segments_list)
                )

            if await task.should_exit():
                logger.info(f"Задача приостановлена или отменена перед сборкой аудио: {task.input_path}")
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
                logger.info(f"Задача приостановлена или отменена перед склейкой: {task.input_path}")
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
                logger.info(f"Прогресс финальный: {task.cleaned_segments}/{task.total_segments}")

            # ------------------------------------------------------------------
            # 7. СОЗДАНИЕ ОТЧЕТА (SUMMARY)
            # ------------------------------------------------------------------
            summary_info = {
                "video_name": video_name,
                "original_video": str(task.input_path),
                "video_with_clean_audio": str(task.output_path),
                "audio_dir": str(audio_dir),
                "clean_audio_dir": str(clean_audio_dir),
                "tmp_audio_dir": str(tmp_audio_dir),
                "total_segments": segment_count,
                "processing_time": datetime.datetime.now().isoformat()
            }

            summary_path = audio_dir / "summary.json"
            await loop.run_in_executor(None, lambda: self._write_summary(summary_path, summary_info))

            # ------------------------------------------------------------------
            # 8. ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ
            # ------------------------------------------------------------------
            try:
                import shutil
                shutil.rmtree(tmp_audio_dir)
                logger.info(f"Удалена временная папка: {tmp_audio_dir}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временную папку {tmp_audio_dir}: {e}")

            logger.info(f"Обработка видео завершена: {video_name}, сегментов: {segment_count}")

        except asyncio.CancelledError:
            if 'segments_list' in locals() and segments_list and 'segments_list_path' in locals():
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: self._write_segments_list(segments_list_path, segments_list)
                    )
                    logger.info("Список сегментов сохранён при остановке")
                except Exception as e:
                    logger.warning(f"Не удалось сохранить список сегментов: {e}")
            
            logger.info(f"Обработка видео отменена: {task.input_path}")
            raise
        except Exception as e:
            await task.set_status(TaskStatus.FAILED)
            logger.exception(f"Ошибка при обработке видео {task.input_path}: {e}")
            raise

    async def assemble_audio(
        self,
        task: AudioCleanupTask,
        audio_dir: Path,
        segment_duration: float = None,
        overlap_duration: float = None,
    ) -> Path:
        """
        Собирает отдельные аудио сегменты в единый файл с усреднением перекрытий.

        Args:
            task (AudioCleanupTask): Задача обработки.
            audio_dir (Path): Директория с сегментами.
            segment_duration (float, optional): Длительность сегмента. По умолчанию из конфига.
            overlap_duration (float, optional): Длительность перекрытия. По умолчанию из конфига.

        Returns:
            Path: Путь к собранному аудиофайлу.
        """
        if segment_duration is None:
            segment_duration = AUDIO_CONFIG["segment_duration"]
        if overlap_duration is None:
            overlap_duration = AUDIO_CONFIG["overlap_duration"]
        
        segments_list_path = audio_dir / "segments_list.txt"
        if not segments_list_path.exists():
            raise FileNotFoundError(f"Список сегментов не найден: {segments_list_path}")

        with open(segments_list_path, 'r', encoding='utf-8') as f:
            segment_files = [
                line.strip().replace("file '", "").replace("'", "")
                for line in f.readlines()
            ]

        if not segment_files:
            raise RuntimeError("Нет сегментов для сборки аудио")

        segment_files.sort(key=lambda x: int(Path(x).stem.split("_")[-1]))

        logger.info(f"Начало сборки аудио: {len(segment_files)} сегментов, overlap={overlap_duration}s")

        sr, first_audio = wavfile.read(audio_dir / segment_files[0])
        first_audio = first_audio.astype(np.float32) / 32767.0
        
        overlap_samples = int(overlap_duration * sr)
        result_audio = first_audio.copy()
        
        logger.info(f"Первый сегмент: {len(result_audio)} сэмплов, sample_rate={sr}")
        
        for i, seg_file in enumerate(segment_files[1:], start=1):
            sr_seg, seg_data = wavfile.read(audio_dir / seg_file)
            seg_data = seg_data.astype(np.float32) / 32767.0
            
            if sr_seg != sr:
                raise ValueError(f"Несовпадающий sample_rate в сегменте {i}: {sr_seg} != {sr}")
            
            if overlap_samples > 0 and len(result_audio) >= overlap_samples and len(seg_data) > overlap_samples:
                overlap_end_idx = min(overlap_samples, len(seg_data))
                
                fade_out = np.linspace(1.0, 0.0, overlap_end_idx)
                fade_in = np.linspace(0.0, 1.0, overlap_end_idx)
                
                result_audio[-overlap_end_idx:] = (
                    result_audio[-overlap_end_idx:] * fade_out + 
                    seg_data[:overlap_end_idx] * fade_in
                )
                
                if len(seg_data) > overlap_end_idx:
                    result_audio = np.concatenate([result_audio, seg_data[overlap_end_idx:]])
            else:
                result_audio = np.concatenate([result_audio, seg_data])
        
        total_samples = len(result_audio)
        logger.info(f"После сборки всех сегментов: {total_samples} сэмплов ({total_samples/sr:.2f}s)")
        
        if task.duration > 0:
            expected_samples = int(task.duration * sr)
            
            if total_samples > expected_samples:
                logger.info(f"Обрезаем аудио с {total_samples} ({total_samples/sr:.2f}s) "
                        f"до {expected_samples} ({expected_samples/sr:.2f}s) сэмплов")
                result_audio = result_audio[:expected_samples]
            elif total_samples < expected_samples:
                shortage = expected_samples - total_samples
                logger.warning(f"Аудио короче ожидаемого на {shortage} сэмплов "
                            f"({shortage/sr:.2f}s), дополняем тишиной")
                padding = np.zeros(shortage, dtype=np.float32)
                result_audio = np.concatenate([result_audio, padding])
        
        result_audio_int16 = np.clip(result_audio * 32767, -32768, 32767).astype(np.int16)
        
        output_wav_path = audio_dir.parent / f"{Path(task.input_path).stem}_assembled.wav"
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: wavfile.write(output_wav_path, sr, result_audio_int16)
        )
        
        for seg_file in segment_files:
            try:
                (audio_dir / seg_file).unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить сегмент {seg_file}: {e}")
        
        final_duration = len(result_audio_int16) / sr
        logger.info(f"Собранное аудио сохранено: {output_wav_path}, "
                    f"длительность={final_duration:.2f}с, ожидалось={task.duration:.2f}с")
        
        return output_wav_path

    async def merge_audio_with_video(
        self,
        task: AudioCleanupTask,
        video_without_audio: str,
        assembled_audio_path: Path
    ) -> None:
        """
        Склеивает собранное аудио с видео без аудио.

        Args:
            task (AudioCleanupTask): Задача обработки видео.
            video_without_audio (str): Путь к видео без аудио.
            assembled_audio_path (Path): Путь к собранному аудио.
        """
        output_path = Path(task.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-i", video_without_audio,
            "-i", str(assembled_audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-y",
            str(output_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg при склейке аудио с видео: {stderr.decode()}")

        try:
            assembled_audio_path.unlink()
        except Exception as e:
            logger.warning(f"Не удалось удалить временное аудио {assembled_audio_path}: {e}")

        logger.info(f"Аудио успешно склеено с видео: {output_path}")

    async def _save_processed_segment(
        self,
        processed_segment: AudioSegment,
        audio_dir: Path,
        video_name: str,
        segments_list: list[str]
    ) -> None:
        """
        Сохраняет обработанный аудио сегмент в WAV файл.

        Args:
            processed_segment (AudioSegment): Обработанный сегмент.
            audio_dir (Path): Директория для сохранения.
            video_name (str): Имя видео для формирования имени файла.
            segments_list (list[str]): Список для добавления имени файла.
        """
        wav_filename = f"{video_name}_segment_{processed_segment.segment_id:04d}.wav"
        wav_path = audio_dir / wav_filename

        audio_data = processed_segment.audio_data
        if audio_data.dtype != np.int16:
            audio_data = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: wavfile.write(wav_path, processed_segment.sample_rate, audio_data)
        )

        segments_list.append(wav_filename)
        del processed_segment.audio_data
        del audio_data

    async def _process_segment_limited(
        self,
        segment: AudioSegment,
        handler,
        handler_settings
    ) -> AudioSegment:
        """
        Обрабатывает аудио сегмент с ограничением параллелизма через семафор.

        Args:
            segment (AudioSegment): Исходный сегмент.
            handler: Обработчик аудио.
            handler_settings: Настройки обработчика.

        Returns:
            AudioSegment: Обработанный сегмент.
        """
        async with self.segment_semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                self.audio_processor.process_audio_segment,
                segment,
                handler,
                handler_settings
            )

    def _write_segments_list(self, path: Path, segments_list: List[str]) -> None:
        """Синхронно записывает список сегментов в файл."""
        with open(path, 'w', encoding='utf-8') as f:
            for wav_file in segments_list:
                f.write(f"file '{wav_file}'\n")

    def _write_summary(self, path: Path, summary_info: Dict[str, Any]) -> None:
        """Синхронно записывает сводку обработки в JSON файл."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(summary_info, f, indent=2, ensure_ascii=False)

    async def _extract_metadata(self, video_path: str) -> Dict[str, Any]:
        """Извлекает метаданные видео с помощью ffprobe."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffprobe: {stderr.decode()}")

        return json.loads(stdout.decode())

    async def _save_video_without_audio(
        self,
        input_path: str,
        output_path: str
    ) -> None:
        """Сохраняет видео без аудио дорожки."""
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-an",
            "-c:v", "copy",
            "-y",
            str(output_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg при сохранении видео без аудио: {stderr.decode()}")

    async def _create_segments_report(
        self,
        video_path: str,
        output_dir: Path,
        task: AudioCleanupTask
    ) -> None:
        """Создаёт отчёт об аудио сегментах."""
        if video_path not in self._audio_segments:
            return

        segments = self._audio_segments[video_path]
        report_path = output_dir / f"{Path(video_path).stem}_segments_report.json"

        report_data = {
            "video_path": video_path,
            "task_info": {
                "priority": task.priority,
                "input_path": task.input_path,
                "output_path": task.output_path,
                "total_segments": task.total_segments,
                "cleaned_segments": task.cleaned_segments,
                "progress_percentage": await task.get_progress_percentage(),
                "is_completed": task.is_completed()
            },
            "audio_config": {
                "segment_duration": AUDIO_CONFIG["segment_duration"],
                "overlap_duration": AUDIO_CONFIG["overlap_duration"],
                "sample_rate": AUDIO_CONFIG["sample_rate"]
            },
            "segments": []
        }

        for segment in segments:
            segment_info = {
                "segment_id": segment.segment_id,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "duration": segment.duration,
                "sample_rate": segment.sample_rate,
                "data_shape": segment.audio_data.shape,
                "data_dtype": str(segment.audio_data.dtype),
                "fragment_path": f"/mnt/d/diplom/.audio/{Path(video_path).stem}/fragment_{segment.segment_id}"
            }
            report_data["segments"].append(segment_info)

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Отчёт о сегментах сохранён: {report_path}")

    async def process_multiple_videos(
        self,
        tasks: list[AudioCleanupTask],
        max_concurrent: int = 3
    ) -> None:
        """
        Обрабатывает несколько видео с ограничением параллелизма.

        Args:
            tasks (list[AudioCleanupTask]): Список задач.
            max_concurrent (int): Максимальное количество параллельных задач.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(task: AudioCleanupTask):
            async with semaphore:
                return await self.process_video(task)

        processing_tasks = [
            asyncio.create_task(process_with_semaphore(task))
            for task in tasks
        ]

        for i, task_obj in enumerate(tasks):
            self._processing_tasks[task_obj.input_path] = processing_tasks[i]

        try:
            await asyncio.gather(*processing_tasks)
        finally:
            for task_obj in tasks:
                self._processing_tasks.pop(task_obj.input_path, None)

    async def cancel_processing(self, input_path: str) -> bool:
        """
        Отменяет обработку конкретного видео.

        Args:
            input_path (str): Путь к видео.

        Returns:
            bool: True если задача отменена.
        """
        task = self._processing_tasks.get(input_path)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Обработка видео отменена: {input_path}")
                return True
        return False

    def get_processing_status(self) -> Dict[str, str]:
        """
        Получает статус всех активных задач обработки.

        Returns:
            Dict[str, str]: Словарь {путь_к_видео: статус}
        """
        status = {}
        for input_path, task in self._processing_tasks.items():
            if task.done():
                if task.exception():
                    status[input_path] = "failed"
                else:
                    status[input_path] = "completed"
            elif task.cancelled():
                status[input_path] = "cancelled"
            else:
                status[input_path] = "processing"
        return status

    def get_audio_segments(self, video_path: str) -> List[AudioSegment]:
        """
        Получает аудио сегменты для конкретного видео.

        Args:
            video_path (str): Путь к видео.

        Returns:
            List[AudioSegment]: Список сегментов.
        """
        return self._audio_segments.get(video_path, [])

    def get_processed_segments(self, video_path: str) -> List[AudioSegment]:
        """
        Получает обработанные аудио сегменты для конкретного видео.

        Args:
            video_path (str): Путь к видео.

        Returns:
            List[AudioSegment]: Список обработанных сегментов.
        """
        return self._processed_segments.get(video_path, [])