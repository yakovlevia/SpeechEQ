#!/bin/bash

# install.sh — установка SpeechEQ
# Поддерживаемые платформы: Ubuntu/Debian, macOS

set -e

echo "=========================================="
echo "       Установка SpeechEQ"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ─── Определение ОС ──────────────────────────────────────────────────────────

detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "Платформа: $OS"
echo ""

# ─── Поиск Python 3.10+ ──────────────────────────────────────────────────────

find_python() {
    for cmd in python3.10 python3.11 python3.12 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python || true)

# ─── Установка Python 3.10, если не найден ───────────────────────────────────

if [ -z "$PYTHON" ]; then
    echo "Python 3.10+ не найден. Устанавливаю..."
    echo ""

    if [ "$OS" = "macos" ]; then
        if ! command -v brew &>/dev/null; then
            echo "Homebrew не установлен. Установите его с https://brew.sh и повторите."
            exit 1
        fi
        brew install python@3.10
        PYTHON=$(brew --prefix python@3.10)/bin/python3.10

    elif [ "$OS" = "debian" ]; then
        sudo apt-get update -qq
        # Пробуем установить из основного репозитория
        if apt-cache show python3.10 &>/dev/null 2>&1; then
            sudo apt-get install -y -qq python3.10 python3.10-venv python3.10-dev
        else
            # Добавляем deadsnakes PPA для Ubuntu
            sudo apt-get install -y -qq software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3.10 python3.10-venv python3.10-dev
        fi
        PYTHON=python3.10

    else
        echo "Неизвестная платформа. Установите Python 3.10+ вручную: https://www.python.org/downloads/"
        exit 1
    fi

    # Перепроверка после установки
    PYTHON=$(find_python || true)
    if [ -z "$PYTHON" ]; then
        echo "Не удалось найти Python 3.10+ после установки."
        exit 1
    fi
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "Python: $PYTHON ($PY_VER)"
echo ""

# ─── Системные зависимости ───────────────────────────────────────────────────

if [ "$OS" = "debian" ]; then
    echo "Установка системных зависимостей..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        ffmpeg \
        python3-venv \
        build-essential \
        pkg-config \
        libsndfile1 \
        libsndfile1-dev \
        libasound2-dev \
        libffi-dev \
        libssl-dev

elif [ "$OS" = "macos" ]; then
    if ! command -v brew &>/dev/null; then
        echo "Homebrew не найден. Установите: https://brew.sh"
        exit 1
    fi
    echo "Установка системных зависимостей (brew)..."
    brew install ffmpeg libsndfile 2>/dev/null || true
fi

# Проверка FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo ""
    echo "[!] FFmpeg не найден в PATH. Убедитесь, что он установлен и доступен."
fi

echo ""

# ─── Виртуальное окружение ───────────────────────────────────────────────────

if [ -d "venv" ]; then
    echo "Удаление старого виртуального окружения..."
    rm -rf venv
fi

echo "Создание виртуального окружения..."
"$PYTHON" -m venv venv

echo ""
echo "Установка зависимостей..."
source venv/bin/activate

python -m pip install --upgrade pip setuptools wheel -q

python -m pip install -r requirements.txt

echo ""
echo "=========================================="
echo "        Установка завершена!"
echo "=========================================="
echo ""
echo "Запуск клиента:  ./run_app.sh"
echo "Запуск сервера:  ./run_server.sh"
echo "=========================================="
