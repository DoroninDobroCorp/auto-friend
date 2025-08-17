from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .llm import LLM
from . import storage


SYSTEM_PROMPT = (
    "Ты дружелюбный, уважительный AI-напарник для непринуждённого общения. "
    "Цели: поддерживать лёгкий диалог, проявлять эмпатию, не навязываться, не продавать, не просить личные данные. "
    "Отвечай кратко и по делу, как человек. Избегай частых сообщений без явного повода. "
    "Не повторяй дословно сообщение собеседника; формулируй свой ответ своими словами. "
    "Если собеседник задаёт общий вопрос вроде 'как дела', дай естественный человеческий ответ и мягкий встречный вопрос. "
    "Если пользователь долго не отвечает, мягко интересуйся позже (в отдельные дни), но не чаще 1 раза в 1-3 дня. "
)


@dataclass
class Reply:
    text: str


class ConversationEngine:
    def __init__(self, llm: LLM):
        self.llm = llm

    def intro_message(self, username: str | None) -> str:
        name = f", {username}" if username else ""
        return (
            f"Привет{name}! Я небольшой ИИ-бот для дружеского общения. "
            f"Поговорим? Если ок — просто напиши что-нибудь. Команды: /pause, /resume, /forget"
        )

    def consent_prompt(self) -> str:
        return (
            "Хочу убедиться, что тебе комфортно. Я ИИ-бот, могу изредка писать, чтобы поддержать разговор. "
            "Если хочешь — скажи, и продолжим. Если нет — можно /pause."
        )

    def generate(self, history: List[Tuple[str, str]], user_message: str) -> Reply:
        text = self.llm.generate_reply(
            system_prompt=SYSTEM_PROMPT,
            history=history,
            user_message=user_message,
        )
        return Reply(text=text)

    def gentle_followup(self) -> str:
        candidates = [
            "Небольшой пинг. Как у тебя дела сегодня?",
            "Привет! Надеюсь, у тебя всё хорошо. Был рад продолжить разговор, если будет настроение.",
            "Хэй, просто хотел узнать как ты. Чем занимался(ась) в последнее время?",
        ]
        # choose deterministically by length to avoid random in unit tests
        return sorted(candidates, key=len)[0]
