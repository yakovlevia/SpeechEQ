#!/bin/bash

# install.sh - установка зависимостей для SpeechEQ
# Ubuntu / Debian / WSL

set -e

echo "=========================================="
echo "       Установка SpeechEQ"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Текущая директория: $(pwd)"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен."
    echo "   Установите: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "🐍 Версия Python: $PYTHON_VERSION"

echo ""
echo "🔄 Обновление списка пакетов..."
sudo apt-get update -qq

echo ""
echo "📦 Установка системных зависимостей..."
sudo apt-get install -y -qq \
    ffmpeg \
    python3-venv \
    python3-dev \
    build-essential \
    pkg-config \
    libsndfile1 \
    libsndfile1-dev \
    libasound2-dev \
    libffi-dev \
    libssl-dev

# Удаление старого venv
if [ -d "venv" ]; then
    echo ""
    echo "🗑️  Удаление старого виртуального окружения..."
    rm -rf venv
fi

echo ""
echo "🔧 Создание виртуального окружения..."
python3 -m venv venv

echo ""
echo "📚 Установка Python зависимостей..."
source venv/bin/activate

python -m pip install --upgrade pip setuptools wheel

# CPU-версия torch по умолчанию.
# Если нужна CUDA-версия, её лучше ставить отдельно под конкретную систему.
python -m pip install \
    "numpy>=1.21.0" \
    "librosa>=0.10.0" \
    "tqdm>=4.65.0" \
    "psutil>=5.9.0" \
    "soundfile>=0.12.0" \
    "PySide6==6.10.0" \
    "grpcio>=1.50.0" \
    "grpcio-tools>=1.50.0" \
    "protobuf>=4.21.0" \
    "torch>=2.0.0" \
    "scipy>=1.10.0" \
    "pyloudnorm>=0.1.1" \
    "noisereduce>=3.0.0" \
    "speechbrain>=0.5.15" \
    "einops>=0.7.0" \
    "rotary-embedding-torch>=0.3.0" \
    "packaging>=23.0"

echo ""
echo "=========================================="
echo "✅ Установка завершена!"
echo "=========================================="
echo ""
echo "🎯 Активировать окружение:"
echo "   source venv/bin/activate"
echo ""
echo "🚀 Запуск клиента:"
echo "   ./run_app.sh"
echo ""
echo "🖥️  Запуск сервера:"
echo "   ./run_server.sh"
echo ""
echo "💡 Деактивация окружения:"
echo "   deactivate"
echo "=========================================="
