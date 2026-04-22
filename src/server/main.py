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
from processing.ml import (
    FRCRNSE16KMethod,
    MossFormerGANSE16KMethod,
    MetricGANPlusMethod,
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

    logging.getLogger("grpc").setLevel(logging.WARNING)


def setup_processing_pipeline() -> tuple[LocalAudioHandler, AudioProcessingLogic]:
    """
    Настройка пайплайна обработки аудио.

    Создаёт цепочку методов для улучшения речи в следующем порядке:
    1. FRCRN / MossFormerGAN / MetricGAN+ (ML) — основное улучшение и очистка речи
    2. NoiseReductionDSP — опциональная мягкая доочистка остаточного шума
    3. HumRemovalDSP — точечное удаление сетевого гула 50/60 Гц и гармоник
    4. DeEsserDSP — подавление сибилянтов (шипящих звуков)
    5. SpeechEQDSP — эквализация под речевой диапазон (финальный тембр)
    6. LoudnessNormalizationDSP — нормализация громкости (LUFS) и true-peak лимитинг

    ML-модель должна идти первой, так как она обучена на сыром сигнале.
    DSP-методы после неё лишь доводят звук и не создают артефактов.

    Returns:
        tuple: (LocalAudioHandler, AudioProcessingLogic) — готовый
               обработчик и его внутренняя логика.
    """
    logger = logging.getLogger(__name__)
    logger.info("Инициализация пайплайна обработки")

    processing_methods = [
        FRCRNSE16KMethod(preload=True),           # ML улучшение речи
        MossFormerGANSE16KMethod(preload=True),   # ML улучшение речи
        MetricGANPlusMethod(preload=True),        # ML улучшение речи
        NoiseReductionDSP(),                      # Шумоподавление
        HumRemovalDSP(),                          # Удаление гула 50/60 Гц
        DeEsserDSP(),                             # Подавление шипящих звуков
        SpeechEQDSP(),                            # Эквализация под речевой диапазон
        LoudnessNormalizationDSP(),               # Нормализация громкости
    ]

    processing_logic = AudioProcessingLogic(
        processing_methods=processing_methods,
    )

    audio_handler = LocalAudioHandler(processing_logic=processing_logic)

    logger.info(
        f"Пайплайн готов: {[m.__class__.__name__ for m in processing_methods]}"
    )

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