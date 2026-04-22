"""
gRPC клиент для связи с сервером обработки аудио.
"""

import logging
import numpy as np
import grpc
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import uuid
import threading
import sys
import time

root_dir = Path(__file__).parent.parent
proto_dir = root_dir / "proto"
if str(proto_dir) not in sys.path:
    sys.path.insert(0, str(proto_dir))

import src.proto.audio_processor_pb2 as audio_processor_pb2
from src.proto.audio_processor_pb2_grpc import AudioProcessorStub
from src.processing.core.settings import ProcessingSettings
from src.processing.handlers.base import AudioHandler

logger = logging.getLogger(__name__)


class GRPCAudioHandler(AudioHandler):
    """
    gRPC клиент для обработки аудио на удалённом сервере.

    Attributes:
        server_address (str): Адрес сервера в формате host:port.
        timeout (float): Таймаут для gRPC вызовов.
        max_retries (int): Максимальное количество повторных попыток.
        channel (grpc.Channel): gRPC канал.
        stub (audio_processor_pb2_grpc.AudioProcessorStub): gRPC заглушка.
        connected (bool): Флаг подключения к серверу.
        client_version (str): Версия клиента.
        _lock (threading.Lock): Блокировка для потокобезопасности.
        connection_lost_callback (Optional[Callable]): Колбэк при потере соединения.
        _connection_check_thread (Optional[threading.Thread]): Поток проверки соединения.
        _stop_check (bool): Флаг остановки проверки соединения.
        _is_shutting_down (bool): Флаг завершения работы.
    """

    def __init__(self, host: str = "localhost", port: int = 50051,
                 timeout: float = 30.0, max_retries: int = 3) -> None:
        """
        Инициализирует gRPC обработчик аудио.

        Args:
            host: Адрес сервера.
            port: Порт сервера.
            timeout: Таймаут для gRPC вызовов.
            max_retries: Максимальное количество повторных попыток.

        Raises:
            Exception: При ошибках инициализации.
        """
        super().__init__(processing_logic=None)
        self.server_address: str = f"{host}:{port}"
        self.timeout: float = timeout
        self.max_retries: int = max_retries
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[AudioProcessorStub] = None
        self.connected: bool = False
        self.client_version: str = "1.0.0"
        self._lock: threading.Lock = threading.Lock()
        self.connection_lost_callback: Optional[Callable] = None
        self._connection_check_thread: Optional[threading.Thread] = None
        self._stop_check: bool = False
        self._is_shutting_down: bool = False

    def set_shutting_down(self, shutting_down: bool) -> None:
        """
        Устанавливает флаг завершения работы.

        Args:
            shutting_down: True если приложение завершается.
        """
        self._is_shutting_down = shutting_down

    def set_connection_lost_callback(self, callback: Callable) -> None:
        """
        Устанавливает колбэк для обработки потери соединения.

        Args:
            callback: Функция для вызова при потере соединения.
        """
        self.connection_lost_callback = callback

    def connect(self) -> bool:
        """
        Устанавливает соединение с gRPC сервером.

        Returns:
            bool: True если подключение успешно, иначе False.

        Raises:
            grpc.RpcError: При ошибках gRPC.
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
            self.stub = AudioProcessorStub(self.channel)
            self.connected = True
            self._stop_check = False
            self._start_connection_check()
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

    def _start_connection_check(self) -> None:
        """Запускает фоновый поток для проверки состояния соединения."""
        if self._connection_check_thread is None or not self._connection_check_thread.is_alive():
            self._stop_check = False
            self._connection_check_thread = threading.Thread(
                target=self._check_connection_loop, daemon=True
            )
            self._connection_check_thread.start()

    def _check_connection_loop(self) -> None:
        """Основной цикл проверки соединения в фоновом потоке."""
        check_interval = 3
        consecutive_failures = 0
        max_failures = 2

        while not self._stop_check and self.connected:
            time.sleep(check_interval)
            if not self.channel or self._is_shutting_down:
                continue

            if not self._check_connection():
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger.error("Потеряно соединение с сервером!")
                    old_connected = self.connected
                    self.connected = False
                    if old_connected and self.connection_lost_callback:
                        try:
                            self.connection_lost_callback()
                        except Exception as e:
                            logger.error(f"Ошибка в колбэке потери соединения: {e}")
                    break
            else:
                if consecutive_failures > 0:
                    consecutive_failures = 0

    def _check_connection(self) -> bool:
        """
        Проверяет активность соединения с сервером.

        Returns:
            bool: True если соединение активно, иначе False.
        """
        if not self.channel or not self.stub or self._is_shutting_down:
            return False

        try:
            test_audio = np.zeros(160, dtype=np.float32)
            test_bytes = test_audio.tobytes()
            test_request = audio_processor_pb2.AudioRequest(
                audio_data=test_bytes,
                sample_rate=16000,
                request_id="connection_test",
                client_version="1.0.0"
            )
            self.stub.ProcessAudio(test_request, timeout=2.0)
            return True
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                return False
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        """Закрывает соединение с сервером и освобождает ресурсы."""
        self._stop_check = True
        self._is_shutting_down = True

        if self._connection_check_thread and self._connection_check_thread.is_alive():
            self._connection_check_thread.join(timeout=1.0)

        if self.channel:
            self.channel.close()

        self.connected = False
        logger.info("Отключение от сервера")

    def _settings_to_proto(self, settings: ProcessingSettings) -> audio_processor_pb2.ProcessingSettings:
        """
        Конвертирует настройки обработки в protobuf формат.

        Args:
            settings: Настройки обработки.

        Returns:
            audio_processor_pb2.ProcessingSettings: Настройки в protobuf формате.
        """
        extra_json = ""
        if settings.extra:
            import json
            try:
                extra_json = json.dumps(settings.extra)
            except Exception:
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

    def _process_audio_sync(self, audio: np.ndarray, sample_rate: int,
                           settings: ProcessingSettings, request_id: str) -> Optional[np.ndarray]:
        """
        Синхронно отправляет аудио на сервер для обработки.

        Args:
            audio: Аудио данные в формате float32.
            sample_rate: Частота дискретизации.
            settings: Настройки обработки.
            request_id: Уникальный идентификатор запроса.

        Returns:
            Optional[np.ndarray]: Обработанное аудио или None при ошибке.

        Raises:
            grpc.RpcError: При ошибках gRPC.
        """
        if not self.connected or not self.stub or self._is_shutting_down:
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
                response = self.stub.ProcessAudio(request, timeout=self.timeout)
                if response.success:
                    return np.frombuffer(response.processed_audio, dtype=np.float32)
                else:
                    logger.error(f"Ошибка сервера: {response.error_message}")
                    return None
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    if attempt < self.max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                        continue
                    else:
                        self.connected = False
                        if self.connection_lost_callback:
                            self.connection_lost_callback()
                return None
            except Exception:
                return None

        return None

    def process(self, audio: np.ndarray, sample_rate: int,
                settings: ProcessingSettings) -> np.ndarray:
        """
        Обрабатывает аудио через удалённый сервер.

        Args:
            audio: Аудио данные в формате float32.
            sample_rate: Частота дискретизации.
            settings: Настройки обработки.

        Returns:
            np.ndarray: Обработанное аудио или оригинал при ошибке.
        """
        if self._is_shutting_down or not self.connected:
            return audio

        request_id = str(uuid.uuid4())
        with self._lock:
            try:
                result = self._process_audio_sync(audio, sample_rate, settings, request_id)
            except Exception as e:
                logger.error(f"Ошибка в process: {e}")
                result = None

        return result if result is not None else audio

    def get_server_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о состоянии сервера.

        Returns:
            Dict[str, Any]: Словарь с информацией о сервере.
        """
        return {
            "connected": self.connected,
            "address": self.server_address,
            "client_version": self.client_version,
            "is_shutting_down": self._is_shutting_down
        }


