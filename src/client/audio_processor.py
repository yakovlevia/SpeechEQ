# src/client/audio_processor.py
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

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Класс для представления сегмента аудио"""
    segment_id: int
    start_time: float
    end_time: float
    duration: float
    audio_data: np.ndarray
    sample_rate: int
    video_path: str
    task_id: str


class AudioProcessor:
    """Класс для обработки аудио"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self.ffmpeg_semaphore = asyncio.Semaphore(3)
    
    async def get_video_duration_fast(self, video_path: str) -> float:
        """Быстрое получение длительности видео"""
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
    
    async def extract_audio_segments(
        self,
        video_path: str,
        segment_duration: int = 30,
        overlap_duration: int = 1,
        sample_rate: int = 44100,
    ) -> AsyncGenerator[AudioSegment, None]:
        """
        Генератор аудио сегментов с перекрытием.
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
                    video_path, start_time, actual_duration, sample_rate
                )

                if audio_data is not None and len(audio_data) > 0:
                    yield AudioSegment(
                        segment_id=segment_id,
                        start_time=start_time,
                        end_time=end_time,
                        duration=actual_duration,
                        audio_data=audio_data,
                        sample_rate=sample_rate,
                        video_path=video_path,
                        task_id=Path(video_path).stem
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
        sample_rate: int
    ) -> Optional[np.ndarray]:
        """Извлечь один аудио сегмент"""
        temp_dir = tempfile.gettempdir()
        temp_filename = f"audio_{int(start_time)}_{int(duration)}.wav"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        logger.debug(f"Создание временного файла: {temp_path}")
        
        try:
            cmd = f'ffmpeg -ss {start_time} -i "{video_path}" -t {duration} -ar {sample_rate} -ac 1 -f wav -y "{temp_path}"'
            logger.debug(f"Запуск команды ffmpeg: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            logger.debug(f"FFmpeg завершился с кодом возврата: {result.returncode}")
            
            if result.returncode != 0:
                error_msg = result.stderr[:200] if result.stderr else "Неизвестная ошибка"
                logger.warning(f"Ошибка ffmpeg при извлечении аудио ({start_time:.1f}-{start_time+duration:.1f}): {error_msg}")
                return None
            
            if not os.path.exists(temp_path):
                logger.warning(f"Временный файл не создан: {temp_path}")
                return None
            
            file_size = os.path.getsize(temp_path)
            logger.debug(f"Временный файл создан, размер: {file_size} байт")
            
            if file_size < 100:
                logger.warning(f"Временный файл слишком мал: {file_size} байт")
                return None
            
            audio_data = self._read_wav_file_sync(temp_path)
            
            if audio_data is None:
                logger.warning(f"Не удалось прочитать аудио из файла: {temp_path}")
            else:
                logger.debug(f"Успешно прочитано аудио: {len(audio_data)} сэмплов")
                
            return audio_data
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Таймаут извлечения аудио сегмента: {start_time:.1f}-{start_time+duration:.1f}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении аудио сегмента ({start_time:.1f}-{start_time+duration:.1f}): {str(e)}")
            return None
        finally:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    logger.debug(f"Удален временный файл: {temp_path}")
            except Exception as e:
                logger.debug(f"Не удалось удалить временный файл {temp_path}: {str(e)}")
    
    async def _read_wav_file(self, wav_path: str) -> Optional[np.ndarray]:
        """Асинхронно прочитать WAV файл"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._read_wav_file_sync, wav_path)
        except Exception as e:
            logger.error(f"Ошибка чтения WAV файла: {str(e)}")
            return None
    
    def _read_wav_file_sync(self, wav_path: str) -> Optional[np.ndarray]:
        """Синхронно прочитать WAV файл (вызывается в executor)"""
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
    
    def process_audio_segment(self, audio_segment: AudioSegment) -> AudioSegment:
        """
        Обработать аудио сегмент: умножить на 0.5
        
        Args:
            audio_segment: Входной аудио сегмент
        
        Returns:
            Обработанный аудио сегмент
        """
        try:
            processed_data = audio_segment.audio_data.copy()
            
            # Заглушка -> меньше громкость
            processed_data = processed_data * 0.2
            
            processed_segment = AudioSegment(
                segment_id=audio_segment.segment_id,
                start_time=audio_segment.start_time,
                end_time=audio_segment.end_time,
                duration=audio_segment.duration,
                audio_data=processed_data,
                sample_rate=audio_segment.sample_rate,
                video_path=audio_segment.video_path,
                task_id=audio_segment.task_id + "_processed"
            )
            
            return processed_segment
            
        except Exception as e:
            logger.error(f"Ошибка обработки аудио сегмента: {str(e)}")
            raise