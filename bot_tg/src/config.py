"""
Конфигурация приложения с использованием Pydantic
"""
import os
import re
from typing import List, Optional
from datetime import time
from pydantic import field_validator
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # игнорируем лишние переменные окружения
    )
    
    # Telegram API
    api_id: int = 0
    api_hash: str = "test_hash"
    phone_number: str = "+10000000000"
    
    # OpenAI API
    openai_api_key: str = "test_key"
    openai_model: str = "gpt-4-turbo-preview"
    
    # Поведение бота
    enable_group_mode: bool = True
    max_daily_messages_per_user: int = 5
    quiet_hours_start: str = "23:00"
    quiet_hours_end: str = "08:00"
    group_cooldown_minutes: int = 30
    min_group_message_length: int = 20
    
    # Follow-up настройки
    follow_up_min_days: int = 1
    follow_up_max_days: int = 3
    
    # Ключевые слова для групп
    group_keywords: str = "совет,опыт,как сделать,помогите,вопрос"
    
    # Запрещённые темы
    forbidden_topics: str = "политика,nsfw,токсичность,спам,реклама"
    
    # База данных
    database_path: str = "./data/bot.db"
    
    # Логирование
    log_level: str = "INFO"
    
    @field_validator('quiet_hours_start', 'quiet_hours_end', mode='before')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Валидация и нормализация формата времени.
        Допускаем значения:
        - "8" -> "08:00"
        - "8:0"/"8:00" -> нормализуем до HH:MM
        - "HH:MM" (стандарт)
        """
        if v is None:
            return v
        if isinstance(v, str):
            s = v.strip()
            # Если только час, например "8" или "08"
            if s.isdigit():
                h = int(s)
                if 0 <= h <= 23:
                    return f"{h:02d}:00"
            # Формат H:MM или HH:M -> приводим к HH:MM при валидных значениях
            if re.fullmatch(r"\d{1,2}:\d{1,2}", s):
                h_str, m_str = s.split(':', 1)
                try:
                    h, m = int(h_str), int(m_str)
                except ValueError:
                    pass
                else:
                    if 0 <= h <= 23 and 0 <= m <= 59:
                        return f"{h:02d}:{m:02d}"
            # Пробуем стандартный разбор
            try:
                time.fromisoformat(s)
                return s
            except ValueError:
                raise ValueError(f"Неверный формат времени: {v}. Используйте формат HH:MM")
        return v
    
    @property
    def group_keywords_list(self) -> List[str]:
        """Список ключевых слов для групп"""
        return [kw.strip() for kw in self.group_keywords.split(',') if kw.strip()]
    
    @property
    def forbidden_topics_list(self) -> List[str]:
        """Список запрещённых тем"""
        return [topic.strip() for topic in self.forbidden_topics.split(',') if topic.strip()]
    
    @property
    def quiet_hours_start_time(self) -> time:
        """Время начала тихих часов"""
        return time.fromisoformat(self.quiet_hours_start)
    
    @property
    def quiet_hours_end_time(self) -> time:
        """Время окончания тихих часов"""
        return time.fromisoformat(self.quiet_hours_end)
    
    # Конфигурация выше задана через model_config


# Глобальный экземпляр настроек
settings = Settings()

