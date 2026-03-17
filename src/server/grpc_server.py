"""
gRPC сервер для обработки аудио
"""
import asyncio
import logging
import numpy as np
from concurrent import futures
from typing import Optional
import traceback
import sys
from pathlib import Path
import grpc

current_dir = Path(__file__).parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
proto_dir = root_dir / "proto"
if str(proto_dir) not in sys.path:
    sys.path.insert(0, str(proto_dir))

import audio_processor_pb2
import audio_processor_pb2_grpc
from processing.handlers.local import LocalAudioHandler
from processing.core.settings import ProcessingSettings

from .config import ServerConfig

logger = logging.getLogger(__name__)


class AudioProcessorServicer(audio_processor_pb2_grpc.AudioProcessorServicer):
    """
    Реализация gRPC сервиса для обработки аудио
    
    Использует готовый AudioHandler из processing, который содержит
    AudioProcessingLogic с настроенным пайплайном DSP методов.
    """
    
    def __init__(self, config: ServerConfig, audio_handler: LocalAudioHandler):
        """
        Инициализация сервиса.
        
        Args:
            config: Конфигурация сервера
            audio_handler: Готовый обработчик аудио из processing
        """
        self.config = config
        self.audio_handler = audio_handler
        self.request_count = 0
        self.active_requests = set()
        logger.info("AudioProcessorServicer инициализирован")
        
        # Логируем информацию о пайплайне
        if hasattr(audio_handler, 'processing_logic') and hasattr(audio_handler.processing_logic, 'dsp_methods'):
            dsp_names = [m.__class__.__name__ for m in audio_handler.processing_logic.dsp_methods]
            logger.info(f"Используется пайплайн DSP методов: {dsp_names}")
    
    def _proto_to_settings(self, proto_settings) -> ProcessingSettings:
        """
        Конвертирует proto настройки в объект ProcessingSettings
        """
        settings = ProcessingSettings()

        settings.noise_reduction = proto_settings.noise_reduction
        settings.hum_removal = proto_settings.hum_removal
        settings.deesser = proto_settings.deesser
        settings.eq = proto_settings.eq
        settings.normalization = proto_settings.normalization
        settings.noise_reduction_level = proto_settings.noise_reduction_level
        settings.hum_frequency = proto_settings.hum_frequency
        settings.hum_removal_strength = proto_settings.hum_removal_strength
        settings.deesser_strength = proto_settings.deesser_strength
        settings.eq_profile = proto_settings.eq_profile
        settings.normalization_target = proto_settings.normalization_target
        settings.ml_model = proto_settings.ml_model
        settings.ml_model_name = proto_settings.ml_model_name
        settings.ml_strength = proto_settings.ml_strength

        if proto_settings.extra:
            try:
                import json
                settings.extra = json.loads(proto_settings.extra)
            except:
                settings.extra = {"raw": proto_settings.extra}
        
        return settings
    
    def _bytes_to_audio(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Конвертирует байты в numpy массив
        """
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.float32)

            if len(audio) == 0:
                logger.warning("Получен пустой аудио буфер")
                return None

            if not np.isfinite(audio).all():
                logger.warning("Аудио содержит некорректные значения")
                audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)
            
            return audio
            
        except Exception as e:
            logger.error(f"Ошибка конвертации аудио: {e}")
            return None
    
    def _audio_to_bytes(self, audio: np.ndarray) -> bytes:
        """
        Конвертирует numpy массив в байты
        """
        return audio.astype(np.float32).tobytes()
    
    async def ProcessAudio(self, request, context):
        """
        Обработка аудио запроса
        """
        self.request_count += 1
        request_id = request.request_id or f"req_{self.request_count}"
        self.active_requests.add(request_id)
        
        logger.info(f"[{request_id}] Получен запрос на обработку аудио")
        logger.debug(f"[{request_id}] Sample rate: {request.sample_rate} Hz")
        logger.debug(f"[{request_id}] Client version: {request.client_version}")
        
        try:
            # 1. Конвертация байт в numpy массив
            audio = self._bytes_to_audio(request.audio_data)
            if audio is None:
                error_msg = "Не удалось декодировать аудио данные"
                logger.error(f"[{request_id}] {error_msg}")
                return audio_processor_pb2.AudioResponse(
                    success=False,
                    error_message=error_msg,
                    request_id=request_id
                )
            
            logger.info(f"[{request_id}] Аудио загружено: {len(audio)} сэмплов")
            
            # 2. Конвертация proto настроек
            settings = self._proto_to_settings(request.settings)
            logger.debug(f"[{request_id}] Настройки: {settings}")
            
            # 3. Обработка аудио через готовый handler
            logger.info(f"[{request_id}] Начало обработки...")
            
            # Обработка может быть длительной - выполняем в пуле потоков
            try:
                processed_audio = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._process_audio_sync,
                    audio,
                    request.sample_rate,
                    settings,
                    request_id
                )
            except asyncio.CancelledError:
                logger.warning(f"[{request_id}] Обработка была отменена")
                raise
            except Exception as e:
                error_msg = f"Ошибка при обработке: {str(e)}"
                logger.error(f"[{request_id}] {error_msg}\n{traceback.format_exc()}")
                return audio_processor_pb2.AudioResponse(
                    success=False,
                    error_message=error_msg,
                    request_id=request_id
                )
            
            logger.info(f"[{request_id}] Обработка завершена")
            
            # 4. Конвертация результата в байты
            processed_bytes = self._audio_to_bytes(processed_audio)
            
            # 5. Отправка ответа
            return audio_processor_pb2.AudioResponse(
                processed_audio=processed_bytes,
                success=True,
                error_message="",
                request_id=request_id
            )
            
        except Exception as e:
            error_msg = f"Непредвиденная ошибка: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}\n{traceback.format_exc()}")
            return audio_processor_pb2.AudioResponse(
                success=False,
                error_message=error_msg,
                request_id=request_id
            )
        finally:
            self.active_requests.remove(request_id)
    
    def _process_audio_sync(self, audio, sample_rate, settings, request_id):
        """
        Синхронная обработка аудио через handler из processing
        Выполняется в пуле потоков
        """
        try:
            processed = self.audio_handler.process(
                audio=audio,
                sample_rate=sample_rate,
                settings=settings
            )
            
            return processed
            
        except Exception as e:
            logger.error(f"[{request_id}] Ошибка в _process_audio_sync: {e}")
            raise
    
    def get_stats(self):
        """Получение статистики сервера"""
        return {
            "total_requests": self.request_count,
            "active_requests": len(self.active_requests),
        }


async def serve(config: ServerConfig, audio_handler: LocalAudioHandler):
    """
    Запуск gRPC сервера с готовым обработчиком аудио
    """
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=config.max_workers),
        options=[
            ('grpc.max_send_message_length', config.max_message_size),
            ('grpc.max_receive_message_length', config.max_message_size),
        ]
    )

    servicer = AudioProcessorServicer(config, audio_handler)

    audio_processor_pb2_grpc.add_AudioProcessorServicer_to_server(servicer, server)

    listen_addr = f"{config.host}:{config.port}"
    server.add_insecure_port(listen_addr)  # TODO: Добавить поддержку TLS
    
    logger.info("=" * 60)
    logger.info("Запуск SpeechEQ gRPC сервера")
    logger.info(f"Конфигурация: {config}")
    logger.info(f"Слушаем на: {listen_addr}")
    logger.info("=" * 60)
    
    try:
        await server.start()
        logger.info("Сервер успешно запущен")

        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения")
        await server.stop(5)
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка сервера: {e}")
        raise