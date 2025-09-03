"""
Генератор отчётов для Telegram userbot.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from .memory.store import store

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Класс генерации ежедневных отчётов.

    Использует данные из БД через `store.get_daily_stats()` и пишет краткий
    отчёт в логи. Может быть расширен для отправки отчёта в файл/канал.
    """

    @staticmethod
    async def generate_daily_report() -> None:
        """Сгенерировать и залогировать ежедневный отчёт."""
        try:
            stats: Dict[str, Any] = await store.get_daily_stats()
            # Форматируем краткий отчёт
            report_lines = [
                "📅 Ежедневный отчёт",
                f"Дата: {stats.get('date', datetime.now().date())}",
                f"Уникальных диалогов: {stats.get('unique_dialogs', 0)}",
                f"Исходящих сообщений: {stats.get('outgoing_messages', 0)}",
                f"Follow-ups создано: {stats.get('follow_ups_created', 0)}",
                f"Follow-ups отправлено: {stats.get('follow_ups_sent', 0)}",
                f"Follow-ups просрочено: {stats.get('follow_ups_delayed', 0)}",
            ]
            report_text = "\n".join(report_lines)
            logger.info(report_text)
        except Exception as e:
            logger.error(f"Ошибка генерации ежедневного отчёта: {e}")
