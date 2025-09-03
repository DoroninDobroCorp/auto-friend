"""
Модерация контента и безопасность
"""
import re
from typing import List, Tuple, Optional
import logging
try:
    from ..config import settings  # when importing as src.moderation.safety
except Exception:
    from config import settings  # when importing as moderation.safety in tests

logger = logging.getLogger(__name__)


class ContentModerator:
    """Модератор контента для проверки безопасности сообщений"""
    
    def __init__(self):
        self.forbidden_topics = settings.forbidden_topics_list
        # Простая морфологическая поддержка для русских словоформ запрещённых тем
        stems = {
            'политика': r'\bполитик\w*\b',
            'спам': r'\bспам\w*\b',
            'реклама': r'\bреклам\w*\b',
            'токсичность': r'\bтоксичн\w*\b',
            'nsfw': r'\bnsfw\b',
        }
        self.forbidden_topic_patterns = [
            stems.get(t.lower(), rf"\\b{re.escape(t.lower())}\\b")
            for t in self.forbidden_topics
        ]
        self.toxic_patterns = [
            r'\b(идиот|дебил|тупой|дурак|кретин)\b',
            r'\b(ненавижу|убью|убить|смерть)\b',
            # токсичность не включает спам/рекламу и общие темы
            r'\b(секс|порно|nsfw|18\+)\b',
            r'\b(наркотики|алкоголь|курить)\b',
        ]
        self.spam_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'\b(купить|продать|заказать|скидка|акция)\b',
            r'\b(подписывайтесь|лайкайте|репост)\b',
        ]
        
    def check_message_safety(self, text: str) -> Tuple[bool, str, Optional[str]]:
        """
        Проверить безопасность сообщения
        
        Returns:
            Tuple[bool, str, Optional[str]]: (is_safe, reason, suggested_replacement)
        """
        if not text or len(text.strip()) == 0:
            return True, "empty_message", None
            
        text_lower = text.lower()
        
        # Проверка на запрещённые темы (с учётом словоформ)
        for pattern in self.forbidden_topic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False, "forbidden_topic", self._suggest_replacement(text, "forbidden_topic")
        
        # Проверка на токсичные паттерны
        for pattern in self.toxic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False, "toxic_content", self._suggest_replacement(text, pattern)
        
        # Проверка на спам
        spam_score = 0
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                spam_score += 1
        
        if spam_score >= 2:
            return False, "spam_detected", self._suggest_replacement(text, "spam")
        
        # Проверка на длину (слишком короткие сообщения могут быть спамом)
        if len(text.strip()) < 3:
            return False, "too_short", None
        
        # Проверка на повторяющиеся символы
        if self._has_repeated_chars(text):
            return False, "repeated_chars", None
        
        return True, "safe", None
    
    def _has_repeated_chars(self, text: str, threshold: int = 5) -> bool:
        """Проверить на повторяющиеся символы"""
        # Считаем повтором только подряд идущие символы (не просто частоту в тексте)
        pattern = rf"(\S)\1{{{threshold-1},}}"
        return re.search(pattern, text) is not None
    
    def _suggest_replacement(self, original_text: str, issue: str) -> str:
        """Предложить замену для проблемного текста"""
        if "forbidden_topic" in issue:
            return "Извините, но я не могу обсуждать эту тему."
        elif "toxic_content" in issue:
            return "Давайте обсудим это более конструктивно."
        elif "spam" in issue:
            return "Извините, но это выглядит как реклама."
        else:
            return "Извините, но я не могу ответить на это сообщение."
    
    def filter_group_message(self, text: str, keywords: List[str] = None) -> bool:
        """
        Проверить, подходит ли сообщение для ответа в группе
        
        Args:
            text: Текст сообщения
            keywords: Ключевые слова для активации (если None, используются из конфига)
        
        Returns:
            bool: True если сообщение подходит для ответа
        """
        if not text:
            return False
        
        # Проверка безопасности первична
        is_safe, reason, _ = self.check_message_safety(text)
        if not is_safe:
            logger.info(f"Group message filtered: {reason}")
            return False
        
        # Проверка ключевых слов (игнорируем минимальную длину, если ключевое слово найдено)
        keywords_to_check = keywords or settings.group_keywords_list
        text_lower = text.lower()
        for keyword in keywords_to_check:
            if keyword.lower() in text_lower:
                return True
        
        # Если ключевых слов нет — применяем порог длины
        return len(text.strip()) >= settings.min_group_message_length
    
    def sanitize_message(self, text: str) -> str:
        """Очистить сообщение от потенциально опасного контента"""
        if not text:
            return ""
        
        # Удаляем ссылки
        text = re.sub(r'http[s]?://\S+', '[ссылка]', text)
        
        # Удаляем повторяющиеся символы
        text = re.sub(r'(.)\1{4,}', r'\1\1\1', text)
        
        # Ограничиваем длину
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        return text.strip()
    
    def is_quiet_hours(self, current_time=None) -> bool:
        """Проверить, сейчас ли тихие часы"""
        from datetime import datetime, time
        
        if current_time is None:
            current_time = datetime.now().time()
        
        start_time = settings.quiet_hours_start_time
        end_time = settings.quiet_hours_end_time
        
        if start_time <= end_time:
            # Обычный случай: 08:00 - 23:00
            return start_time <= current_time <= end_time
        else:
            # Ночной переход: 23:00 - 08:00
            return current_time >= start_time or current_time <= end_time


# Глобальный экземпляр модератора
moderator = ContentModerator()

