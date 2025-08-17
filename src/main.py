from __future__ import annotations

import asyncio
import os
import sys

from .config import Config
from . import storage
from .cadence import Cadence
from .llm import LLM
from .conversation import ConversationEngine
from .platforms.telegram_adapter import TelegramAdapter


def main():
    cfg = Config.load()
    storage.init_db()

    cadence = Cadence(
        quiet_start=cfg.quiet_hours_start,
        quiet_end=cfg.quiet_hours_end,
        timezone=cfg.timezone,
    )
    llm = LLM(api_key=cfg.openai_api_key, base_url=cfg.openai_base_url)
    engine = ConversationEngine(llm)

    # At least Telegram adapter if token present
    if not cfg.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not set. Please fill .env to run Telegram bot.")
        return 1

    tg = TelegramAdapter(cfg, cadence, engine)
    tg.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
        raise
