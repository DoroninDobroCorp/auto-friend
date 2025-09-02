#!/usr/bin/env python3
"""
Тестирование логики упоминаний бота
"""

from core.config import Config

def test_mention_detection():
    """Тестирует логику определения упоминаний"""
    config = Config.load()
    
    print("🔍 Тестирование конфигурации упоминаний")
    print("=" * 50)
    
    print(f"🤖 Имя бота: {config.bot.name}")
    print(f"👤 Username бота: {config.bot.username}")
    print(f"🔑 Токен: {config.bot.token[:20]}...")
    
    print("\n📝 Тестовые сообщения для упоминаний:")
    print("-" * 40)
    
    test_messages = [
        f"@{config.bot.username} привет!",
        f"Эй, {config.bot.name}, как дела?",
        "Бот, помоги с Python",
        "Слушай, ассистент, что думаешь?",
        "Помогите, бот!",
        "Что думаете о программировании?",
        "Как сделать API на Python?",
        "Привет всем!",
        "Спасибо за помощь!"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i:2d}. {message}")
    
    print("\n🎯 Ожидаемое поведение:")
    print("-" * 40)
    print("✅ Сообщения 1-5: Бот ДОЛЖЕН ответить (упоминание)")
    print("✅ Сообщения 6-7: Бот МОЖЕТ ответить (тематика)")
    print("❌ Сообщения 8-9: Бот НЕ должен отвечать")
    
    print("\n💡 Как тестировать в Telegram:")
    print("-" * 40)
    print("1. Добавьте бота в группу")
    print("2. Отправьте одно из тестовых сообщений")
    print("3. Проверьте логи: tail -f logs/bot_*.log")
    print("4. Убедитесь, что бот отвечает на упоминания")

if __name__ == "__main__":
    test_mention_detection()