class GRPCConnectionManager:
    """
    Менеджер соединений для управления локальным и удалённым режимами.

    Attributes:
        current_handler (Optional[GRPCAudioHandler]): Текущий активный обработчик.
        local_mode (bool): Флаг локального режима.
        local_handler (Optional[AudioHandler]): Локальный обработчик.
        _lock (threading.Lock): Блокировка для потокобезопасности.
        connection_lost_callback (Optional[Callable]): Колбэк при потере соединения.
    """

    def __init__(self) -> None:
        """Инициализирует менеджер соединений."""
        self.current_handler: Optional[GRPCAudioHandler] = None
        self.local_mode: bool = True
        self.local_handler: Optional[AudioHandler] = None
        self._lock: threading.Lock = threading.Lock()
        self.connection_lost_callback: Optional[Callable] = None
        logger.info("GRPCConnectionManager инициализирован")

    def set_connection_lost_callback(self, callback: Callable) -> None:
        """
        Устанавливает колбэк для обработки потери соединения.

        Args:
            callback: Функция для вызова при потере соединения.
        """
        self.connection_lost_callback = callback

    def set_local_handler(self, handler: AudioHandler) -> None:
        """
        Устанавливает локальный обработчик аудио.

        Args:
            handler: Локальный обработчик.
        """
        self.local_handler = handler
        if self.local_mode:
            with self._lock:
                self.current_handler = handler

    def connect_to_server(self, host: str, port: int) -> bool:
        """
        Подключается к удалённому gRPC серверу.

        Args:
            host: Адрес сервера.
            port: Порт сервера.

        Returns:
            bool: True если подключение успешно, иначе False.

        Raises:
            Exception: При ошибках подключения.
        """
        logger.info(f"GRPCConnectionManager.connect_to_server({host}, {port})")

        with self._lock:
            grpc_handler = GRPCAudioHandler(host=host, port=port)
            if self.connection_lost_callback:
                grpc_handler.set_connection_lost_callback(self.connection_lost_callback)

            try:
                success = grpc_handler.connect()
            except Exception as e:
                logger.error(f"Ошибка при подключении: {e}")
                return False

            if success:
                if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
                    try:
                        self.current_handler.set_shutting_down(True)
                        self.current_handler.disconnect()
                    except Exception:
                        pass

                self.current_handler = grpc_handler
                self.local_mode = False
                logger.info(f"Подключено к серверу {host}:{port}")
                return success
            else:
                logger.error(f"Не удалось подключиться к {host}:{port}")
                return success

    async def disconnect_from_server(self) -> None:
        """
        Отключается от удалённого сервера и переключается на локальный режим.

        Raises:
            Exception: При ошибках отключения.
        """
        logger.info("GRPCConnectionManager.disconnect_from_server")

        with self._lock:
            if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
                try:
                    self.current_handler.set_shutting_down(True)
                    self.current_handler.disconnect()
                except Exception as e:
                    logger.error(f"Ошибка при отключении: {e}")

            self.current_handler = self.local_handler
            self.local_mode = True
            logger.info("Отключено от сервера, переключено на локальный режим")

    def switch_to_local(self) -> None:
        """Принудительно переключает менеджер на локальный режим."""
        with self._lock:
            self.local_mode = True
            self.current_handler = self.local_handler
            logger.info("GRPCConnectionManager принудительно переключен на локальный режим")

    def get_current_handler(self) -> Optional[AudioHandler]:
        """
        Возвращает текущий активный обработчик аудио.

        Returns:
            Optional[AudioHandler]: Текущий обработчик или None.
        """
        with self._lock:
            return self.current_handler

    def is_connected(self) -> bool:
        """
        Проверяет, активно ли соединение с сервером.

        Returns:
            bool: True если соединение активно, иначе False.
        """
        if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
            return self.current_handler.connected
        return False

    def is_local(self) -> bool:
        """
        Проверяет, активен ли локальный режим.

        Returns:
            bool: True если локальный режим активен, иначе False.
        """
        return self.local_mode

    def set_shutting_down(self, shutting_down: bool) -> None:
        """
        Устанавливает флаг завершения работы.

        Args:
            shutting_down: True если приложение завершается.
        """
        with self._lock:
            if self.current_handler and isinstance(self.current_handler, GRPCAudioHandler):
                self.current_handler.set_shutting_down(shutting_down)