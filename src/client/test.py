# ФАЙЛ: client/test.py
import asyncio
import logging
from pathlib import Path
import sys

from client.video_queue import AudioCleanupTask

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug.log')
    ]
)
logger = logging.getLogger(__name__)

from client.processing_manager import ProcessingManager
from processing.core.processing_logic import AudioProcessingLogic
from processing.core.settings import ProcessingSettings

from processing.dsp import (
    NoiseReductionDSP,
    HumRemovalDSP,
    DeEsserDSP,
    SpeechEQDSP,
    LoudnessNormalizationDSP
)

logic = AudioProcessingLogic(
    dsp_methods=[
        HumRemovalDSP(),
        NoiseReductionDSP(),
        DeEsserDSP(),
        SpeechEQDSP(),
        LoudnessNormalizationDSP(),
    ],
    ml_methods=[]
)

settings = ProcessingSettings(
    hum_removal=True,            # Включить удаление гула
    hum_frequency=50.0,          # 50 Гц (для Европы)
    hum_removal_strength=0.8,    # Сила удаления
    
    noise_reduction=True,        # Включить подавление шума
    noise_reduction_level=0.7,   # Уровень подавления
    
    deesser=True,                # Включить де-эссер
    deesser_strength=0.6,        # Сила де-эссера
    
    eq=True,                     # Включить эквалайзер
    eq_profile="speech_clarity", # Профиль для разборчивости речи
    
    normalization=True,          # Включить нормализацию
    normalization_target=-16.0,  # Целевой уровень -16 LUFS
)

from processing.handlers.local import LocalAudioHandler

handlers = [LocalAudioHandler(processing_logic=logic)]


async def process_videos():
    """Основная функция для обработки видео"""
    handler = handlers[0]
    
    video_files = [
        "/mnt/d/diplom/video_small.mp4",
        "/mnt/d/diplom/video1.mp4",
    ]
    
    manager = ProcessingManager()
    
    for i, video_path in enumerate(video_files):
        if not Path(video_path).exists():
            logger.error(f"Файл не найден: {video_path}")
            continue
    
        priority = i + 1
        
        base_dir = Path("/mnt/d/diplom")
        
        # Видео без аудио будет сохранено в скрытую папку .video
        video_no_audio_dir = base_dir / ".video"
        video_no_audio_dir.mkdir(exist_ok=True)
        
        # Аудио фрагменты будут сохранены в скрытую папку .audio
        audio_fragments_dir = base_dir / ".audio"
        audio_fragments_dir.mkdir(exist_ok=True)
        
        final_output_path = base_dir / f"{Path(video_path).stem}_processed.mp4"
        
        task = AudioCleanupTask(
            priority=priority,
            input_path=video_path,
            output_path=final_output_path,
            handler=handler,
            handler_settings=settings
        )
        
        manager.add_video_task(task)
        logger.info(f"Добавлена задача: {video_path} (приоритет: {priority})")
    
    await manager.start_processing()


if __name__ == "__main__":
    asyncio.run(process_videos())