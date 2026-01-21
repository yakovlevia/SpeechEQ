#!/bin/bash

# run_example.sh - запуск примера Video Audio Processor

echo "Запуск Video Audio Processor..."
echo ""

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено."
    echo "Сначала запустите установку:"
    echo "  ./install.sh"
    exit 1
fi

# Проверка FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg не установлен."
    echo "Установите: sudo apt install ffmpeg"
    exit 1
fi

# Активация виртуального окружения
echo "Активация виртуального окружения..."
source venv/bin/activate

# Создание директорий если их нет
mkdir -p input output

# Запуск примера
echo "Запуск example.py..."
echo ""
python3 example.py