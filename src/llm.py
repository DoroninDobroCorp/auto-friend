from __future__ import annotations

from typing import List, Tuple, Optional

from openai import OpenAI


class LLM:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.client = None
        if api_key:
            self.client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    def generate_reply(
        self,
        system_prompt: str,
        history: List[Tuple[str, str]],  # list of (role, content) where role in {"user","assistant"}
        user_message: str,
        temperature: float = 0.6,
        model: str = "gpt-4o-mini",
        max_tokens: int = 300,
    ) -> str:
        if not self.client:
            # offline fallback: echo with a friendly twist
            return self._fallback_reply(user_message)

        messages = [{"role": "system", "content": system_prompt}]
        for role, content in history:
            if role not in {"user", "assistant"}:
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return self._fallback_reply(user_message)

    @staticmethod
    def _fallback_reply(msg: str) -> str:
        base = msg.strip()
        if not base:
            return "Маленький пинг :) Как дела?"
        if len(base) > 300:
            base = base[:300] + "..."
        return f"Слушаю тебя. {base}"
