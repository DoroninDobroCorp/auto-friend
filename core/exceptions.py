"""
Пользовательские исключения системы
"""

class AIAssistantError(Exception):
    """Базовое исключение системы"""
    pass

class ConfigurationError(AIAssistantError):
    """Ошибка конфигурации"""
    pass

class DatabaseError(AIAssistantError):
    """Ошибка базы данных"""
    pass

class TelegramError(AIAssistantError):
    """Ошибка Telegram API"""
    pass

class AIError(AIAssistantError):
    """Ошибка AI сервиса"""
    pass

class ValidationError(AIAssistantError):
    """Ошибка валидации"""
    pass

class RateLimitError(AIAssistantError):
    """Превышен лимит запросов"""
    pass

class ContentFilterError(AIAssistantError):
    """Контент заблокирован фильтром"""
    pass
