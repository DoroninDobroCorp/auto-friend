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
from .platforms.telegram_user_adapter import TelegramUserAdapter


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

    # Prefer user-mode (MTProto via Telethon) if credentials are present
    if cfg.tg_api_id and cfg.tg_api_hash:
        print("Starting Telegram in USER mode (Telethon)...")
        tg_user = TelegramUserAdapter(cfg, cadence, engine)
        tg_user.run()
    else:
        # Fallback: Bot mode
        if not cfg.telegram_bot_token:
            print("Neither TG_API_ID/TG_API_HASH nor TELEGRAM_BOT_TOKEN is set. Please fill .env.")
            return 1
        print("Starting Telegram in BOT mode...")
        tg = TelegramAdapter(cfg, cadence, engine)
        tg.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
        raise
