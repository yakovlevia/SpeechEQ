"""
Генерирует 3 демо-видео: (noisy + clean) × 4 из случайных пар examples/,
затем прогоняет каждое через два пайплайна проекта.

  video_examples/
    demo.mp4 / .mkv / .mov          — исходные демо-видео
    output/
      demo_frcrn.mp4 / .mkv / .mov  — FRCRN + нормализация
      demo_full.mp4  / .mkv / .mov  — все DSP + FRCRN + нормализация

Запуск:
  python create_demo_videos.py
  python create_demo_videos.py --ffmpeg /path/to/ffmpeg  --no-process
"""

import argparse
import asyncio
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

OUTPUT_DIR   = Path("video_examples")
EXAMPLES_DIR = Path("examples")
N_REPS       = 4

FORMATS = ["mp4", "mkv", "mov"]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]

RED   = "0xEF5350"
GREEN = "0x66BB6A"


# ── Утилиты ───────────────────────────────────────────────────────────────────

def _find_font() -> str:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return ""


def _e(t: float) -> str:
    return f"{t:.3f}"


def _enable(i: int, n: int, t_start: float, t_end: float) -> str:
    if i == 0:
        return f"enable='lte(t\\,{_e(t_end)})'"
    if i == n - 1:
        return f"enable='gte(t\\,{_e(t_start)})'"
    return f"enable='between(t\\,{_e(t_start)}\\,{_e(t_end)})'"


# ── Создание демо-видео ───────────────────────────────────────────────────────

