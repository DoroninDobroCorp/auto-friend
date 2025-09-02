"""
Конфигурация приложения с использованием Pydantic
"""
import os
from typing import List, Optional
from datetime import time
from pydantic import validator
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Telegram API
    api_id: int
    api_hash: str
    phone_number: str
    
    # OpenAI API
    openai_api_key: str
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
    
    @validator('quiet_hours_start', 'quiet_hours_end')
    def validate_time_format(cls, v):
        """Валидация формата времени"""
        try:
            time.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Неверный формат времени: {v}. Используйте формат HH:MM")
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Глобальный экземпляр настроек
settings = Settings()

