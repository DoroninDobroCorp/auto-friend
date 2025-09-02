#!/usr/bin/env python3
"""
Скрипт для запуска Telegram Userbot
"""
import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

if __name__ == "__main__":
    from app import run
    run()