def create_demo(fmt: str, ffmpeg: str) -> None:
    available = sorted(
        int(p.stem.split("_")[1])
        for p in (EXAMPLES_DIR / "noisy").glob("noisy_*.wav")
    )
    if not available:
        print("  [!] Нет файлов в examples/noisy/")
        sys.exit(1)

    chosen = random.sample(available, min(N_REPS, len(available)))
    if len(chosen) < N_REPS:
        chosen += random.choices(available, k=N_REPS - len(chosen))

    segments = []
    for idx in chosen:
        noisy, sr = sf.read(str(EXAMPLES_DIR / "noisy" / f"noisy_{idx}.wav"), dtype="float32")
        clean, _  = sf.read(str(EXAMPLES_DIR / "clean" / f"clean_{idx}.wav"), dtype="float32")
        segments.append((noisy, f"noisy_{idx}", True))
        segments.append((clean, f"clean_{idx}", False))

    combined = np.concatenate([s[0] for s in segments]).astype(np.float32)

    times = [0.0]
    for audio, _, _ in segments:
        times.append(times[-1] + len(audio) / sr)

    tmp_wav = OUTPUT_DIR / f"_tmp_{fmt}.wav"
    sf.write(str(tmp_wav), combined, sr)

    output_path = OUTPUT_DIR / f"demo.{fmt}"
    font = _find_font()
    fopt = f":fontfile={font}" if font else ""
    n = len(segments)

    filters = []
    vi = 0

    def node() -> str:
        nonlocal vi
        vi += 1
        return f"v{vi}"

    prev = "bg"
    filters.append("color=c=black:s=1280x720:r=25[bg]")

    for i, (_, _, is_noisy) in enumerate(segments):
        color = RED if is_noisy else GREEN
        out = node()
        filters.append(
            f"[{prev}]drawbox=x=0:y=0:w=iw:h=ih:color={color}@0.13:t=fill:"
            f"{_enable(i, n, times[i], times[i+1])}[{out}]"
        )
        prev = out

    for i, (_, _, is_noisy) in enumerate(segments):
        color = RED if is_noisy else GREEN
        out = node()
        filters.append(
            f"[{prev}]drawbox=x=0:y=356:w=iw:h=4:color={color}@0.9:t=fill:"
            f"{_enable(i, n, times[i], times[i+1])}[{out}]"
        )
        prev = out

    filters.append("[0:a]showwaves=s=1280x360:mode=cline:rate=25:colors=#81D4FA[wave]")
    wv_out = node()
    filters.append(f"[{prev}][wave]overlay=0:360[{wv_out}]")
    prev = wv_out

    for i, (_, label, is_noisy) in enumerate(segments):
        color = RED if is_noisy else GREEN
        out = node()
        filters.append(
            f"[{prev}]drawtext=text='{label}':fontsize=60{fopt}:"
            f"fontcolor={color}:x=(w-text_w)/2:y=120:"
            f"{_enable(i, n, times[i], times[i+1])}[{out}]"
        )
        prev = out

    pairs_str = "  |  ".join(f"noisy_{idx}+clean_{idx}" for idx in chosen)
    filters.append(
        f"[{prev}]drawtext=text='{pairs_str}':fontsize=20{fopt}:"
        f"fontcolor=0x555555:x=(w-text_w)/2:y=h-36[vout]"
    )

    fc = ";".join(filters)

    cmd = [
        ffmpeg,
        "-i", str(tmp_wav),
        "-filter_complex", fc,
        "-map", "[vout]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-r", "25",
        "-shortest",
        "-y", str(output_path),
    ]

    print(f"Создание demo.{fmt}  ({times[-1]:.1f}s, пары: {chosen}) ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    tmp_wav.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"  Ошибка FFmpeg:\n{result.stderr[-2000:]}")
        sys.exit(1)

    size_kb = output_path.stat().st_size / 1024
    print(f"  → {output_path}  ({size_kb:.0f} KB)")


# ── Обработка через пайплайны проекта ────────────────────────────────────────

def build_pipelines():
    """
    Собирает два пайплайна из инфраструктуры проекта.

    Возвращает список: [(name, handler, settings), ...]
      frcrn  — FRCRN + нормализация громкости
      full   — все DSP + FRCRN + нормализация (лучший пайплайн)
    """
    from src.processing.core.processing_logic import AudioProcessingLogic
    from src.processing.core.settings import ProcessingSettings
    from src.processing.handlers.local import LocalAudioHandler
    from src.processing.dsp.noise_reduction import NoiseReductionDSP
    from src.processing.dsp.speech_eq import SpeechEQDSP
    from src.processing.dsp.loudness_normalization import LoudnessNormalizationDSP
    from src.processing.ml.frcrn_se_16k import FRCRNSE16KMethod

    print("Загрузка FRCRN (один раз для обоих пайплайнов)...")
    frcrn = FRCRNSE16KMethod(preload=True)

    # ── Пайплайн 1: FRCRN + нормализация ─────────────────────────────────────
    frcrn_settings = ProcessingSettings(
        noise_reduction=False,
        hum_removal=False,
        deesser=False,
        eq=False,
        normalization=True,
        ml_model_name="FRCRN_SE_16K",
        ml_strength=1.0,
    )
    frcrn_handler = LocalAudioHandler(
        AudioProcessingLogic([frcrn, LoudnessNormalizationDSP()])
    )

    # ── Пайплайн 2: DSP + FRCRN + нормализация ───────────────────────────────
    full_settings = ProcessingSettings(
        noise_reduction=True,
        noise_reduction_level=0.3,
        hum_removal=False,
        deesser=False,
        eq=True,
        normalization=True,
        ml_model_name="FRCRN_SE_16K",
        ml_strength=1.0,
    )
    full_handler = LocalAudioHandler(
        AudioProcessingLogic([
            NoiseReductionDSP(),
            SpeechEQDSP(),
            frcrn,
            LoudnessNormalizationDSP(),
        ])
    )

    return [
        ("frcrn", frcrn_handler, frcrn_settings),
        ("full",  full_handler,  full_settings),
    ]


async def _run_task(input_path: Path, output_path: Path, handler, settings) -> None:
    from src.client.video_processor import VideoProcessor
    from src.client.video_queue import AudioCleanupTask

    output_path.parent.mkdir(parents=True, exist_ok=True)

    task = AudioCleanupTask(
        input_path=str(input_path),
        output_path=str(output_path),
        handler=handler,
        handler_settings=settings,
    )
    processor = VideoProcessor()
    await processor.process_video(task)


def process_video(input_path: Path, output_path: Path, handler, settings) -> None:
    asyncio.run(_run_task(input_path, output_path, handler, settings))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Создание и обработка демо-видео")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="Путь к ffmpeg")
    parser.add_argument("--no-process", action="store_true",
                        help="Только создать демо-видео, без обработки")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    # ── Шаг 1: создать демо-видео ─────────────────────────────────────────────
    print("=== Создание демо-видео ===")
    for fmt in FORMATS:
        create_demo(fmt, args.ffmpeg)

    if args.no_process:
        print(f"\nГотово. Видео сохранены в {OUTPUT_DIR}/")
        return

    # ── Шаг 2: прогнать через пайплайны проекта ───────────────────────────────
    print("\n=== Обработка через пайплайны проекта ===")
    pipelines = build_pipelines()
    out_dir = OUTPUT_DIR / "output"

    for fmt in FORMATS:
        demo_path = OUTPUT_DIR / f"demo.{fmt}"
        for pipe_name, handler, settings in pipelines:
            out_path = out_dir / f"demo_{pipe_name}.{fmt}"
            print(f"\ndemo.{fmt}  →  {out_path.name}  ({pipe_name}) ...")
            process_video(demo_path, out_path, handler, settings)
            size_kb = out_path.stat().st_size / 1024
            print(f"  ✓  {out_path}  ({size_kb:.0f} KB)")

    print(f"\n=== Готово ===")
    print(f"  Исходные демо:  {OUTPUT_DIR}/demo.{{mp4,mkv,mov}}")
    print(f"  FRCRN:          {out_dir}/demo_frcrn.{{mp4,mkv,mov}}")
    print(f"  Full DSP+FRCRN: {out_dir}/demo_full.{{mp4,mkv,mov}}")


if __name__ == "__main__":
    main()
