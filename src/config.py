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

    # Telegram user-mode (MTProto)
    tg_api_id: Optional[int]
    tg_api_hash: Optional[str]
    tg_session: Optional[str]

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
            # Accept both TG_* and TELEGRAM_* names
            tg_api_id=(
                int(os.getenv("TG_API_ID")) if os.getenv("TG_API_ID")
                else (int(os.getenv("TELEGRAM_API_ID")) if os.getenv("TELEGRAM_API_ID") else None)
            ),
            tg_api_hash=(
                os.getenv("TG_API_HASH") if os.getenv("TG_API_HASH")
                else os.getenv("TELEGRAM_API_HASH")
            ),
            tg_session=os.getenv("TG_SESSION"),
        )
