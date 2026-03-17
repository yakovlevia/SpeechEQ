"""
Пакет серверной части SpeechEQ
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

proto_dir = root_dir / "proto"
if str(proto_dir) not in sys.path:
    sys.path.insert(0, str(proto_dir))

from .grpc_server import AudioProcessorServicer, serve
from .config import ServerConfig

__all__ = [
    'AudioProcessorServicer',
    'serve',
    'ServerConfig',
]