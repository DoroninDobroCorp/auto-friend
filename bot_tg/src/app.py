"""
Главный файл приложения - точка входа
"""
import asyncio
import logging
import sys
import os
import uvloop
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.memory.store import store
from src.clients.telegram_client import userbot

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    log_level = getattr(logging, settings.log_level.upper())
    
    # Создаём директорию для логов
    os.makedirs('logs', exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Хендлер для файла
    file_handler = logging.FileHandler(
        f'logs/userbot_{settings.log_level.lower()}.log',
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Устанавливаем уровень для сторонних библиотек
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


async def main():
    """Главная функция приложения"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Запуск Telegram Userbot...")
        
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await store.init_db()
        logger.info("База данных инициализирована")
        
        # Запуск userbot
        logger.info("Запуск Telegram клиента...")
        await userbot.run_forever()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    finally:
        # Очистка ресурсов
        logger.info("Остановка приложения...")
        await userbot.stop()
        logger.info("Приложение остановлено")


def run():
    """Функция для запуска приложения"""
    # Настройка asyncio
    if sys.platform.startswith('linux'):
        uvloop.install()
    
    # Настройка логирования
    setup_logging()
    
    # Запуск главной функции
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПриложение остановлено пользователем")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()

