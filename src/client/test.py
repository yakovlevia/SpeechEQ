# src/client/test.py
from pathlib import Path

from client.batch_media_processor import BatchMediaProcessor
from processing.local import LocalEngine
from processing.settings import ProcessingSettings


def main():
    # Только флаги: какие методы включать
    settings = ProcessingSettings(
        dehum_notch=True,
        ml_model=False,
    )

    engine = LocalEngine(settings=settings)

    processor = BatchMediaProcessor(
        engine=engine,
        block_size=65536,
        out_subtype="PCM_16",
        # полезно привести всё к одному формату (особенно перед ML в будущем)
        target_sr=48000,
        target_channels=2,
        video_codec="copy",  # Копируем видео без перекодирования
        audio_codec="aac",   # Используем AAC для аудио в MP4
        audio_bitrate="192k", # Битрейт аудио
    )

    inputs = [
        Path("/mnt/d/diplom/video1.mp4"),
    ]

    results = processor.process_many(inputs, output_dir=Path("out_video"))
    for r in results:
        print(f"{r.input_path} ->")
        print(f"  Audio: {r.output_audio_path} (sr={r.sample_rate}, ch={r.channels})")
        print(f"  Video: {r.output_video_path}")


if __name__ == "__main__":
    main()