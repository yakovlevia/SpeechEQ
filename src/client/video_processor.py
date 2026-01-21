# src/client/video_processor.py
import asyncio
import os
import subprocess
import json
import numpy as np
import datetime
from scipy.io import wavfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import asdict
import logging
import tempfile

from .video_queue import AudioCleanupTask
from .audio_processor import AudioProcessor, AudioSegment
from .config import FFMPEG_CONFIG, QUEUE_CONFIG, AUDIO_CONFIG, PATHS

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Класс для асинхронной обработки видео из AudioCleanupTask"""
    
    def __init__(
        self, 
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        max_concurrent_segments: int = 500
    ):
        """
        Инициализация процессора видео
        
        Args:
            audio_queue: Очередь для отправки аудио (лимит 500)
            ffmpeg_path: Путь к ffmpeg
            ffprobe_path: Путь к ffprobe
        """
        self.max_concurrent_segments = max_concurrent_segments
        self.segment_semaphore = asyncio.Semaphore(self.max_concurrent_segments)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.audio_processor = AudioProcessor(ffmpeg_path)
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._audio_segments: Dict[str, List[AudioSegment]] = {}
        self._processed_segments: Dict[str, List[AudioSegment]] = {}
    
    async def calculate_total_segments(self, video_path: str) -> int:
        """
        Рассчитать количество сегментов видео с учетом перекрытия.
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
            logger.error(f"Ошибка при расчете количества сегментов: {str(e)}")
            return 1000


    async def process_video(self, task: AudioCleanupTask) -> None:
        """
        Асинхронно обработать видео.
        Видео — последовательно.
        Аудио сегменты — параллельно, с лимитом из QUEUE_CONFIG.
        После обработки аудио сегментов создается файл списка сегментов,
        затем собирается новое аудио с учетом перекрытия
        и склеивается с видео без аудио. Все временные файлы очищаются.
        """
        try:
            logger.info(f"Начало обработки видео: {task.input_path}")

            if not os.path.exists(task.input_path):
                raise FileNotFoundError(f"Файл не найден: {task.input_path}")

            total_segments = await self.calculate_total_segments(task.input_path)
            task.set_total_segments(total_segments)

            logger.info(
                f"Видео {Path(task.input_path).name}: ожидается ~{total_segments} сегментов"
            )

            input_path = Path(task.input_path)
            video_name = input_path.stem
            video_ext = input_path.suffix
            base_dir = input_path.parent

            video_output_dir = base_dir / ".video"
            audio_dir = base_dir / ".audio" / video_name
            video_output_dir.mkdir(exist_ok=True)
            audio_dir.mkdir(parents=True, exist_ok=True)

            video_output_path = video_output_dir / f"{video_name}{video_ext}"

            logger.info(f"Выходные пути: {video_output_path}, {audio_dir}")

            # ------------------------------------------------------------------
            # 1. ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА АУДИО СЕГМЕНТОВ
            # ------------------------------------------------------------------

            logger.info(
                "Извлечение и параллельная обработка аудио сегментов "
                f"(max={self.max_concurrent_segments})"
            )

            pending_tasks: set[asyncio.Task] = set()
            segment_count = 0
            segments_list: list[str] = []

            async for segment in self.audio_processor.extract_audio_segments(
                video_path=task.input_path,
                segment_duration=AUDIO_CONFIG["segment_duration"],
                overlap_duration=AUDIO_CONFIG["overlap_duration"],
                sample_rate=AUDIO_CONFIG["sample_rate"],
            ):
                seg_task = asyncio.create_task(
                    self._process_segment_limited(segment)
                )
                pending_tasks.add(seg_task)

                if len(pending_tasks) >= self.max_concurrent_segments:
                    done, pending_tasks = await asyncio.wait(
                        pending_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for finished in done:
                        processed_segment = finished.result()
                        await self._save_processed_segment(
                            processed_segment,
                            audio_dir,
                            video_name,
                            segments_list
                        )
                        segment_count += 1
                        task.increment_progress()

            if pending_tasks:
                done, _ = await asyncio.wait(pending_tasks)
                for finished in done:
                    processed_segment = finished.result()
                    await self._save_processed_segment(
                        processed_segment,
                        audio_dir,
                        video_name,
                        segments_list
                    )
                    segment_count += 1
                    task.increment_progress()

            logger.info(f"Фактически обработано {segment_count} сегментов")

            if segment_count == 0:
                raise RuntimeError("Не было обработано ни одного аудио сегмента")

            if segment_count != total_segments:
                logger.warning(
                    f"Расчетное количество сегментов ({total_segments}) "
                    f"не совпало с фактическим ({segment_count})"
                )
                task.set_total_segments(segment_count)

            # ------------------------------------------------------------------
            # 2. Сохранение видео без аудио
            # ------------------------------------------------------------------

            logger.info("Сохранение видео без аудио")
            await self._save_video_without_audio(
                task.input_path,
                video_output_path
            )

            # ------------------------------------------------------------------
            # 3. Сохранение списка сегментов для совместимости и assemble_audio
            # ------------------------------------------------------------------

            if segments_list:
                segments_list_path = audio_dir / "segments_list.txt"
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._write_segments_list(
                        segments_list_path,
                        segments_list
                    )
                )
                logger.info(f"Создан список сегментов: {segments_list_path}")

            # ------------------------------------------------------------------
            # 4. Сборка нового аудио с учетом перекрытия
            # ------------------------------------------------------------------

            assembled_audio_path = await self.assemble_audio(
                task=task,
                audio_dir=audio_dir,
                segment_duration=AUDIO_CONFIG["segment_duration"],
                overlap_duration=AUDIO_CONFIG["overlap_duration"]
            )
            print("aaa\n")

            # ------------------------------------------------------------------
            # 5. Склейка нового аудио с видео
            # ------------------------------------------------------------------

            await self.merge_audio_with_video(
                task=task,
                video_without_audio=str(video_output_path),
                assembled_audio_path=assembled_audio_path
            )
            print("bbb\n")

            # ------------------------------------------------------------------
            # 6. Summary
            # ------------------------------------------------------------------

            summary_info = {
                "video_name": video_name,
                "original_video": str(task.input_path),
                "video_with_clean_audio": str(task.output_path),
                "audio_dir": str(audio_dir),
                "total_segments": segment_count,
                "processing_time": datetime.datetime.now().isoformat()
            }

            summary_path = audio_dir / "summary.json"
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._write_summary(summary_path, summary_info)
            )

            # ------------------------------------------------------------------
            # 7. Обновление задачи
            # ------------------------------------------------------------------

            task.cleaned_segments = segment_count

            logger.info(
                f"Обработка видео завершена: {video_name}, "
                f"сегментов: {segment_count}"
            )

        except Exception as e:
            logger.exception(
                f"Ошибка при обработке видео {task.input_path}: {e}"
            )
            raise

    async def assemble_audio(
        self,
        task: AudioCleanupTask,
        audio_dir: Path,
        segment_duration: float = AUDIO_CONFIG["segment_duration"],
        overlap_duration: float = AUDIO_CONFIG["merge_overlap"],
    ) -> Path:
        """
        Собрать аудио с усреднением перекрытий и удалить временные сегменты.
        """
        segments_list_path = audio_dir / "segments_list.txt"
        if not segments_list_path.exists():
            raise FileNotFoundError(f"Список сегментов не найден: {segments_list_path}")

        with open(segments_list_path, 'r', encoding='utf-8') as f:
            segment_files = [line.strip().replace("file '", "").replace("'", "") for line in f.readlines()]

        if not segment_files:
            raise RuntimeError("Нет сегментов для сборки аудио")

        sr, audio_data = wavfile.read(audio_dir / segment_files[0])
        audio_data = audio_data.astype(np.float32) / 32767.0
        assembled_audio = audio_data.copy()

        step_samples = int((segment_duration - overlap_duration) * sr)
        overlap_samples = int(overlap_duration * sr)

        for seg_file in segment_files[1:]:
            sr_seg, seg_data = wavfile.read(audio_dir / seg_file)
            seg_data = seg_data.astype(np.float32) / 32767.0

            if sr_seg != sr:
                raise ValueError(f"Несовпадающий sample_rate: {sr_seg} != {sr}")

            actual_overlap = min(overlap_samples, len(assembled_audio), len(seg_data))
            if actual_overlap > 0:
                assembled_audio[-actual_overlap:] = (
                    assembled_audio[-actual_overlap:] + seg_data[:actual_overlap]
                ) / 2

            remaining = seg_data[actual_overlap:]
            assembled_audio = np.concatenate([assembled_audio, remaining])

        assembled_audio_int16 = np.clip(assembled_audio * 32767, -32768, 32767).astype(np.int16)
        output_wav_path = audio_dir / f"{Path(task.input_path).stem}_assembled.wav"

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: wavfile.write(output_wav_path, sr, assembled_audio_int16)
        )

        for seg_file in segment_files:
            try:
                os.remove(audio_dir / seg_file)
            except Exception as e:
                logger.warning(f"Не удалось удалить сегмент {seg_file}: {e}")

        logger.info(f"Собранное аудио сохранено: {output_wav_path}")
        return output_wav_path

    async def merge_audio_with_video(
        self,
        task: AudioCleanupTask,
        video_without_audio: str,
        assembled_audio_path: Path
    ) -> None:
        """
        Склеить собранное аудио с видео без аудио и сохранить в task.output_path.
        Удалить временное аудио после склейки.
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

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg при склейке аудио с видео: {stderr.decode()}")

        try:
            os.remove(assembled_audio_path)
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
        Сохранить обработанный аудио сегмент в WAV файл
        """

        wav_filename = f"{video_name}_segment_{processed_segment.segment_id:04d}.wav"
        wav_path = audio_dir / wav_filename

        audio_data = processed_segment.audio_data

        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: wavfile.write(
                wav_path,
                processed_segment.sample_rate,
                audio_data
            )
        )

        segments_list.append(wav_filename)
        del processed_segment.audio_data
        del audio_data

    async def _process_segment_limited(
        self,
        segment: AudioSegment
    ) -> AudioSegment:
        async with self.segment_semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                self.audio_processor.process_audio_segment,
                segment
            )
    
    def _write_segments_list(self, path: Path, segments_list: List[str]) -> None:
        """Синхронная запись списка сегментов"""
        with open(path, 'w', encoding='utf-8') as f:
            for wav_file in segments_list:
                f.write(f"file '{wav_file}'\n")
    
    def _write_summary(self, path: Path, summary_info: Dict[str, Any]) -> None:
        """Синхронная запись summary"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(summary_info, f, indent=2, ensure_ascii=False)
    
    async def _extract_metadata(self, video_path: str) -> Dict[str, Any]:
        """Извлечь метаданные видео с помощью ffprobe"""
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
        """Сохранить видео без аудио с помощью ffmpeg"""
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
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg при сохранении видео без аудио: {stderr.decode()}")
    
    async def _create_segments_report(
        self, 
        video_path: str, 
        output_dir: Path,
        task: AudioCleanupTask
    ) -> None:
        """Создать отчет об аудио сегментах"""
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
                "progress_percentage": task.get_progress_percentage(),
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
        
        logger.info(f"Отчет о сегментах сохранен: {report_path}")
    
    async def process_multiple_videos(
        self, 
        tasks: list[AudioCleanupTask],
        max_concurrent: int = 3
    ) -> None:
        """
        Обработать несколько видео с ограничением на параллельное выполнение
        
        Args:
            tasks: Список задач для обработки
            max_concurrent: Максимальное количество параллельных задач
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
        """Отменить обработку конкретного видео"""
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
        """Получить статус всех задач обработки"""
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
        """Получить аудио сегменты для видео"""
        return self._audio_segments.get(video_path, [])
    
    def get_processed_segments(self, video_path: str) -> List[AudioSegment]:
        """Получить обработанные аудио сегменты для видео"""
        return self._processed_segments.get(video_path, [])