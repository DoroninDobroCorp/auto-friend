from __future__ import annotations

import os
from ..config import Config
from telethon import TelegramClient


def main():
    cfg = Config.load()
    if not cfg.tg_api_id or not cfg.tg_api_hash:
        print("Set TG_API_ID and TG_API_HASH (or TELEGRAM_API_ID/TELEGRAM_API_HASH) in .env")
        return 1
    session = cfg.tg_session or "auto_friend_user"
    client = TelegramClient(session=session, api_id=cfg.tg_api_id, api_hash=cfg.tg_api_hash)
    try:
        print("Starting interactive login (phone + code). This runs once; session will be saved.")
        client.start()  # will prompt for phone and code
        print("Login complete. Session saved.")
        return 0
    finally:
        # Ensure we disconnect to release the session DB lock
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
