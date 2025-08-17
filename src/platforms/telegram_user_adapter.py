from __future__ import annotations

from typing import List, Tuple
from datetime import datetime
import time

from telethon import TelegramClient, events

from ..config import Config
from ..cadence import Cadence
from ..conversation import ConversationEngine
from .. import storage
from .. import policies


class TelegramUserAdapter:
    PLATFORM = "telegram_user"

    def __init__(self, cfg: Config, cadence: Cadence, engine: ConversationEngine):
        if cfg.tg_api_id is None or cfg.tg_api_hash is None:
            raise ValueError("TG_API_ID/TG_API_HASH are required for user mode")
        session = cfg.tg_session or "auto_friend_user"
        self.client = TelegramClient(session=session, api_id=cfg.tg_api_id, api_hash=cfg.tg_api_hash)
        self.cfg = cfg
        self.cadence = cadence
        self.engine = engine

    def _ensure_user(self, peer) -> storage.User:
        uid = str(peer.id)
        username = getattr(peer, 'username', None)
        return storage.upsert_user(self.PLATFORM, uid, username)

    def _register_handlers(self):
        @self.client.on(events.NewMessage(incoming=True))
        async def handler(event: events.NewMessage.Event):
            try:
                # private chats only (avoid auto posting in groups)
                if not event.is_private:
                    return
                sender = await event.get_sender()
                if sender is None:
                    return
                user = self._ensure_user(sender)
                print(f"[TG] inbound from {user.username or user.platform_user_id}")

                text = (event.raw_text or "").strip()
                storage.record_message(user.id, 'in', text)

                # implicit consent after first inbound message
                if not user.consent:
                    storage.set_consent(user.id, True)

                # commands
                if text.startswith("/pause"):
                    storage.set_paused(user.id, True)
                    out = "Ок, поставил на паузу. Напиши /resume, когда захочешь продолжить."
                    storage.record_message(user.id, 'out', out)
                    await event.reply(out)
                    return
                if text.startswith("/resume"):
                    storage.set_paused(user.id, False)
                    storage.set_consent(user.id, True)
                    out = "Продолжаем. Рад вернуться к чату :)"
                    storage.record_message(user.id, 'out', out)
                    await event.reply(out)
                    return
                if text.startswith("/forget"):
                    storage.delete_user(user.id)
                    await event.reply("Готово. Я забыл нашу историю. Можем начать заново, если захочешь.")
                    return

                # build history for LLM
                raw = storage.get_recent_messages(user.id, limit=20)
                history: List[Tuple[str, str]] = []
                for direction, content, _ts in raw:
                    role = 'user' if direction == 'in' else 'assistant'
                    history.append((role, content))

                reply = self.engine.generate(history=history, user_message=text).text
                print(f"[TG] generated reply len={len(reply)}")

                ok, why = policies.can_send_to_user(storage.get_user_by_id(user.id), self.cfg)  # type: ignore
                if not ok:
                    print(f"[TG] policy blocked send: {why}")
                    return
                if not policies.anti_repetition_ok(raw, reply):
                    print("[TG] anti_repetition blocked send")
                    return

                # Send as a new standalone message (not a threaded reply)
                try:
                    # send to the current chat to avoid peer resolution issues
                    await self.client.send_message(event.chat_id, reply)
                    storage.record_message(user.id, 'out', reply)
                    print("[TG] sent reply")
                except Exception as e:
                    print(f"[TG] send_message failed: {e}")
                    return

                # schedule gentle follow-up
                due = self.cadence.schedule_followup_in_days(1, 3)
                storage.schedule_followup(user.id, due.isoformat(), reason="gentle_followup")
            except Exception as e:
                print(f"[TG] handler error: {e}")

        @self.client.on(events.NewMessage(outgoing=False))
        async def followups_tick(event: events.NewMessage.Event):
            # cheap tick: periodically check due followups upon any new message in the account
            now_iso = datetime.utcnow().isoformat()
            due = storage.due_followups(now_iso)
            for f in due:
                user = storage.get_user_by_id(f["user_id"])  # type: ignore
                if not user:
                    storage.delete_followup(f["id"])  # type: ignore
                    continue
                ok, _why = policies.can_send_to_user(user, self.cfg)
                if not ok:
                    storage.delete_followup(f["id"])  # avoid pile-up
                    continue
                text = self.engine.gentle_followup()
                recent = storage.get_recent_messages(user.id, 20)
                if not policies.anti_repetition_ok(recent, text):
                    storage.delete_followup(f["id"])  # skip
                    continue
                try:
                    await self.client.send_message(int(user.platform_user_id), text)
                    storage.record_message(user.id, 'out', text)
                except Exception:
                    pass
                finally:
                    storage.delete_followup(f["id"])  # remove processed

                next_due = self.cadence.schedule_followup_in_days(1, 3)
                storage.schedule_followup(user.id, next_due.isoformat(), reason="gentle_followup")

    def run(self):
        # Подключаемся без интерактива через connect(); при валидной сессии не требуется ввод кода.
        # Иногда Telethon session (SQLite) может быть временно залочен ("database is locked").
        # Делаем несколько повторов с бэкоффом.
        connected = False
        for attempt in range(10):
            try:
                self.client.loop.run_until_complete(self.client.connect())
                connected = True
                break
            except Exception as e:
                msg = str(e).lower()
                if "database is locked" in msg:
                    print(f"Telethon session DB locked; retrying in 1s (attempt {attempt+1}/10)...")
                    time.sleep(1)
                    continue
                print(f"Failed to connect Telethon client: {e}")
                return
        if not connected:
            print("Failed to connect Telethon client after retries (session DB locked).")
            return

        # финальная проверка на авторизацию
        try:
            authorized = self.client.loop.run_until_complete(self.client.is_user_authorized())
        except Exception:
            authorized = False
        if not authorized:
            print("Not authorized for Telegram user-mode. Please run: .venv/bin/python -m src.tools.tg_login")
            return
        # делаем лёгкий пинг к API, чтобы убедиться, что соединение живо
        verified = False
        for attempt in range(10):
            try:
                self.client.loop.run_until_complete(self.client.get_me())
                verified = True
                break
            except Exception as e:
                msg = str(e).lower()
                if "database is locked" in msg:
                    print(f"Connected but get_me() hit DB lock; retrying in 1s (attempt {attempt+1}/10)...")
                    time.sleep(1)
                    continue
                print(f"Connected but failed to verify with get_me(): {e}")
                return
        if not verified:
            print("Failed to verify with get_me() after retries (session DB locked).")
            return
        # сброс дневных лимитов при запуске
        try:
            storage.reset_daily_counts_if_needed()
            print(f"[TG] max_daily_messages_per_user={self.cfg.max_daily_messages_per_user}")
        except Exception as e:
            print(f"[TG] failed to reset daily counts: {e}")
        self._register_handlers()
        # Теперь клиент подключён и авторизован; запускаем цикл до отключения
        try:
            self.client.run_until_disconnected()
        finally:
            try:
                self.client.disconnect()
            except Exception:
                pass
