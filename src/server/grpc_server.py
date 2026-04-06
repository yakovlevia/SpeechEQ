#!/usr/bin/env python3
"""
gRPC-сервер для обработки аудио.

Предоставляет удалённый интерфейс для очистки аудио через protobuf.
Использует локальный обработчик (LocalAudioHandler) из модуля processing
для выполнения DSP-пайплайна и ML-обработки.
"""
import asyncio
import logging
import json
import sys
import traceback
from pathlib import Path
from typing import Optional
from concurrent import futures

import numpy as np
import grpc

# Настройка путей для импорта proto-модулей
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
    """Реализация gRPC-сервиса для обработки аудио.

    Делегирует обработку аудио экземпляру LocalAudioHandler,
    который содержит настроенный пайплайн DSP-методов.
    """

    def __init__(self, config: ServerConfig, audio_handler: LocalAudioHandler) -> None:
        """Инициализация сервиса.

        Args:
            config: Конфигурация сервера.
            audio_handler: Готовый обработчик аудио.
        """
        self.config = config
        self.audio_handler = audio_handler
        self.request_count = 0
        self.active_requests: set[str] = set()
        logger.info("AudioProcessorServicer инициализирован")

        # Логирование активного пайплайна обработки
        if (
            hasattr(audio_handler, "processing_logic")
            and hasattr(audio_handler.processing_logic, "dsp_methods")
        ):
            dsp_names = [
                m.__class__.__name__
                for m in audio_handler.processing_logic.dsp_methods
            ]
            logger.info(f"Активный пайплайн: {dsp_names}")

    def _proto_to_settings(self, proto_settings) -> ProcessingSettings:
        """Конвертирует protobuf-настройки в объект ProcessingSettings.

        Args:
            proto_settings: Proto-объект с параметрами обработки.

        Returns:
            ProcessingSettings: Настройки для обработчика.
        """
        settings = ProcessingSettings()

        # DSP-флаги
        settings.noise_reduction = proto_settings.noise_reduction
        settings.hum_removal = proto_settings.hum_removal
        settings.deesser = proto_settings.deesser
        settings.eq = proto_settings.eq
        settings.normalization = proto_settings.normalization

        # Параметры DSP
        settings.noise_reduction_level = proto_settings.noise_reduction_level
        settings.hum_frequency = proto_settings.hum_frequency
        settings.hum_removal_strength = proto_settings.hum_removal_strength
        settings.deesser_strength = proto_settings.deesser_strength
        settings.eq_profile = proto_settings.eq_profile
        settings.normalization_target = proto_settings.normalization_target

        # ML-параметры
        settings.ml_model = proto_settings.ml_model
        settings.ml_model_name = proto_settings.ml_model_name
        settings.ml_strength = proto_settings.ml_strength

        # Дополнительные настройки из JSON-строки
        if proto_settings.extra:
            try:
                settings.extra = json.loads(proto_settings.extra)
            except json.JSONDecodeError:
                settings.extra = {"raw": proto_settings.extra}

        return settings

    def _settings_to_proto(self, settings: ProcessingSettings) -> audio_processor_pb2.ProcessingSettings:
        """Конвертирует ProcessingSettings в protobuf-формат.

        Args:
            settings: Объект настроек обработки.

        Returns:
            audio_processor_pb2.ProcessingSettings: Proto-объект.
        """
        extra_json = json.dumps(settings.extra) if settings.extra else ""

        return audio_processor_pb2.ProcessingSettings(
            noise_reduction=settings.noise_reduction,
            hum_removal=settings.hum_removal,
            deesser=settings.deesser,
            eq=settings.eq,
            normalization=settings.normalization,
            noise_reduction_level=float(settings.noise_reduction_level),
            hum_frequency=float(settings.hum_frequency),
            hum_removal_strength=float(settings.hum_removal_strength),
            deesser_strength=float(settings.deesser_strength),
            eq_profile=settings.eq_profile,
            normalization_target=float(settings.normalization_target),
            ml_model=settings.ml_model,
            ml_model_name=settings.ml_model_name,
            ml_strength=float(settings.ml_strength),
            extra=extra_json,
        )

    def _bytes_to_audio(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """Конвертирует байты в numpy-массив float32.

        Args:
            audio_bytes: Сырые аудио-данные.

        Returns:
            np.ndarray или None при ошибке декодирования.
        """
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.float32)

            if len(audio) == 0:
                logger.warning("Получен пустой аудио-буфер")
                return None

            if not np.isfinite(audio).all():
                logger.warning("Аудио содержит некорректные значения, нормализация")
                audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)

            return audio

        except Exception as e:
            logger.error(f"Ошибка декодирования аудио: {e}")
            return None

    def _audio_to_bytes(self, audio: np.ndarray) -> bytes:
        """Конвертирует numpy-массив в байты.

        Args:
            audio: Массив с аудио-данными.

        Returns:
            bytes: Сериализованные данные.
        """
        return audio.astype(np.float32).tobytes()

    async def ProcessAudio(self, request, context):
        """Обрабатывает входящий запрос на очистку аудио.

        Этап обработки:
        1. Декодирование аудио из байтов
        2. Конвертация настроек из proto
        3. Обработка через LocalAudioHandler (в пуле потоков)
        4. Кодирование результата и отправка ответа

        Args:
            request: Входной protobuf-запрос.
            context: gRPC-контекст.

        Returns:
            audio_processor_pb2.AudioResponse: Ответ с результатом.
        """
        self.request_count += 1
        request_id = request.request_id or f"req_{self.request_count}"
        self.active_requests.add(request_id)

        logger.info(f"[{request_id}] Запрос на обработку")
        logger.debug(f"[{request_id}] Sample rate: {request.sample_rate} Hz")
        logger.debug(f"[{request_id}] Client version: {request.client_version}")

        try:
            # Декодирование аудио
            audio = self._bytes_to_audio(request.audio_data)
            if audio is None:
                error_msg = "Не удалось декодировать аудио"
                logger.error(f"[{request_id}] {error_msg}")
                return audio_processor_pb2.AudioResponse(
                    success=False, error_message=error_msg, request_id=request_id
                )

            logger.info(f"[{request_id}] Загружено: {len(audio)} сэмплов")

            # Конвертация настроек
            settings = self._proto_to_settings(request.settings)
            logger.debug(
                f"[{request_id}] Настройки: noise={settings.noise_reduction}, "
                f"hum={settings.hum_removal}, deesser={settings.deesser}"
            )

            # Обработка в пуле потоков
            logger.info(f"[{request_id}] Начало обработки")
            try:
                processed_audio = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._process_audio_sync,
                    audio,
                    request.sample_rate,
                    settings,
                    request_id,
                )
            except asyncio.CancelledError:
                logger.warning(f"[{request_id}] Обработка отменена")
                raise
            except Exception as e:
                error_msg = f"Ошибка обработки: {e}"
                logger.error(f"[{request_id}] {error_msg}\n{traceback.format_exc()}")
                return audio_processor_pb2.AudioResponse(
                    success=False, error_message=error_msg, request_id=request_id
                )

            logger.info(f"[{request_id}] Обработка завершена")

            # Кодирование и отправка ответа
            processed_bytes = self._audio_to_bytes(processed_audio)
            return audio_processor_pb2.AudioResponse(
                processed_audio=processed_bytes,
                success=True,
                error_message="",
                request_id=request_id,
            )

        except Exception as e:
            error_msg = f"Непредвиденная ошибка: {e}"
            logger.error(f"[{request_id}] {error_msg}\n{traceback.format_exc()}")
            return audio_processor_pb2.AudioResponse(
                success=False, error_message=error_msg, request_id=request_id
            )
        finally:
            self.active_requests.discard(request_id)

    def _process_audio_sync(self, audio, sample_rate, settings, request_id):
        """Синхронная обработка аудио через handler.

        Выполняется в пуле потоков, чтобы не блокировать event loop.

        Args:
            audio: numpy-массив с аудио.
            sample_rate: Частота дискретизации.
            settings: Настройки обработки.
            request_id: Идентификатор запроса для логирования.

        Returns:
            np.ndarray: Обработанное аудио.
        """
        try:
            return self.audio_handler.process(
                audio=audio, sample_rate=sample_rate, settings=settings
            )
        except Exception as e:
            logger.error(f"[{request_id}] Ошибка в _process_audio_sync: {e}")
            raise

    def get_stats(self) -> dict:
        """Возвращает статистику работы сервиса.

        Returns:
            dict: Словарь с метриками (всего запросов, активных).
        """
        return {
            "total_requests": self.request_count,
            "active_requests": len(self.active_requests),
        }


async def serve(config: ServerConfig, audio_handler: LocalAudioHandler) -> None:
    """Запускает gRPC-сервер с указанным обработчиком.

    Блокирует выполнение до завершения сервера.

    Args:
        config: Конфигурация сервера.
        audio_handler: Экземпляр обработчика аудио.
    """
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=config.max_workers),
        options=[
            ("grpc.max_send_message_length", config.max_message_size),
            ("grpc.max_receive_message_length", config.max_message_size),
        ],
    )

    servicer = AudioProcessorServicer(config, audio_handler)
    audio_processor_pb2_grpc.add_AudioProcessorServicer_to_server(servicer, server)

    listen_addr = f"{config.host}:{config.port}"
    server.add_insecure_port(listen_addr)

    logger.info("=" * 60)
    logger.info("Запуск SpeechEQ gRPC-сервера")
    logger.info(f"Конфигурация: {config}")
    logger.info(f"Адрес: {listen_addr}")
    logger.info("=" * 60)

    try:
        await server.start()
        logger.info("Сервер запущен")
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения")
        await server.stop(5)
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка сервера: {e}")
        raise