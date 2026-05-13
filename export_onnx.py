"""
Экспорт ML моделей в ONNX формат для ускорения через ONNX Runtime.

Запуск:
    python export_onnx.py
    python export_onnx.py --model frcrn          # только FRCRN
    python export_onnx.py --model mossformer     # только MossFormerGAN
    python export_onnx.py --force                # перезаписать существующие .onnx

Файлы сохраняются рядом с .pt весами:
    src/processing/ml/models/FRCRN_SE_16K.onnx
    src/processing/ml/models/MossFormerGAN_SE_16K.onnx
"""

import sys
import argparse
from pathlib import Path

import torch
import torch.nn as nn
import onnx
import onnxruntime as ort

sys.path.insert(0, ".")


MODELS_DIR = Path("src/processing/ml/models")
SAMPLE_RATE = 16000


def validate_onnx(onnx_path: Path):
    model = onnx.load(str(onnx_path))
    onnx.checker.check_model(model)
    print(f"    ONNX валидация: OK")


def make_ort_session(onnx_path: Path) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])


# ─── FRCRN ───────────────────────────────────────────────────────────────────

def export_frcrn(force: bool):
    onnx_path = MODELS_DIR / "FRCRN_SE_16K.onnx"
    if onnx_path.exists() and not force:
        print(f"  FRCRN_SE_16K: уже экспортирован ({onnx_path}), пропускаем (--force чтобы перезаписать)")
        return

    print("  FRCRN_SE_16K: загрузка модели...")
    from src.processing.ml.frcrn_se_16k import FRCRNSE16KMethod
    method = FRCRNSE16KMethod(preload=True)

    class _Wrapper(nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m
        def forward(self, x):
            return self.m.inference(x)

    model_cpu = method.model.cpu()
    wrapper = _Wrapper(model_cpu)
    wrapper.eval()

    dummy = torch.zeros(1, SAMPLE_RATE)  # 1s аудио

    print(f"  FRCRN_SE_16K: экспорт в {onnx_path} ...")
    torch.onnx.export(
        wrapper,
        dummy,
        str(onnx_path),
        input_names=["waveform"],
        output_names=["enhanced"],
        dynamic_axes={"waveform": {1: "length"}, "enhanced": {0: "length"}},
        opset_version=17,
        do_constant_folding=True,
    )

    validate_onnx(onnx_path)
    size_mb = onnx_path.stat().st_size / 1024 / 1024
    print(f"  FRCRN_SE_16K: готово, размер {size_mb:.1f} MB")

    print("  FRCRN_SE_16K: тест ORT сессии...")
    session = make_ort_session(onnx_path)
    test_in = dummy.numpy()
    out = session.run(None, {"waveform": test_in})[0]
    print(f"  FRCRN_SE_16K: ORT тест OK, выход shape={out.shape}")


# ─── MossFormerGAN ───────────────────────────────────────────────────────────

def export_mossformer(force: bool):
    # MossFormerGAN использует torch.complex() в attention-механизме (MossFormer).
    # aten::complex не поддерживается ни в одном ONNX opset — экспорт невозможен
    # без переписывания модели. Используем PyTorch inference as-is.
    print("  MossFormerGAN_16K: ПРОПУСК — архитектура использует aten::complex")
    print("    (torch.complex в attention не поддерживается ONNX ни в одном opset)")
    print("    Модель продолжит работать через обычный PyTorch.")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Экспорт ML моделей в ONNX")
    parser.add_argument("--model", choices=["frcrn", "mossformer", "all"], default="all")
    parser.add_argument("--force", action="store_true", help="Перезаписать существующие .onnx")
    args = parser.parse_args()

    print(f"torch: {torch.__version__}")
    print(f"onnxruntime: {ort.__version__}")
    print(f"onnx: {onnx.__version__}")
    print()

    try:
        if args.model in ("frcrn", "all"):
            export_frcrn(args.force)
            print()
        if args.model in ("mossformer", "all"):
            export_mossformer(args.force)
            print()
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("Готово. Теперь запускай benchmark_processing.py — ONNX Runtime подхватится автоматически.")


if __name__ == "__main__":
    main()
