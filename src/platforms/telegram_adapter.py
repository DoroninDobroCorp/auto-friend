from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional, List, Tuple

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from ..config import Config
from ..cadence import Cadence
from ..conversation import ConversationEngine
from .. import storage
from .. import policies


class TelegramAdapter:
    PLATFORM = "telegram"

    def __init__(self, cfg: Config, cadence: Cadence, engine: ConversationEngine):
        self.cfg = cfg
        self.cadence = cadence
        self.engine = engine
        self.app = (
            ApplicationBuilder()
            .token(cfg.telegram_bot_token)
            .build()
        )
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.on_start))
        self.app.add_handler(CommandHandler("pause", self.on_pause))
        self.app.add_handler(CommandHandler("resume", self.on_resume))
        self.app.add_handler(CommandHandler("forget", self.on_forget))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))
        # background follow-up checker every 5 minutes
        self.app.job_queue.run_repeating(self._check_followups_job, interval=300, first=10)
        # reset counts hourly; function will no-op unless date changed
        self.app.job_queue.run_repeating(self._reset_daily_counts_job, interval=3600, first=60)

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.effective_chat:
            return
        tg_user = update.effective_user
        chat = update.effective_chat
        user = storage.upsert_user(self.PLATFORM, str(tg_user.id), tg_user.username)
        intro = self.engine.intro_message(tg_user.first_name or tg_user.username)
        storage.record_message(user.id, 'out', intro)
        await context.bot.send_message(chat_id=chat.id, text=intro)
        consent = self.engine.consent_prompt()
        storage.record_message(user.id, 'out', consent)
        await context.bot.send_message(chat_id=chat.id, text=consent)

    async def on_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        u = update.effective_user
        c = update.effective_chat
        if not u or not c:
            return
        user = storage.upsert_user(self.PLATFORM, str(u.id), u.username)
        storage.set_paused(user.id, True)
        text = "Ок, поставил на паузу. Можешь написать /resume, когда захочешь продолжить."
        storage.record_message(user.id, 'out', text)
        await context.bot.send_message(chat_id=c.id, text=text)

    async def on_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        u = update.effective_user
        c = update.effective_chat
        if not u or not c:
            return
        user = storage.upsert_user(self.PLATFORM, str(u.id), u.username)
        storage.set_paused(user.id, False)
        storage.set_consent(user.id, True)
        text = "Продолжаем. Рад вернуться к чату :)"
        storage.record_message(user.id, 'out', text)
        await context.bot.send_message(chat_id=c.id, text=text)

    async def on_forget(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        u = update.effective_user
        c = update.effective_chat
        if not u or not c:
            return
        user = storage.get_user_by_platform_id(self.PLATFORM, str(u.id))
        if user:
            storage.delete_user(user.id)
        await context.bot.send_message(chat_id=c.id, text="Готово. Я забыл нашу историю. Можем начать заново, если захочешь.")

    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user or not update.effective_chat:
            return
        text = update.message.text or ""
        tg_user = update.effective_user
        chat = update.effective_chat
        user = storage.upsert_user(self.PLATFORM, str(tg_user.id), tg_user.username)

        # record inbound
        storage.record_message(user.id, 'in', text)

        # set consent on first message after intro
        if not user.consent:
            storage.set_consent(user.id, True)

        # prepare history
        raw = storage.get_recent_messages(user.id, limit=20)
        history: List[Tuple[str, str]] = []
        for direction, content, _ts in raw:
            role = 'user' if direction == 'in' else 'assistant'
            history.append((role, content))

        # generate reply
        reply = self.engine.generate(history=history, user_message=text)

        ok, reason = policies.can_send_to_user(storage.get_user_by_id(user.id), self.cfg)  # type: ignore
        if not ok:
            # do not send if over limits or paused
            return

        recent = raw
        if not policies.anti_repetition_ok(recent, reply.text):
            # avoid repetition
            return

        storage.record_message(user.id, 'out', reply.text)
        await context.bot.send_message(chat_id=chat.id, text=reply.text, parse_mode=ParseMode.HTML)

        # schedule a gentle follow-up in 1-3 days
        due = self.cadence.schedule_followup_in_days(1, 3)
        storage.schedule_followup(user.id, due.isoformat(), reason="gentle_followup")

    async def _check_followups_job(self, context: ContextTypes.DEFAULT_TYPE):
        now_iso = datetime.utcnow().isoformat()
        due = storage.due_followups(now_iso)
        for f in due:
            user = storage.get_user_by_id(f["user_id"])  # type: ignore
            if not user:
                storage.delete_followup(f["id"])  # type: ignore
                continue
            # check policies
            ok, _why = policies.can_send_to_user(user, self.cfg)
            if not ok:
                storage.delete_followup(f["id"])  # avoid pile-up
                continue
            # build follow-up text
            text = self.engine.gentle_followup()
            # anti-repetition
            recent = storage.get_recent_messages(user.id, 20)
            if not policies.anti_repetition_ok(recent, text):
                storage.delete_followup(f["id"])  # skip
                continue

            # send via Telegram
            try:
                chat_id = int(user.platform_user_id)
                await context.bot.send_message(chat_id=chat_id, text=text)
                storage.record_message(user.id, 'out', text)
            except Exception:
                pass
            finally:
                storage.delete_followup(f["id"])  # remove processed

            # schedule next follow-up in 1–3 days if desired
            next_due = self.cadence.schedule_followup_in_days(1, 3)
            storage.schedule_followup(user.id, next_due.isoformat(), reason="gentle_followup")

    async def _reset_daily_counts_job(self, context: ContextTypes.DEFAULT_TYPE):
        storage.reset_daily_counts_if_needed()

    def run(self):
        self.app.run_polling()
