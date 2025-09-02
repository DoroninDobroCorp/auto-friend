"""
Конфигурация системы
"""

import os
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def getenv_int(name: str, default: int) -> int:
    """Получает целочисленное значение из переменной окружения"""
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def getenv_bool(name: str, default: bool) -> bool:
    """Получает булево значение из переменной окружения"""
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}

def getenv_list(name: str, default: List[str]) -> List[str]:
    """Получает список значений из переменной окружения"""
    v = os.getenv(name)
    if v is None:
        return default
    return [item.strip() for item in v.split(",") if item.strip()]

@dataclass(frozen=True)
class BotConfig:
    """Конфигурация бота"""
    token: str
    name: str
    username: str
    webhook_url: Optional[str] = None

@dataclass(frozen=True)
class AIConfig:
    """Конфигурация AI"""
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 300
    # Yandex GPT настройки
    yandex_api_key: Optional[str] = None
    yandex_folder_id: Optional[str] = None
    yandex_model: str = "yandexgpt-lite"
    # Выбор провайдера AI
    ai_provider: str = "yandex"  # "openai", "yandex", "offline"

@dataclass(frozen=True)
class PersonaConfig:
    """Конфигурация личности бота"""
    name: str
    style: str
    bio: str
    language: str = "ru"

@dataclass(frozen=True)
class TimeConfig:
    """Конфигурация времени"""
    timezone: str
    quiet_hours_start: int
    quiet_hours_end: int

@dataclass(frozen=True)
class LimitsConfig:
    """Конфигурация лимитов"""
    max_daily_messages_per_user: int
    max_daily_messages_per_group: int
    min_delay_between_messages: int

@dataclass(frozen=True)
class GroupConfig:
    """Конфигурация групповых чатов"""
    enabled: bool
    min_message_length: int
    reply_keywords: List[str]
    whitelist_chat_ids: List[str]
    force_mode: bool

@dataclass(frozen=True)
class FilterConfig:
    """Конфигурация фильтров"""
    forbidden_keywords: List[str]
    forbidden_adult_keywords: List[str]
    forbidden_obscene_keywords: List[str]

@dataclass(frozen=True)
class TelegramUserConfig:
    """Конфигурация для работы от лица пользователя"""
    api_id: Optional[int]
    api_hash: Optional[str]
    session_name: str

@dataclass(frozen=True)
class Config:
    """Основная конфигурация системы"""
    
    # Основные компоненты
    bot: BotConfig
    ai: AIConfig
    persona: PersonaConfig
    time: TimeConfig
    limits: LimitsConfig
    group: GroupConfig
    filter: FilterConfig
    telegram_user: TelegramUserConfig
    
    @staticmethod
    def load() -> "Config":
        """Загружает конфигурацию из переменных окружения"""
        
        # Telegram Bot
        bot = BotConfig(
            token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            name=os.getenv("BOT_NAME", "AI Assistant"),
            username=os.getenv("BOT_USERNAME", ""),
            webhook_url=os.getenv("WEBHOOK_URL")
        )
        
        # AI Configuration
        ai = AIConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "300")),
            yandex_api_key=os.getenv("YANDEX_API_KEY"),
            yandex_folder_id=os.getenv("YANDEX_FOLDER_ID"),
            yandex_model=os.getenv("YANDEX_MODEL", "yandexgpt-lite"),
            ai_provider=os.getenv("AI_PROVIDER", "yandex")
        )
        
        # Persona
        persona = PersonaConfig(
            name=os.getenv("PERSONA_NAME", "Алексей"),
            style=os.getenv("PERSONA_STYLE", "дружелюбный и естественный"),
            bio=os.getenv("PERSONA_BIO", "Привет! Я AI-ассистент для общения."),
            language=os.getenv("PERSONA_LANGUAGE", "ru")
        )
        
        # Time settings
        time = TimeConfig(
            timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
            quiet_hours_start=getenv_int("QUIET_HOURS_START", 23),
            quiet_hours_end=getenv_int("QUIET_HOURS_END", 8)
        )
        
        # Limits
        limits = LimitsConfig(
            max_daily_messages_per_user=getenv_int("MAX_DAILY_MESSAGES_PER_USER", 5),
            max_daily_messages_per_group=getenv_int("MAX_DAILY_MESSAGES_PER_GROUP", 3),
            min_delay_between_messages=getenv_int("MIN_DELAY_BETWEEN_MESSAGES", 30)
        )
        
        # Group settings
        group = GroupConfig(
            enabled=getenv_bool("GROUP_MODE_ENABLED", True),
            min_message_length=getenv_int("GROUP_MIN_MESSAGE_LEN", 10),
            reply_keywords=getenv_list("GROUP_REPLY_KEYWORDS", [
                "что думаете", "как считаете", "кто в теме", 
                "совет", "мнение", "обсуждение", "вопрос"
            ]),
            whitelist_chat_ids=getenv_list("GROUP_WHITELIST_CHAT_IDS", []),
            force_mode=getenv_bool("GROUP_FORCE_MODE", False)
        )
        
        # Content filtering
        filter = FilterConfig(
            forbidden_keywords=getenv_list("FORBIDDEN_KEYWORDS", [
                "nsfw", "порно", "секс", "наркотики", "политика", "war", "война"
            ]),
            forbidden_adult_keywords=getenv_list("FORBIDDEN_ADULT_KEYWORDS", [
                "сиськи", "грудь", "член", "стояк", "интим", "сексуальный"
            ]),
            forbidden_obscene_keywords=getenv_list("FORBIDDEN_OBSCENE_KEYWORDS", [
                "хуй", "пизда", "ебать", "сука", "блядь", "говно"
            ])
        )
        
        # Telegram User mode
        telegram_user = TelegramUserConfig(
            api_id=int(os.getenv("TG_API_ID")) if os.getenv("TG_API_ID") else None,
            api_hash=os.getenv("TG_API_HASH"),
            session_name=os.getenv("TG_SESSION", "ai_assistant_user")
        )
        
        return Config(
            bot=bot,
            ai=ai,
            persona=persona,
            time=time,
            limits=limits,
            group=group,
            filter=filter,
            telegram_user=telegram_user
        )
    
    def validate(self) -> bool:
        """Проверяет корректность конфигурации"""
        if not self.bot.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не настроен")
        
        if self.telegram_user.api_id and not self.telegram_user.api_hash:
            raise ValueError("TG_API_HASH не настроен при наличии TG_API_ID")
        
        return True
