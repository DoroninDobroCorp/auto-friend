import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def getenv_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


@dataclass(frozen=True)
class Config:
    telegram_bot_token: Optional[str]
    openai_api_key: Optional[str]
    openai_base_url: Optional[str]

    timezone: str
    quiet_hours_start: int  # 0-23
    quiet_hours_end: int    # 0-23
    max_daily_messages_per_user: int

    @staticmethod
    def load() -> "Config":
        return Config(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            timezone=os.getenv("TIMEZONE", "Europe/Berlin"),
            quiet_hours_start=getenv_int("QUIET_HOURS_START", 22),
            quiet_hours_end=getenv_int("QUIET_HOURS_END", 8),
            max_daily_messages_per_user=getenv_int("MAX_DAILY_MESSAGES_PER_USER", 3),
        )
