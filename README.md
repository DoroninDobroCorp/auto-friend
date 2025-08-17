# Auto Friend (Non-intrusive AI social companion)

Goal: experiment with making new online friends through natural, non-spammy, human-like conversation. Absolutely no selling, no mass outreach, and strict respect for platform rules and user consent.

This project ships with:
- Core engine (scheduler, storage, LLM wrapper, policies)
- Telegram adapter (fully working)
- Discord/Reddit adapters (stubs)
- Guardrails: consent, quiet hours, rate limits, anti-repetition

## Quick start (Telegram)
1. Install Python 3.10+
2. Create and fill .env (copy from .env.example):
   - TELEGRAM_BOT_TOKEN=... (from @BotFather)
   - OPENAI_API_KEY=... (optional; if omitted, a simple offline echo LLM is used)
3. Install deps:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
4. Run:
```
python -m src.main
```
5. Message your bot in Telegram to start the conversation.

## Быстрый запуск (на русском, Telegram)
1. Установите Python 3.10+ (проверьте `python --version`).
2. Создайте бота у @BotFather в Telegram:
   - Команда `/newbot` → задайте имя и username.
   - Скопируйте `TOKEN` (будет вида `123456:ABC...`).
3. Создайте файл `.env` из шаблона и вставьте токен:
   ```bash
   cp .env.example .env
   # Откройте .env и заполните TELEGRAM_BOT_TOKEN=...
   # (Опционально) Добавьте OPENAI_API_KEY=... если хотите ответы от LLM
   ```
4. Установите зависимости в виртуальной среде:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. Запустите бота:
   ```bash
   python -m src.main
   ```
6. Откройте ваш бот в Telegram и нажмите Start/напишите любое сообщение.

Команды в чате:
- `/pause` — поставить на паузу сообщения
- `/resume` — продолжить и считать согласие дано
- `/forget` — удалить историю (забыть диалог)

Настройки (редактируются в `.env`):
- `TIMEZONE` (например, Europe/Berlin)
- `QUIET_HOURS_START`, `QUIET_HOURS_END` — тихие часы (0–23)
- `MAX_DAILY_MESSAGES_PER_USER` — дневной лимит исходящих сообщений

Типичные проблемы:
- Нет ответов от бота: убедитесь, что процесс запущен без ошибок и вы пишете именно вашему боту, созданному у @BotFather.
- Ошибка токена: проверьте `TELEGRAM_BOT_TOKEN` в `.env`.
- Нет ответов ИИ: задайте `OPENAI_API_KEY`. Без него включён оффлайн‑фолбек c простыми ответами.

## Safety and principles
- No spam. Only respond to users who initiate contact, or who clearly consent in a group context by addressing the bot.
- Transparency. Bot will introduce itself as an AI helper and ask for consent to continue casual chats.
- Quiet hours. Default 22:00–08:00 (configurable).
- Pacing. Max 3 messages/day per user by default. Randomized cadence for follow-ups (1–3 days) if user opted in.
- Opt-out. `/pause` to stop follow-ups, `/resume` to allow, `/forget` to delete stored conversation history.
- Compliance. You are responsible for following each platform’s Terms of Service.

## Configuration
See `src/config.py` and `.env.example` for all options. Key ones:
- TELEGRAM_BOT_TOKEN
- OPENAI_API_KEY (optional)
- OPENAI_BASE_URL (optional, for OpenAI-compatible servers)
- QUIET_HOURS_START, QUIET_HOURS_END (24h integers)
- MAX_DAILY_MESSAGES_PER_USER
- TIMEZONE (e.g., Europe/Berlin)

## Structure
- `src/main.py` – entry point; wires adapters
- `src/config.py` – settings via env
- `src/storage.py` – SQLite persistence
- `src/llm.py` – OpenAI-compatible wrapper + offline echo
- `src/cadence.py` – schedules next-contact time respecting quiet hours
- `src/policies.py` – consent checks, rate limits, anti-repetition
- `src/conversation.py` – simple state machine and persona
- `src/platforms/telegram_adapter.py` – working bot
- `src/platforms/discord_adapter.py` – stub
- `src/platforms/reddit_adapter.py` – stub

## Notes on platforms
- Telegram: bot cannot DM users unless they initiate the chat first. This is perfect for non-spam: only converse with consent.
- Discord: bot must share a server and have required intents. DMing random users is not allowed.
- Reddit: messaging and commenting are heavily moderated; any automated activity must be slow, human-like, and compliant.

## Roadmap
- Enrich memory with embeddings
- Add content discovery plugins for public comments (strictly paced)
- Multi-LLM support

## Disclaimer
Use responsibly and ethically. This is an experiment for relationship-building conversation only. No outreach at scale, no scraping, no selling.
