"""
Модуль для обработки аудио из видеофайлов.

Содержит классы для извлечения аудио сегментов из видео,
их предварительной обработки и чтения WAV-файлов.
"""
import asyncio
import os
import subprocess
import json
import numpy as np
import wave
import io
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any, AsyncGenerator
import logging
import tempfile
from .config import FFMPEG_CONFIG
from processing.handlers.base import AudioHandler
from processing.core.settings import ProcessingSettings


logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """
    Класс для представления аудио сегмента, извлеченного из видео.
    
    Attributes:
        segment_id (int): Уникальный идентификатор сегмента.
        start_time (float): Время начала сегмента в секундах.
        end_time (float): Время окончания сегмента в секундах.
        duration (float): Длительность сегмента в секундах.
        audio_data (np.ndarray): Аудио данные в формате float32.
        sample_rate (int): Частота дискретизации аудио.
        video_path (str): Путь к исходному видеофайлу.
        task_id (str): Идентификатор задачи обработки.
    """
    segment_id: int
    start_time: float
    end_time: float
    duration: float
    audio_data: np.ndarray
    sample_rate: int
    video_path: str
    task_id: str


class AudioProcessor:
    """
    Основной класс для обработки аудио из видеофайлов.
    
    Предоставляет методы для извлечения аудио сегментов из видео
    и их предварительной обработки.
    
    Attributes:
        ffmpeg_path (str): Путь к исполняемому файлу ffmpeg.
        ffmpeg_semaphore (asyncio.Semaphore): Семафор для ограничения
            количества параллельных вызовов ffmpeg.
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Инициализирует AudioProcessor.

        Args:
            ffmpeg_path (str, optional): Путь к исполняемому файлу ffmpeg.
                По умолчанию "ffmpeg" (должен быть в PATH).
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffmpeg_semaphore = asyncio.Semaphore(3)
    
    async def get_video_duration_fast(self, video_path: str) -> float:
        """
        Быстро получает длительность видеофайла с помощью ffprobe.

        Args:
            video_path (str): Путь к видеофайлу.

        Returns:
            float: Длительность видео в секундах. Возвращает 0.0 в случае ошибки.
        
        Note:
            Использует ffprobe для быстрого чтения метаданных без декодирования видео.
        """
        try:
            cmd = [
                FFMPEG_CONFIG["ffprobe_path"],
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'format' in data and 'duration' in data['format']:
                    return float(data['format']['duration'])
        except:
            pass

        return 0.0
    
    def _get_temp_dir(self, video_path: str, task_id: str = None) -> Path:
        """
        Создает и возвращает путь к временной директории для видео.

        Args:
            video_path (str): Путь к видеофайлу.
            task_id (str, optional): ID задачи для уникальности папки.

        Returns:
            Path: Путь к временной директории.
        """
        input_path = Path(video_path)
        base_dir = input_path.parent
        
        if task_id:
            temp_dir = base_dir / ".audio" / task_id / "tmp"
        else:
            video_name = input_path.stem
            temp_dir = base_dir / ".audio" / video_name / "tmp"
            
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        return temp_dir
    
    async def extract_audio_segments(
        self,
        video_path: str,
        segment_duration: int = 30,
        overlap_duration: int = 1,
        sample_rate: int = 44100,
        task_id: str = None,
    ) -> AsyncGenerator[AudioSegment, None]:
        """
        Асинхронный генератор для извлечения аудио сегментов из видео.
        
        Разделяет аудио дорожку видео на перекрывающиеся сегменты
        указанной длительности для последующей обработки.

        Args:
            video_path (str): Путь к видеофайлу.
            segment_duration (int, optional): Длительность каждого сегмента
                в секундах. По умолчанию 30.
            overlap_duration (int, optional): Длительность перекрытия
                между сегментами в секундах. По умолчанию 1.
            sample_rate (int, optional): Частота дискретизации для
                извлеченного аудио. По умолчанию 44100.
            task_id (str, optional): ID задачи для уникальности.

        Yields:
            AsyncGenerator[AudioSegment, None]: Очередной аудио сегмент для обработки.

        Raises:
            Exception: Если произошла ошибка при извлечении сегментов.
        
        Note:
            Генератор создает сегменты "на лету" для экономии памяти.
        """
        try:
            duration = await self.get_video_duration_fast(video_path)
            if duration <= 0:
                duration = 60

            step = segment_duration - overlap_duration
            if step <= 0:
                step = segment_duration

            segment_id = 0
            start_time = 0.0

            while start_time < duration:
                end_time = min(start_time + segment_duration, duration)
                actual_duration = end_time - start_time

                if actual_duration < 0.5:
                    break

                audio_data = await self._extract_single_audio_segment(
                    video_path, start_time, actual_duration, sample_rate, task_id
                )

                if audio_data is not None and len(audio_data) > 0:
                    seg_task_id = task_id if task_id else Path(video_path).stem
                    yield AudioSegment(
                        segment_id=segment_id,
                        start_time=start_time,
                        end_time=end_time,
                        duration=actual_duration,
                        audio_data=audio_data,
                        sample_rate=sample_rate,
                        video_path=video_path,
                        task_id=seg_task_id
                    )

                segment_id += 1
                start_time += step

        except Exception as e:
            logger.error(f"Ошибка при извлечении аудио сегментов: {str(e)}")
            raise
    
    async def _extract_single_audio_segment(
        self, 
        video_path: str, 
        start_time: float, 
        duration: float,
        sample_rate: int,
        task_id: str = None
    ) -> Optional[np.ndarray]:
        """
        Извлекает один аудио сегмент из видео.

        Args:
            video_path (str): Путь к видеофайлу.
            start_time (float): Время начала сегмента в секундах.
            duration (float): Длительность сегмента в секундах.
            sample_rate (int): Частота дискретизации аудио.
            task_id (str, optional): ID задачи для уникальности.

        Returns:
            Optional[np.ndarray]: Аудио данные в формате float32 
            или None в случае ошибки.
        
        Note:
            Использует временные файлы для извлечения аудио через ffmpeg.
            Автоматически очищает временные файлы после обработки.
        """
        temp_dir = self._get_temp_dir(video_path, task_id)
        
        import time
        timestamp = int(time.time() * 1000000)
        if task_id:
            temp_filename = f"{task_id}_audio_{timestamp}_{int(start_time)}_{int(duration)}.wav"
        else:
            temp_filename = f"audio_{timestamp}_{int(start_time)}_{int(duration)}.wav"
        temp_path = temp_dir / temp_filename
        
        logger.debug(f"Создание временного файла: {temp_path}")
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-ar', str(sample_rate),
                '-ac', '1',
                '-f', 'wav',
                '-y', str(temp_path)
            ]
            logger.debug(f"Запуск команды ffmpeg: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            
            logger.debug(f"FFmpeg завершился с кодом возврата: {process.returncode}")
            
            if process.returncode != 0:
                error_msg = stderr.decode()[:200] if stderr else "Неизвестная ошибка"
                logger.warning(f"Ошибка ffmpeg при извлечении аудио ({start_time:.1f}-{start_time+duration:.1f}): {error_msg}")
                return None
            
            if not temp_path.exists():
                logger.warning(f"Временный файл не создан: {temp_path}")
                return None

            loop = asyncio.get_event_loop()
            file_size = await loop.run_in_executor(None, lambda: temp_path.stat().st_size if temp_path.exists() else 0)
            logger.debug(f"Временный файл создан, размер: {file_size} байт")
            
            if file_size < 100:
                logger.warning(f"Временный файл слишком мал: {file_size} байт")
                return None

            audio_data = await loop.run_in_executor(
                None, 
                self._read_wav_file_sync, 
                str(temp_path)
            )
            
            if audio_data is None:
                logger.warning(f"Не удалось прочитать аудио из файла: {temp_path}")
            else:
                logger.debug(f"Успешно прочитано аудио: {len(audio_data)} сэмплов")
                
            return audio_data
            
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут извлечения аудио сегмента: {start_time:.1f}-{start_time+duration:.1f}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении аудио сегмента ({start_time:.1f}-{start_time+duration:.1f}): {str(e)}")
            return None
        finally:
            try:
                if temp_path.exists():
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, lambda: temp_path.unlink())
                    logger.debug(f"Удален временный файл: {temp_path}")
            except Exception as e:
                logger.debug(f"Не удалось удалить временный файл {temp_path}: {str(e)}")
    
    async def _read_wav_file(self, wav_path: str) -> Optional[np.ndarray]:
        """
        Асинхронно читает WAV файл в numpy массив.

        Args:
            wav_path (str): Путь к WAV файлу.

        Returns:
            Optional[np.ndarray]: Аудио данные в формате float32 
            или None в случае ошибки.
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._read_wav_file_sync, wav_path)
        except Exception as e:
            logger.error(f"Ошибка чтения WAV файла: {str(e)}")
            return None
    
    def _read_wav_file_sync(self, wav_path: str) -> Optional[np.ndarray]:
        """
        Синхронно читает WAV файл в numpy массив.

        Args:
            wav_path (str): Путь к WAV файлу.

        Returns:
            Optional[np.ndarray]: Аудио данные в формате float32 
            или None в случае ошибки.
        
        Note:
            Поддерживает 16-битные и 32-битные аудио форматы.
            Автоматически конвертирует многоканальное аудио в моно.
        """
        try:
            with wave.open(wav_path, 'r') as wav_file:
                n_channels = wav_file.getnchannels()
                sampwidth = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                
                if n_frames == 0:
                    return None
                
                audio_bytes = wav_file.readframes(n_frames)
                
                if sampwidth == 2:
                    dtype = np.int16
                elif sampwidth == 3:
                    dtype = np.int32
                elif sampwidth == 4:
                    dtype = np.int32
                else:
                    dtype = np.int16

                audio_array = np.frombuffer(audio_bytes, dtype=dtype)
                
                if n_channels > 1:
                    audio_array = audio_array.reshape(-1, n_channels)
                    audio_array = audio_array.mean(axis=1)
                
                if dtype == np.int16:
                    audio_float = audio_array.astype(np.float32) / 32768.0
                elif dtype == np.int32:
                    audio_float = audio_array.astype(np.float32) / 2147483648.0
                else:
                    audio_float = audio_array.astype(np.float32)
                
                return audio_float
                
        except Exception as e:
            logger.error(f"Ошибка чтения WAV файла {wav_path}: {str(e)}")
            return None
    
    def process_audio_segment(
        self,
        audio_segment: AudioSegment,
        handler: AudioHandler,
        handler_settings: ProcessingSettings,
    ) -> AudioSegment:
        """
        Обрабатывает аудио сегмент с помощью указанного обработчика.

        Args:
            audio_segment (AudioSegment): Входной аудио сегмент.
            handler (AudioHandler): Обработчик аудио, реализующий метод process().
            handler_settings (ProcessingSettings): Настройки для обработчика.

        Returns:
            AudioSegment: Обработанный аудио сегмент с обновленным task_id.

        Raises:
            Exception: Если произошла ошибка при обработке сегмента.
        """
        try:
            processed_data = handler.process(
                audio=audio_segment.audio_data,
                sample_rate=audio_segment.sample_rate,
                settings=handler_settings
            )

            return AudioSegment(
                segment_id=audio_segment.segment_id,
                start_time=audio_segment.start_time,
                end_time=audio_segment.end_time,
                duration=audio_segment.duration,
                audio_data=processed_data,
                sample_rate=audio_segment.sample_rate,
                video_path=audio_segment.video_path,
                task_id=audio_segment.task_id + "_processed"
            )

        except Exception as e:
            logger.error(f"Ошибка обработки аудио сегмента: {e}")
            raise