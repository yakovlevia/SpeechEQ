#!/usr/bin/env python3
"""
Точка входа для запуска gRPC-сервера обработки аудио.

Инициализирует пайплайн обработки (DSP-методы) один раз при старте
и передаёт готовый обработчик в gRPC-сервер для многопоточного использования.
"""
import asyncio
import logging
import sys
import argparse
from pathlib import Path

# Настройка путей для импортов
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
    LoudnessNormalizationDSP,
)


def setup_logging(debug: bool = False) -> None:
    """Настраивает систему логирования с выводом в консоль и файл.

    Создаёт обработчики для stdout и файла серверного лога,
    устанавливает уровень детализации и формат сообщений.

    Args:
        debug: Если True — устанавливает уровень DEBUG, иначе INFO.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    log_dir = ServerConfig.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "server.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Снижаем детализацию логов gRPC — они слишком шумные
    logging.getLogger("grpc").setLevel(logging.WARNING)


def setup_processing_pipeline() -> tuple[LocalAudioHandler, AudioProcessingLogic]:
    """Создаёт и настраивает пайплайн обработки аудио.

    Формирует цепочку DSP-методов в строгом порядке:
    1. Удаление сетевого гула (50/60 Гц)
    2. Шумоподавление
    3. Де-эссер (подавление шипящих)
    4. Речевой эквалайзер
    5. Нормализация громкости (финальный этап)

    Порядок критичен: например, нормализация должна идти последней,
    чтобы не исказить результаты предыдущих этапов.

    Returns:
        tuple: (LocalAudioHandler, AudioProcessingLogic) — готовый
               обработчик и его внутренняя логика.
    """
    logger = logging.getLogger(__name__)
    logger.info("Инициализация пайплайна обработки")

    # Порядок методов важен — см. docstring функции
    dsp_methods = [
        HumRemovalDSP(),              # Удаление гула 50/60 Гц
        NoiseReductionDSP(),          # Шумоподавление
        DeEsserDSP(),                 # Подавление шипящих звуков
        SpeechEQDSP(),                # Эквализация под речевой диапазон
        LoudnessNormalizationDSP(),   # Нормализация громкости (последний этап)
    ]

    processing_logic = AudioProcessingLogic(
        dsp_methods=dsp_methods,
        ml_methods=[]  # ML-методы пока не используются
    )

    audio_handler = LocalAudioHandler(processing_logic=processing_logic)
    logger.info(f"Пайплайн готов: {[m.__class__.__name__ for m in dsp_methods]}")
    return audio_handler, processing_logic


def main() -> int:
    """Точка входа в приложение.

    Парсит аргументы командной строки, инициализирует логирование,
    создаёт обработчик аудио и запускает gRPC-сервер.

    Returns:
        int: Код завершения (0 — успех, 1 — ошибка).
    """
    parser = argparse.ArgumentParser(description="SpeechEQ gRPC Server")
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help=f"Хост для прослушивания (по умолчанию: {ServerConfig.DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Порт для прослушивания (по умолчанию: {ServerConfig.DEFAULT_PORT})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"Макс. количество потоков (по умолчанию: {ServerConfig.DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить режим отладки (подробные логи)",
    )

    args = parser.parse_args()
    setup_logging(args.debug)

    logger = logging.getLogger(__name__)

    # Загрузка конфигурации: env-переменные + переопределение из CLI
    config = ServerConfig.from_env()
    if args.host is not None:
        config.host = args.host
    if args.port is not None:
        config.port = args.port
    if args.workers is not None:
        config.max_workers = args.workers

    logger.info("Инициализация обработчика аудио")
    audio_handler, _ = setup_processing_pipeline()

    logger.info(f"Запуск сервера: {config}")

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