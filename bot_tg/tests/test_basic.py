"""
Базовые тесты для Telegram Userbot
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, date

# Импорты для тестирования
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Settings
from memory.store import DatabaseStore
from moderation.safety import ContentModerator
from dialog.manager import DialogManager


class TestConfig:
    """Тесты конфигурации"""
    
    def test_settings_validation(self):
        """Тест валидации настроек"""
        # Тест с корректными данными
        settings = Settings(
            api_id=12345,
            api_hash="test_hash",
            phone_number="+1234567890",
            openai_api_key="test_key"
        )
        
        assert settings.api_id == 12345
        assert settings.api_hash == "test_hash"
        assert settings.phone_number == "+1234567890"
        assert settings.openai_api_key == "test_key"
    
    def test_group_keywords_parsing(self):
        """Тест парсинга ключевых слов"""
        settings = Settings(
            api_id=12345,
            api_hash="test_hash",
            phone_number="+1234567890",
            openai_api_key="test_key",
            group_keywords="совет,опыт,помощь"
        )
        
        assert "совет" in settings.group_keywords_list
        assert "опыт" in settings.group_keywords_list
        assert "помощь" in settings.group_keywords_list
        assert len(settings.group_keywords_list) == 3


class TestContentModeration:
    """Тесты модерации контента"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.moderator = ContentModerator()
    
    def test_safe_message(self):
        """Тест безопасного сообщения"""
        is_safe, reason, replacement = self.moderator.check_message_safety(
            "Привет! Как дела?"
        )
        
        assert is_safe is True
        assert reason == "safe"
        assert replacement is None
    
    def test_forbidden_topic(self):
        """Тест запрещённой темы"""
        is_safe, reason, replacement = self.moderator.check_message_safety(
            "Давайте обсудим политику"
        )
        
        assert is_safe is False
        assert "forbidden_topic" in reason
        assert replacement is not None
    
    def test_toxic_content(self):
        """Тест токсичного контента"""
        is_safe, reason, replacement = self.moderator.check_message_safety(
            "Ты идиот!"
        )
        
        assert is_safe is False
        assert reason == "toxic_content"
        assert replacement is not None
    
    def test_spam_detection(self):
        """Тест обнаружения спама"""
        is_safe, reason, replacement = self.moderator.check_message_safety(
            "Купить сейчас! Скидка 50%! Подписывайтесь!"
        )
        
        assert is_safe is False
        assert reason == "spam_detected"
        assert replacement is not None
    
    def test_group_message_filter(self):
        """Тест фильтра групповых сообщений"""
        # Сообщение с ключевым словом
        result = self.moderator.filter_group_message(
            "Можете дать совет по программированию?"
        )
        assert result is True
        
        # Сообщение без ключевых слов
        result = self.moderator.filter_group_message(
            "Привет всем!"
        )
        assert result is False
    
    def test_quiet_hours(self):
        """Тест тихих часов"""
        # Тест в тихие часы (23:00)
        from datetime import time
        quiet_time = time(23, 30)
        assert self.moderator.is_quiet_hours(quiet_time) is True
        
        # Тест в обычные часы (14:00)
        normal_time = time(14, 0)
        assert self.moderator.is_quiet_hours(normal_time) is False


class TestDialogManager:
    """Тесты менеджера диалогов"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.manager = DialogManager()
        self.manager.last_messages = {}
    
    def test_repeated_message_detection(self):
        """Тест обнаружения повторяющихся сообщений"""
        user_id = 12345
        message = "Привет! Как дела?"
        
        # Первое сообщение
        assert self.manager._is_repeated_message(user_id, message) is False
        
        # То же сообщение снова
        assert self.manager._is_repeated_message(user_id, message) is True
    
    def test_similar_message_detection(self):
        """Тест обнаружения схожих сообщений"""
        user_id = 12345
        
        # Схожие сообщения
        message1 = "Привет! Как дела?"
        message2 = "Привет! Как твои дела?"
        
        # Первое сообщение
        assert self.manager._is_repeated_message(user_id, message1) is False
        
        # Схожее сообщение
        similarity = self.manager._simple_similarity(message1, message2)
        assert similarity > 0.5  # Должны быть схожи
    
    def test_conversation_history_formatting(self):
        """Тест форматирования истории сообщений"""
        messages = [
            {"text": "Привет", "is_outgoing": False},
            {"text": "Привет! Как дела?", "is_outgoing": True},
            {"text": "Хорошо, спасибо", "is_outgoing": False}
        ]
        
        formatted = self.manager._format_conversation_history(messages)
        
        assert len(formatted) == 3
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Привет"
        assert formatted[1]["role"] == "assistant"
        assert formatted[1]["content"] == "Привет! Как дела?"


@pytest.mark.asyncio
class TestDatabaseStore:
    """Тесты хранилища данных"""
    
    async def setup_method(self):
        """Настройка перед каждым тестом"""
        self.store = DatabaseStore(":memory:")  # In-memory база для тестов
        await self.store.init_db()
    
    async def test_user_creation(self):
        """Тест создания пользователя"""
        user_info = await self.store.get_or_create_user(
            user_id=12345,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        
        assert user_info["user_id"] == 12345
        assert user_info["username"] == "test_user"
        assert user_info["first_name"] == "Test"
        assert user_info["last_name"] == "User"
    
    async def test_daily_limit_check(self):
        """Тест проверки дневного лимита"""
        user_id = 12345
        
        # Первая проверка должна пройти
        assert await self.store.check_daily_limit(user_id) is True
        
        # Увеличиваем лимит до максимума
        for _ in range(5):  # MAX_DAILY_MESSAGES_PER_USER = 5
            await self.store.increment_daily_limit(user_id)
        
        # Следующая проверка должна не пройти
        assert await self.store.check_daily_limit(user_id) is False
    
    async def test_user_pause(self):
        """Тест паузы пользователя"""
        user_id = 12345
        
        # По умолчанию пользователь не на паузе
        assert await self.store.is_user_paused(user_id) is False
        
        # Устанавливаем паузу
        await self.store.set_user_paused(user_id, True)
        assert await self.store.is_user_paused(user_id) is True
        
        # Снимаем паузу
        await self.store.set_user_paused(user_id, False)
        assert await self.store.is_user_paused(user_id) is False
    
    async def test_follow_up_creation(self):
        """Тест создания follow-up"""
        user_id = 12345
        message_template = "Привет! Как дела?"
        days_ahead = 2
        
        await self.store.create_follow_up(user_id, message_template, days_ahead)
        
        # Получаем pending follow-up
        follow_ups = await self.store.get_pending_follow_ups()
        
        # Должен быть один follow-up
        assert len(follow_ups) == 1
        assert follow_ups[0]["user_id"] == user_id
        assert follow_ups[0]["message_template"] == message_template


if __name__ == "__main__":
    pytest.main([__file__])

