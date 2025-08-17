from __future__ import annotations

from typing import List, Tuple

from .config import Config
from . import storage


def can_send_to_user(user: storage.User, cfg: Config) -> tuple[bool, str]:
    if user.paused:
        return False, "paused"
    if not user.consent:
        return False, "no_consent"
    if user.daily_msg_count >= cfg.max_daily_messages_per_user:
        return False, "daily_limit"
    return True, "ok"


def anti_repetition_ok(recent: List[Tuple[str, str, str]], next_text: str) -> bool:
    # avoid repeating the same assistant text recently
    next_text_norm = normalize(next_text)
    for direction, content, _ts in reversed(recent):
        if direction != 'out':
            continue
        if similarity(normalize(content), next_text_norm) > 0.9:
            return False
    return True


def similarity(a: str, b: str) -> float:
    # quick Jaccard over word sets
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union


def normalize(s: str) -> str:
    return ' '.join(s.lower().strip().split())
