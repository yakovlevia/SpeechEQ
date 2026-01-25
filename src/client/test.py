# src/client/test.py
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
from processing.handlers.local import LocalAudioHandler

from processing.dsp.noise_reduction import NoiseReductionDSP
from processing.dsp.normalization import NormalizationDSP

logic = AudioProcessingLogic(
    dsp_methods=[
        NoiseReductionDSP(),
        NormalizationDSP(),
    ],
    ml_methods=[]
)

settings = ProcessingSettings(
    noise_reduction=True,
    normalization=True,
)

handlers = [LocalAudioHandler(processing_logic=logic)]


async def process_videos():
    """Основная функция для обработки видео"""
    handler = handlers[0]
    
    video_files = [
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
        
        final_output_path = base_dir / f"{Path(video_path).stem}_final.mp4"
        
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