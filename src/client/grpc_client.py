"""
gRPC клиент для связи с сервером обработки аудио.

Предоставляет классы для удалённой обработки аудио через gRPC,
а также менеджер для управления подключением и переключением
между локальным и удалённым режимами.
"""
import logging
import numpy as np
import grpc
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
import threading
import sys

root_dir = Path(__file__).parent.parent
proto_dir = root_dir / "proto"
if str(proto_dir) not in sys.path:
    sys.path.insert(0, str(proto_dir))

import audio_processor_pb2
import audio_processor_pb2_grpc

from processing.core.settings import ProcessingSettings
from processing.handlers.base import AudioHandler

logger = logging.getLogger(__name__)


class GRPCAudioHandler(AudioHandler):
    """
    Обработчик аудио через gRPC сервер.
    
    Использует синхронный gRPC клиент для избежания проблем с event loop.
    Позволяет передавать аудиоданные на удалённый сервер для обработки
    и получать обработанный результат.
    
    Attributes:
        server_address (str): Адрес gRPC сервера (host:port)
        timeout (float): Таймаут запроса в секундах
        max_retries (int): Максимальное количество повторных попыток
        channel (grpc.Channel): Канал gRPC
        stub (audio_processor_pb2_grpc.AudioProcessorStub): Stub для вызова методов
        connected (bool): Флаг подключения к серверу
        client_version (str): Версия клиента
    """
    
    def __init__(self, host: str = "localhost", port: int = 50051, 
                 timeout: float = 30.0, max_retries: int = 3):
        """
        Инициализирует gRPC клиента.

        Args:
            host (str, optional): Адрес сервера. По умолчанию "localhost".
            port (int, optional): Порт сервера. По умолчанию 50051.
            timeout (float, optional): Таймаут запроса в секундах. По умолчанию 30.0.
            max_retries (int, optional): Максимальное количество повторных попыток. По умолчанию 3.
        """
        super().__init__(processing_logic=None)
        
        self.server_address = f"{host}:{port}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.channel = None
        self.stub = None
        self.connected = False
        self.client_version = "1.0.0"
        self._lock = threading.Lock()
        
        logger.info(f"GRPCAudioHandler инициализирован для сервера {self.server_address}")
    
    def connect(self) -> bool:
        """
        Устанавливает синхронное соединение с сервером.

        Returns:
            bool: True если соединение установлено успешно, False в противном случае.
        """
        try:
            logger.info(f"Попытка подключения к {self.server_address}")

            self.channel = grpc.insecure_channel(
                self.server_address,
                options=[
                    ('grpc.max_send_message_length', 50 * 1024 * 1024),
                    ('grpc.max_receive_message_length', 50 * 1024 * 1024),
                ]
            )

            grpc.channel_ready_future(self.channel).result(timeout=5)

            self.stub = audio_processor_pb2_grpc.AudioProcessorStub(self.channel)
            
            self.connected = True
            logger.info(f"Успешное подключение к серверу {self.server_address}")
            return True
            
        except grpc.FutureTimeoutError:
            logger.error(f"Таймаут подключения к серверу {self.server_address}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Ошибка подключения к серверу: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Закрывает соединение с сервером."""
        if self.channel:
            self.channel.close()
            self.connected = False
            logger.info("Отключение от сервера")
    
    def _settings_to_proto(self, settings: ProcessingSettings) -> audio_processor_pb2.ProcessingSettings:
        """
        Конвертирует ProcessingSettings в protobuf формат.

        Args:
            settings (ProcessingSettings): Настройки обработки

        Returns:
            audio_processor_pb2.ProcessingSettings: Настройки в protobuf формате.
        """
        extra_json = ""
        if settings.extra:
            import json
            try:
                extra_json = json.dumps(settings.extra)
            except:
                extra_json = str(settings.extra)
        
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
            extra=extra_json
        )
    
    def _process_audio_sync(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings,
        request_id: str
    ) -> Optional[np.ndarray]:
        """
        Синхронная обработка аудио через gRPC.

        Args:
            audio (np.ndarray): Аудио данные в формате float32
            sample_rate (int): Частота дискретизации
            settings (ProcessingSettings): Настройки обработки
            request_id (str): Уникальный идентификатор запроса

        Returns:
            Optional[np.ndarray]: Обработанное аудио или None в случае ошибки.
        """
        if not self.connected or not self.stub:
            logger.error("Нет подключения к серверу")
            return None

        audio_bytes = audio.astype(np.float32).tobytes()

        request = audio_processor_pb2.AudioRequest(
            audio_data=audio_bytes,
            sample_rate=sample_rate,
            settings=self._settings_to_proto(settings),
            request_id=request_id,
            client_version=self.client_version
        )

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Отправка запроса {request_id} (попытка {attempt + 1})")

                response = self.stub.ProcessAudio(
                    request,
                    timeout=self.timeout
                )
                
                if response.success:
                    processed = np.frombuffer(response.processed_audio, dtype=np.float32)
                    logger.debug(f"Запрос {request_id} успешно обработан")
                    return processed
                else:
                    logger.error(f"Ошибка сервера: {response.error_message}")
                    return None
                    
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    logger.warning(f"Сервер недоступен (попытка {attempt + 1})")
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(1 * (attempt + 1))
                        continue
                elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                    logger.error(f"Таймаут запроса {request_id}")
                else:
                    logger.error(f"gRPC ошибка: {e.code()} - {e.details()}")
                
                return None
                
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                return None
        
        return None
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
        settings: ProcessingSettings
    ) -> np.ndarray:
        """
        Синхронная обработка аудио через gRPC.

        Реализация интерфейса AudioHandler.

        Args:
            audio (np.ndarray): Аудио данные
            sample_rate (int): Частота дискретизации
            settings (ProcessingSettings): Настройки обработки

        Returns:
            np.ndarray: Обработанное аудио. В случае ошибки возвращает исходный сигнал.
        """
        if not self.connected:
            logger.warning("Нет подключения к серверу, возвращаем исходный сигнал")
            return audio
        
        request_id = str(uuid.uuid4())
        
        with self._lock:
            try:
                result = self._process_audio_sync(audio, sample_rate, settings, request_id)
            except Exception as e:
                logger.error(f"Ошибка в process: {e}")
                result = None
        
        if result is None:
            logger.warning("Ошибка обработки на сервере, возвращаем исходный сигнал")
            return audio
        
        return result
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Получает информацию о сервере.

        Returns:
            Dict[str, Any]: Словарь с информацией о подключении и версиях.
        """
        return {
            "connected": self.connected,
            "address": self.server_address,
            "client_version": self.client_version
        }


class GRPCConnectionManager:
    """
    Менеджер для управления подключением к gRPC серверу.
    
    Используется в UI для переключения между локальным и удалённым режимами.
    Обеспечивает потокобезопасное переключение обработчиков.
    
    Attributes:
        current_handler (Optional[AudioHandler]): Текущий обработчик (локальный или gRPC)
        local_mode (bool): Флаг использования локального режима
        local_handler (Optional[AudioHandler]): Обработчик для локального режима
    """
    
    def __init__(self):
        """
        Инициализирует менеджер подключения.
        """
        self.current_handler: Optional[GRPCAudioHandler] = None
        self.local_mode = True
        self.local_handler: Optional[AudioHandler] = None
        self._lock = threading.Lock()
        logger.info("GRPCConnectionManager инициализирован")
    
    def set_local_handler(self, handler: AudioHandler):
        """
        Устанавливает обработчик для локального режима.

        Args:
            handler (AudioHandler): Обработчик аудио для локального режима
        """
        self.local_handler = handler
        if self.local_mode:
            self.current_handler = handler
    
    def connect_to_server(self, host: str, port: int) -> bool:
        """
        Подключается к удалённому серверу (синхронно).

        Args:
            host (str): Адрес сервера
            port (int): Порт сервера

        Returns:
            bool: True если подключение успешно, False в противном случае.
        """
        logger.info(f"GRPCConnectionManager.connect_to_server({host}, {port})")
        
        with self._lock:
            grpc_handler = GRPCAudioHandler(host=host, port=port)
            
            try:
                success = grpc_handler.connect()
            except Exception as e:
                logger.error(f"Ошибка при подключении: {e}")
                return False
            
            if success:
                if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
                    try:
                        self.current_handler.disconnect()
                    except:
                        pass
                
                self.current_handler = grpc_handler
                self.local_mode = False
                logger.info(f"Подключено к серверу {host}:{port}")
            else:
                logger.error(f"Не удалось подключиться к {host}:{port}")
            
            return success
    
    def disconnect_from_server(self):
        """Отключается от удалённого сервера и переключается на локальный режим."""
        logger.info("GRPCConnectionManager.disconnect_from_server")
        
        with self._lock:
            if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
                try:
                    self.current_handler.disconnect()
                except Exception as e:
                    logger.error(f"Ошибка при отключении: {e}")
            
            self.current_handler = self.local_handler
            self.local_mode = True
            logger.info("Отключено от сервера, переключено на локальный режим")
    
    def get_current_handler(self) -> Optional[AudioHandler]:
        """
        Возвращает текущий обработчик.

        Returns:
            Optional[AudioHandler]: Текущий обработчик (локальный или gRPC)
        """
        return self.current_handler
    
    def is_connected(self) -> bool:
        """
        Проверяет, подключен ли клиент к серверу.

        Returns:
            bool: True если подключение активно, False в противном случае.
        """
        if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
            return self.current_handler.connected
        return False
    
    def is_local(self) -> bool:
        """
        Проверяет, используется ли локальный режим.

        Returns:
            bool: True если используется локальный режим, False если удалённый.
        """
        return self.local_mode