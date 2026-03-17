#!/usr/bin/env python3
"""
Конфигурация gRPC сервера
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ServerConfig:
    """Конфигурация сервера"""
    
    # Параметры сервера по умолчанию
    DEFAULT_HOST = "0.0.0.0" 
    DEFAULT_PORT = 50051
    DEFAULT_MAX_WORKERS = 10
    DEFAULT_MAX_MESSAGE_SIZE = 50 * 1024 * 1024
    
    # Параметры аудио
    TARGET_SAMPLE_RATE = 16000
    TARGET_CHANNELS = 1
    TARGET_DTYPE = "float32"
    
    # Пути
    BASE_DIR = Path(__file__).parent.parent
    LOG_DIR = BASE_DIR / "logs"
    MODEL_DIR = BASE_DIR / "models"
    
    @classmethod
    def from_env(cls):
        """Создание конфигурации из переменных окружения"""
        config = cls()
        
        config.host = os.getenv("SPEECHEQ_HOST", cls.DEFAULT_HOST)
        config.port = int(os.getenv("SPEECHEQ_PORT", cls.DEFAULT_PORT))
        config.max_workers = int(os.getenv("SPEECHEQ_MAX_WORKERS", cls.DEFAULT_MAX_WORKERS))
        config.max_message_size = int(
            os.getenv("SPEECHEQ_MAX_MESSAGE_SIZE", cls.DEFAULT_MAX_MESSAGE_SIZE)
        )
        
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        return config
    
    def __str__(self):
        return (
            f"ServerConfig(host={self.host}, port={self.port}, "
            f"max_workers={self.max_workers}, "
            f"max_message_size={self.max_message_size / 1024 / 1024:.1f}MB)"
        )