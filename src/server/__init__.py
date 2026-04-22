"""
Пакет серверной части SpeechEQ
"""
from src.server.grpc_server import AudioProcessorServicer, serve
from src.server.config import ServerConfig

__all__ = [
    'AudioProcessorServicer',
    'serve',
    'ServerConfig',
]