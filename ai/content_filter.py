"""
Фильтрация контента
"""

import re
import logging
from typing import Tuple, List, Dict, Any
from core.exceptions import ContentFilterError

logger = logging.getLogger(__name__)

class ContentFilter:
    """Фильтр контента для сообщений"""
    
    def __init__(self, config: Dict[str, List[str]]):
        self.forbidden_keywords = config.get('forbidden_keywords', [])
        self.forbidden_adult_keywords = config.get('forbidden_adult_keywords', [])
        self.forbidden_obscene_keywords = config.get('forbidden_obscene_keywords', [])
        
        # Компилируем регулярные выражения для более быстрой работы
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Компилирует регулярные выражения"""
        # Паттерны для URL
        self.url_pattern = re.compile(r'https?://\S+')
        
        # Паттерны для спама
        self.spam_patterns = [
            re.compile(r'[A-Z]{5,}'),  # Много заглавных букв подряд
            re.compile(r'[!]{3,}'),    # Много восклицательных знаков
            re.compile(r'[?]{3,}'),    # Много вопросительных знаков
        ]
        
        # Паттерны для подозрительного контента
        self.suspicious_patterns = [
            re.compile(r'\b(?:купить|продать|заказать|скидка|акция|бесплатно)\b', re.IGNORECASE),
            re.compile(r'\b(?:деньги|доллар|рубль|евро|криптовалюта|биткоин)\b', re.IGNORECASE),
        ]
    
    def check_message(self, text: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Проверяет сообщение на соответствие правилам
        
        Returns:
            Tuple[bool, str, Dict]: (разрешено, причина, детали)
        """
        if not text or not text.strip():
            return False, "Пустое сообщение", {}
        
        text_lower = text.lower()
        details = {
            'original_length': len(text),
            'filtered_length': len(text.strip()),
            'checks_passed': 0,
            'total_checks': 5
        }
        
        # 1. Проверка запрещенных ключевых слов
        forbidden_found = self._check_forbidden_keywords(text_lower)
        if forbidden_found:
            return False, f"Запрещенная тема: {forbidden_found}", details
        
        # 2. Проверка 18+ контента
        adult_found = self._check_adult_content(text_lower)
        if adult_found:
            return False, f"Контент 18+: {adult_found}", details
        
        # 3. Проверка нецензурной лексики
        obscene_found = self._check_obscene_content(text_lower)
        if obscene_found:
            return False, f"Нецензурная лексика: {obscene_found}", details
        
        # 4. Проверка на спам
        spam_detected = self._check_spam(text)
        if spam_detected:
            return False, "Обнаружен спам", details
        
        # 5. Проверка подозрительного контента
        suspicious_detected = self._check_suspicious_content(text_lower)
        if suspicious_detected:
            return False, "Подозрительный контент", details
        
        details['checks_passed'] = details['total_checks']
        return True, "ok", details
    
    def _check_forbidden_keywords(self, text: str) -> str:
        """Проверяет запрещенные ключевые слова"""
        for keyword in self.forbidden_keywords:
            if keyword.lower() in text:
                return keyword
        return ""
    
    def _check_adult_content(self, text: str) -> str:
        """Проверяет 18+ контент"""
        for keyword in self.forbidden_adult_keywords:
            if keyword.lower() in text:
                return keyword
        return ""
    
    def _check_obscene_content(self, text: str) -> str:
        """Проверяет нецензурную лексику"""
        for keyword in self.forbidden_obscene_keywords:
            if keyword.lower() in text:
                return keyword
        return ""
    
    def _check_spam(self, text: str) -> bool:
        """Проверяет на спам"""
        # Проверяем паттерны спама
        for pattern in self.spam_patterns:
            if pattern.search(text):
                return True
        
        # Проверяем длину сообщения
        if len(text) > 1000:
            return True
        
        # Проверяем повторяющиеся символы
        if re.search(r'(.)\1{4,}', text):
            return True
        
        return False
    
    def _check_suspicious_content(self, text: str) -> bool:
        """Проверяет подозрительный контент"""
        # Проверяем подозрительные паттерны
        for pattern in self.suspicious_patterns:
            if pattern.search(text):
                return True
        
        # Проверяем URL
        if self.url_pattern.search(text):
            # Разрешаем URL только если они безопасные
            urls = self.url_pattern.findall(text)
            for url in urls:
                if not self._is_safe_url(url):
                    return True
        
        return False
    
    def _is_safe_url(self, url: str) -> bool:
        """Проверяет безопасность URL"""
        safe_domains = [
            'telegram.org', 't.me', 'github.com', 'stackoverflow.com',
            'wikipedia.org', 'youtube.com', 'google.com', 'yandex.ru'
        ]
        
        url_lower = url.lower()
        return any(domain in url_lower for domain in safe_domains)
    
    def sanitize_message(self, text: str) -> str:
        """Очищает сообщение от нежелательного контента"""
        if not text:
            return text
        
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Ограничиваем длину
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        # Убираем повторяющиеся символы
        text = re.sub(r'(.)\1{4,}', r'\1\1\1', text)
        
        return text
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Получает статистику фильтра"""
        return {
            'forbidden_keywords_count': len(self.forbidden_keywords),
            'adult_keywords_count': len(self.forbidden_adult_keywords),
            'obscene_keywords_count': len(self.forbidden_obscene_keywords),
            'total_patterns': len(self.spam_patterns) + len(self.suspicious_patterns)
        }
    
    def add_custom_keyword(self, category: str, keyword: str):
        """Добавляет пользовательское ключевое слово"""
        if category == 'forbidden':
            self.forbidden_keywords.append(keyword.lower())
        elif category == 'adult':
            self.forbidden_adult_keywords.append(keyword.lower())
        elif category == 'obscene':
            self.forbidden_obscene_keywords.append(keyword.lower())
        else:
            raise ValueError(f"Неизвестная категория: {category}")
        
        logger.info(f"Добавлено ключевое слово '{keyword}' в категорию '{category}'")
    
    def remove_custom_keyword(self, category: str, keyword: str) -> bool:
        """Удаляет пользовательское ключевое слово"""
        keyword_lower = keyword.lower()
        
        if category == 'forbidden' and keyword_lower in self.forbidden_keywords:
            self.forbidden_keywords.remove(keyword_lower)
            return True
        elif category == 'adult' and keyword_lower in self.forbidden_adult_keywords:
            self.forbidden_adult_keywords.remove(keyword_lower)
            return True
        elif category == 'obscene' and keyword_lower in self.forbidden_obscene_keywords:
            self.forbidden_obscene_keywords.remove(keyword_lower)
            return True
        
        return False
