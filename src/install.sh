#!/bin/bash

# install.sh - установка зависимостей для Async Video Audio Processor
# Минимальная версия для Ubuntu/WSL

set -e

echo "=========================================="
echo "  Установка Async Video Audio Processor"
echo "=========================================="
echo ""

# Переход в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Текущая директория: $(pwd)"
echo ""

# Проверка Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен. Установите:"
    echo "   sudo apt install python3 python3-pip"
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "🐍 Версия Python: $PYTHON_VERSION"

# Обновление пакетов
echo ""
echo "🔄 Обновление списка пакетов..."
sudo apt-get update -qq

# Установка FFmpeg
echo ""
echo "🎬 Установка FFmpeg..."
sudo apt-get install -y -qq ffmpeg

# Установка системных зависимостей
echo ""
echo "📦 Установка системных зависимостей..."
sudo apt-get install -y -qq \
    python3-venv \
    python3-dev \
    libsndfile1 \
    libasound2-dev

# Удаление старого venv если есть
if [ -d "venv" ]; then
    echo ""
    echo "🗑️  Удаление старого виртуального окружения..."
    rm -rf venv
fi

# Создание виртуального окружения
echo ""
echo "🔧 Создание виртуального окружения 'venv'..."
python3 -m venv venv

# Активация venv и установка Python пакетов
echo ""
echo "📚 Установка Python пакетов..."
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Основные зависимости для асинхронной обработки видео/аудио
echo "Установка основных зависимостей..."
pip install \
    numpy \
    librosa \
    soundfile \
    moviepy \
    aiofiles \
    tqdm

echo ""
echo "=========================================="
echo "✅ Установка завершена!"
echo "=========================================="
echo ""
echo "🎯 Активируйте виртуальное окружение:"
echo "   source venv/bin/activate"
echo ""
echo "💡 Для деактивации виртуального окружения:"
echo "   deactivate"
echo "=========================================="