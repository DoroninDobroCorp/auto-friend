from __future__ import annotations

from typing import List, Tuple, Optional
import time
import os

from openai import OpenAI


class LLM:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.client = None
        if api_key:
            # add a reasonable timeout to avoid hanging
            kwargs = {"api_key": api_key, "timeout": 20}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

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
            # offline fallback with simple heuristics, using history
            print("LLM: offline heuristic (no client)")
            return self._heuristic_reply(history, user_message)

        messages = [{"role": "system", "content": system_prompt}]
        for role, content in history:
            if role not in {"user", "assistant"}:
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        # allow overriding model via env
        model = os.getenv("OPENAI_MODEL", model)
        try:
            print(f"LLM cfg: model={model}, base_url={self.base_url or 'default'}")
        except Exception:
            pass

        # simple retry with backoff for transient network issues
        last_err = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                print("LLM: OpenAI API OK")
                return resp.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                wait = 0.7 * (2 ** attempt)
                print(f"LLM: API error, retrying in {wait:.1f}s... Error: {e}")
                time.sleep(wait)
        # after retries, fallback heuristically
        print(f"LLM: API error -> heuristic after retries. Error: {last_err}")
        return self._heuristic_reply(history, user_message)

    @staticmethod
    def _heuristic_reply(history: List[Tuple[str, str]], msg: str) -> str:
        """Very simple Russian heuristics to keep convo human-like offline.
        Avoid parroting; ask light follow-ups; keep it brief.
        """
        text = (msg or "").strip().lower()
        if not text:
            return "Хэй! Как ты сегодня?"

        # clamp length
        if len(text) > 400:
            text = text[:400] + "..."

        # heuristics
        if "как дела" in text or "как ты" in text:
            return "Нормально, спасибо! А у тебя как сегодня настроение?"

        if text.endswith("?"):
            # try to be helpful without echoing
            return "Хороший вопрос. Можешь чуть уточнить, что для тебя здесь важнее всего?"

        # if last assistant spoke recently, avoid repeating
        last_assistant = next((c for r, c in reversed(history) if r == "assistant"), None)
        if last_assistant and last_assistant[:50].lower() in text[:120]:
            return "Вижу. А как ты сам(а) это чувствуешь сейчас?"

        # default short empathetic follow-up
        return "Понимаю. Что для тебя сейчас самое главное в этой теме?"
