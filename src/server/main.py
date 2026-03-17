"""
Точка входа для запуска gRPC сервера.
Создает AudioProcessingLogic один раз и передает его в сервер.
"""
import asyncio
import logging
import sys
import argparse
from pathlib import Path

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

proto_dir = root_dir / "proto"
if str(proto_dir) not in sys.path:
    sys.path.insert(0, str(proto_dir))

from server.grpc_server import serve
from server.config import ServerConfig

from processing.core.processing_logic import AudioProcessingLogic
from processing.handlers.local import LocalAudioHandler
from processing.dsp import (
    NoiseReductionDSP,
    HumRemovalDSP,
    DeEsserDSP,
    SpeechEQDSP,
    LoudnessNormalizationDSP
)


def setup_logging(debug: bool = False):
    """Настройка логирования"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Хендлер для файла
    log_dir = ServerConfig.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / "server.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Уменьшаем уровень логирования для grpc
    logging.getLogger("grpc").setLevel(logging.WARNING)


def setup_processing_pipeline():
    """
    Настройка пайплайна обработки аудио.
    Создает цепочку DSP-методов для улучшения речи.
    """
    logger = logging.getLogger(__name__)
    logger.info("Инициализация пайплайна обработки аудио на сервере")
    
    # Создание цепочки DSP-методов
    dsp_methods = [
        HumRemovalDSP(),           # Удаление гула 50/60 Гц
        NoiseReductionDSP(),       # Шумоподавление
        DeEsserDSP(),              # Де-эссер (удаление шипящих)
        SpeechEQDSP(),             # Эквализация под речь
        LoudnessNormalizationDSP(), # Нормализация громкости
    ]
    
    # Логика обработки с DSP-методами
    processing_logic = AudioProcessingLogic(
        dsp_methods=dsp_methods,
        ml_methods=[]  # ML-методы пока не используются
    )
    
    audio_handler = LocalAudioHandler(processing_logic=processing_logic)
    logger.info(f"Пайплайн инициализирован: {[method.__class__.__name__ for method in dsp_methods]}")
    return audio_handler, processing_logic


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="SpeechEQ gRPC Server")
    parser.add_argument(
        "--host",
        type=str,
        default=ServerConfig.DEFAULT_HOST,
        help=f"Хост для прослушивания (по умолчанию: {ServerConfig.DEFAULT_HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=ServerConfig.DEFAULT_PORT,
        help=f"Порт для прослушивания (по умолчанию: {ServerConfig.DEFAULT_PORT})"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=ServerConfig.DEFAULT_MAX_WORKERS,
        help=f"Максимальное количество рабочих потоков (по умолчанию: {ServerConfig.DEFAULT_MAX_WORKERS})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить режим отладки (больше логов)"
    )
    
    args = parser.parse_args()

    setup_logging(args.debug)

    logger = logging.getLogger(__name__)
    config = ServerConfig.from_env()

    if args.host != ServerConfig.DEFAULT_HOST:
        config.host = args.host
    if args.port != ServerConfig.DEFAULT_PORT:
        config.port = args.port
    if args.workers != ServerConfig.DEFAULT_MAX_WORKERS:
        config.max_workers = args.workers

    logger.info("=" * 60)
    logger.info("Инициализация обработчика аудио")
    audio_handler, processing_logic = setup_processing_pipeline()
    logger.info("=" * 60)

    logger.info(f"Запуск сервера с конфигурацией: {config}")
    
    try:
        asyncio.run(serve(config, audio_handler))
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
        return 0
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())