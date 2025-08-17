from __future__ import annotations

from telethon import TelegramClient
from ..config import Config


def main():
    cfg = Config.load()
    if not cfg.tg_api_id or not cfg.tg_api_hash:
        print("Missing TG_API_ID/TG_API_HASH")
        return 1
    session = cfg.tg_session or "auto_friend_user"
    client = TelegramClient(session=session, api_id=cfg.tg_api_id, api_hash=cfg.tg_api_hash)
    async def run():
        try:
            await client.connect()
            if not await client.is_user_authorized():
                print("Not authorized")
                return 2
            me = await client.get_me()
            print(f"Authorized as: {getattr(me, 'first_name', '')} {getattr(me, 'last_name', '')} (@{getattr(me, 'username', '')})")
            return 0
        finally:
            await client.disconnect()
    return client.loop.run_until_complete(run())


if __name__ == "__main__":
    raise SystemExit(main())
