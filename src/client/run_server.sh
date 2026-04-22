#!/bin/bash

# run_server.sh - запуск gRPC сервера SpeechEQ

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено."
    echo "   Сначала выполните: ./install.sh"
    exit 1
fi

source venv/bin/activate

echo "=========================================="
echo "🖥️  Запуск сервера SpeechEQ"
echo "=========================================="
echo ""

python -m server.main "$@"
