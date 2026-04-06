#!/usr/bin/env python3
"""
Конфигурация gRPC-сервера для обработки аудио.

Содержит класс ServerConfig для управления параметрами сервера:
- Сетевые настройки (хост, порт)
- Параметры параллелизма и размера сообщений
- Пути к директориям логов и моделей
- Аудио-параметры по умолчанию
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ServerConfig:
    """Конфигурация gRPC-сервера.

    Предоставляет централизованное управление параметрами сервера
    с поддержкой переопределения через переменные окружения.
    """

    # Параметры сервера по умолчанию
    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 50051
    DEFAULT_MAX_WORKERS = 100
    DEFAULT_MAX_MESSAGE_SIZE = 50 * 1024 * 1024  # 50 MB

    # Параметры аудио по умолчанию
    TARGET_SAMPLE_RATE = 16000
    TARGET_CHANNELS = 1
    TARGET_DTYPE = "float32"

    # Базовые пути
    BASE_DIR = Path(__file__).parent.parent
    LOG_DIR = BASE_DIR / "logs"
    MODEL_DIR = BASE_DIR / "models"

    def __init__(self) -> None:
        """Инициализация конфигурации значениями по умолчанию."""
        self.host = self.DEFAULT_HOST
        self.port = self.DEFAULT_PORT
        self.max_workers = self.DEFAULT_MAX_WORKERS
        self.max_message_size = self.DEFAULT_MAX_MESSAGE_SIZE

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Создаёт конфигурацию с переопределением из переменных окружения.

        Поддерживаемые переменные:
            SPEECHEQ_HOST: Адрес для прослушивания
            SPEECHEQ_PORT: Порт сервера
            SPEECHEQ_MAX_WORKERS: Максимальное количество воркеров
            SPEECHEQ_MAX_MESSAGE_SIZE: Максимальный размер сообщения в байтах

        Returns:
            ServerConfig: Экземпляр конфигурации.
        """
        config = cls()

        if os.getenv("SPEECHEQ_HOST"):
            config.host = os.getenv("SPEECHEQ_HOST")
        if os.getenv("SPEECHEQ_PORT"):
            config.port = int(os.getenv("SPEECHEQ_PORT"))
        if os.getenv("SPEECHEQ_MAX_WORKERS"):
            config.max_workers = int(os.getenv("SPEECHEQ_MAX_WORKERS"))
        if os.getenv("SPEECHEQ_MAX_MESSAGE_SIZE"):
            config.max_message_size = int(os.getenv("SPEECHEQ_MAX_MESSAGE_SIZE"))

        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        return config

    def __str__(self) -> str:
        """Возвращает человекочитаемое представление конфигурации.

        Returns:
            str: Строка с основными параметрами сервера.
        """
        return (
            f"ServerConfig(host={self.host}, port={self.port}, "
            f"max_workers={self.max_workers}, "
            f"max_message_size={self.max_message_size / 1024 / 1024:.1f}MB)"
        )