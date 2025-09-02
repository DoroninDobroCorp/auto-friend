#!/usr/bin/env python3
"""
Полная очистка и запуск бота
"""

import os
import signal
import subprocess
import time

def clean_kill_all_bots():
    """Принудительно убивает все экземпляры бота"""
    print("🧹 Полная очистка всех экземпляров бота...")
    
    try:
        # Способ 1: По имени процесса
        subprocess.run(['pkill', '-9', '-f', 'main_bot.py'], 
                      capture_output=True)
        
        # Способ 2: По имени файла
        subprocess.run(['pkill', '-9', '-f', 'python3.*main_bot.py'], 
                      capture_output=True)
        
        # Способ 3: По имени python
        subprocess.run(['pkill', '-9', '-f', 'python.*main_bot.py'], 
                      capture_output=True)
        
        time.sleep(2)
        
        # Проверяем, что все остановлены
        result = subprocess.run(['pgrep', '-f', 'main_bot.py'], 
                              capture_output=True, text=True)
        
        if not result.stdout:
            print("✅ Все процессы бота остановлены")
            return True
        else:
            print("⚠️ Некоторые процессы все еще работают")
            return False
            
    except Exception as e:
        print(f"⚠️ Ошибка при остановке: {e}")
        return False

def clean_telegram_cache():
    """Очищает кэш Telegram"""
    print("🗑️ Очищаю кэш Telegram...")
    
    try:
        # Очищаем возможные кэш-директории
        cache_dirs = [
            os.path.expanduser("~/.cache/telegram*"),
            os.path.expanduser("~/.local/share/telegram*"),
            os.path.expanduser("~/.telegram*")
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                subprocess.run(['rm', '-rf', cache_dir], 
                              capture_output=True)
                print(f"✅ Очищен кэш: {cache_dir}")
        
        print("✅ Кэш Telegram очищен")
        
    except Exception as e:
        print(f"⚠️ Ошибка при очистке кэша: {e}")

def start_bot():
    """Запускает бота"""
    print("🚀 Запускаю бота...")
    
    try:
        # Запускаем бота в фоне
        subprocess.Popen(['python3', 'main_bot.py'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        
        time.sleep(5)
        
        # Проверяем, что бот запустился
        result = subprocess.run(['pgrep', '-f', 'main_bot.py'], 
                              capture_output=True, text=True)
        
        if result.stdout:
            print("✅ Бот успешно запущен!")
            print(f"📊 PID: {result.stdout.strip()}")
            return True
        else:
            print("❌ Бот не запустился")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        return False

def main():
    """Главная функция"""
    print("🤖 Полная очистка и запуск бота")
    print("=" * 50)
    
    # Шаг 1: Останавливаем все экземпляры
    if not clean_kill_all_bots():
        print("❌ Не удалось остановить все процессы")
        return
    
    # Шаг 2: Очищаем кэш
    clean_telegram_cache()
    
    # Шаг 3: Ждем немного
    print("⏳ Ждем 3 секунды...")
    time.sleep(3)
    
    # Шаг 4: Запускаем бота
    if start_bot():
        print("\n🎉 Бот успешно запущен!")
        print("💡 Теперь протестируйте его в Telegram")
        print("🔍 Проверьте логи: tail -f logs/bot_*.log")
    else:
        print("\n❌ Не удалось запустить бота")
        print("💡 Проверьте конфигурацию и зависимости")

if __name__ == "__main__":
    main()
