"""
Управление политиками и правилами системы
"""

import time
import logging
from typing import Tuple, Dict, Any, List
from dataclasses import dataclass
from core.exceptions import RateLimitError, ValidationError

logger = logging.getLogger(__name__)

@dataclass
class UserLimits:
    """Лимиты для пользователя"""
    max_daily_messages: int
    min_delay_between_messages: int
    max_message_length: int
    max_consecutive_messages: int

@dataclass
class GroupLimits:
    """Лимиты для групповых чатов"""
    max_daily_messages_per_chat: int
    min_message_length: int
    max_participation_rate: float

class PolicyManager:
    """Менеджер политик и правил системы"""
    
    def __init__(self, user_limits: UserLimits, group_limits: GroupLimits):
        self.user_limits = user_limits
        self.group_limits = group_limits
        
        # Кэш для отслеживания активности пользователей
        self.user_activity_cache = {}
        self.group_activity_cache = {}
    
    def can_send_to_user(self, user_id: str, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, можно ли отправлять сообщение пользователю"""
        try:
            # 1. Проверка паузы
            if user_data.get('paused', False):
                return False, "Пользователь поставил общение на паузу"
            
            # 2. Проверка согласия
            if not user_data.get('consent', False):
                return False, "Требуется согласие пользователя"
            
            # 3. Проверка дневного лимита
            daily_count = user_data.get('daily_msg_count', 0)
            if daily_count >= self.user_limits.max_daily_messages:
                return False, f"Достигнут дневной лимит ({self.user_limits.max_daily_messages} сообщений)"
            
            # 4. Проверка анти-спама
            if not self._check_anti_spam(user_id):
                return False, "Слишком частые сообщения"
            
            return True, "ok"
            
        except Exception as e:
            logger.error(f"Ошибка проверки политик для пользователя {user_id}: {e}")
            return False, f"Ошибка проверки: {e}"
    
    def can_send_to_group(self, chat_id: str, chat_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, можно ли отправлять сообщение в группу"""
        try:
            # 1. Проверка дневного лимита для группы
            daily_count = chat_data.get('daily_msg_count', 0)
            if daily_count >= self.group_limits.max_daily_messages_per_chat:
                return False, f"Достигнут дневной лимит для группы ({self.group_limits.max_daily_messages_per_chat} сообщений)"
            
            # 2. Проверка длины сообщения
            last_message_length = chat_data.get('last_message_length', 0)
            if last_message_length < self.group_limits.min_message_length:
                return False, f"Сообщение слишком короткое (минимум {self.group_limits.min_message_length} символов)"
            
            # 3. Проверка частоты участия
            if not self._check_group_participation_rate(chat_id):
                return False, "Слишком частое участие в группе"
            
            return True, "ok"
            
        except Exception as e:
            logger.error(f"Ошибка проверки политик для группы {chat_id}: {e}")
            return False, f"Ошибка проверки: {e}"
    
    def should_participate_in_group(self, message: str, keywords: List[str]) -> bool:
        """Определяет, стоит ли участвовать в групповом обсуждении"""
        if not message or not message.strip():
            return False
        
        message_lower = message.lower()
        
        # 1. Проверка ключевых слов
        for keyword in keywords:
            if keyword.lower() in message_lower:
                return True
        
        # 2. Проверка вопроса
        if message.strip().endswith('?'):
            return True
        
        # 3. Проверка призывов к обсуждению
        discussion_triggers = [
            'что думаете', 'как считаете', 'кто в теме', 'обсуждение',
            'мнение', 'совет', 'помогите', 'подскажите'
        ]
        
        for trigger in discussion_triggers:
            if trigger in message_lower:
                return True
        
        # 4. Случайное участие (небольшая вероятность)
        import random
        if random.random() < 0.05:  # 5% вероятность
            return True
        
        return False
    
    def validate_message_content(self, message: str) -> Tuple[bool, str]:
        """Валидирует содержимое сообщения"""
        if not message or not message.strip():
            return False, "Пустое сообщение"
        
        # Проверка длины
        if len(message) > self.user_limits.max_message_length:
            return False, f"Сообщение слишком длинное (максимум {self.user_limits.max_message_length} символов)"
        
        # Проверка на повторяющиеся символы
        if self._has_repetitive_characters(message):
            return False, "Обнаружены повторяющиеся символы"
        
        # Проверка на капс
        if self._is_all_caps(message):
            return False, "Не используйте заглавные буквы для всего текста"
        
        return True, "ok"
    
    def _check_anti_spam(self, user_id: str) -> bool:
        """Проверяет анти-спам правила"""
        current_time = time.time()
        
        if user_id not in self.user_activity_cache:
            self.user_activity_cache[user_id] = []
        
        # Убираем старые записи (старше 1 часа)
        self.user_activity_cache[user_id] = [
            timestamp for timestamp in self.user_activity_cache[user_id]
            if current_time - timestamp < 3600
        ]
        
        # Проверяем количество сообщений за последний час
        if len(self.user_activity_cache[user_id]) >= self.user_limits.max_consecutive_messages:
            return False
        
        # Добавляем текущее время
        self.user_activity_cache[user_id].append(current_time)
        
        return True
    
    def _check_group_participation_rate(self, chat_id: str) -> bool:
        """Проверяет частоту участия в группе"""
        current_time = time.time()
        
        if chat_id not in self.group_activity_cache:
            self.group_activity_cache[chat_id] = []
        
        # Убираем старые записи (старше 24 часов)
        self.group_activity_cache[chat_id] = [
            timestamp for timestamp in self.group_activity_cache[chat_id]
            if current_time - timestamp < 86400
        ]
        
        # Проверяем частоту участия
        messages_count = len(self.group_activity_cache[chat_id])
        hours_passed = (current_time - min(self.group_activity_cache[chat_id])) / 3600 if self.group_activity_cache[chat_id] else 1
        
        participation_rate = messages_count / hours_passed
        
        if participation_rate > self.group_limits.max_participation_rate:
            return False
        
        # Добавляем текущее время
        self.group_activity_cache[chat_id].append(current_time)
        
        return True
    
    def _has_repetitive_characters(self, message: str) -> bool:
        """Проверяет наличие повторяющихся символов"""
        import re
        return bool(re.search(r'(.)\1{4,}', message))
    
    def _is_all_caps(self, message: str) -> bool:
        """Проверяет, написан ли весь текст заглавными буквами"""
        if not message.strip():
            return False
        
        # Игнорируем короткие сообщения и сообщения только с символами
        if len(message.strip()) < 5:
            return False
        
        # Проверяем, что есть буквы и они все заглавные
        letters = [char for char in message if char.isalpha()]
        if not letters:
            return False
        
        return all(char.isupper() for char in letters)
    
    def get_user_limits_info(self, user_id: str) -> Dict[str, Any]:
        """Получает информацию о лимитах пользователя"""
        current_time = time.time()
        
        if user_id in self.user_activity_cache:
            recent_activity = [
                timestamp for timestamp in self.user_activity_cache[user_id]
                if current_time - timestamp < 3600
            ]
            messages_last_hour = len(recent_activity)
        else:
            messages_last_hour = 0
        
        return {
            'max_daily_messages': self.user_limits.max_daily_messages,
            'min_delay_between_messages': self.user_limits.min_delay_between_messages,
            'max_message_length': self.user_limits.max_message_length,
            'max_consecutive_messages': self.user_limits.max_consecutive_messages,
            'messages_last_hour': messages_last_hour,
            'can_send_more': messages_last_hour < self.user_limits.max_consecutive_messages
        }
    
    def get_group_limits_info(self, chat_id: str) -> Dict[str, Any]:
        """Получает информацию о лимитах группы"""
        current_time = time.time()
        
        if chat_id in self.group_activity_cache:
            recent_activity = [
                timestamp for timestamp in self.group_activity_cache[chat_id]
                if current_time - timestamp < 86400
            ]
            messages_last_24h = len(recent_activity)
        else:
            messages_last_24h = 0
        
        return {
            'max_daily_messages_per_chat': self.group_limits.max_daily_messages_per_chat,
            'min_message_length': self.group_limits.min_message_length,
            'max_participation_rate': self.group_limits.max_participation_rate,
            'messages_last_24h': messages_last_24h,
            'can_participate': messages_last_24h < self.group_limits.max_daily_messages_per_chat
        }
    
    def reset_daily_limits(self):
        """Сбрасывает дневные лимиты"""
        current_time = time.time()
        
        # Очищаем кэш активности (старше 24 часов)
        for user_id in list(self.user_activity_cache.keys()):
            self.user_activity_cache[user_id] = [
                timestamp for timestamp in self.user_activity_cache[user_id]
                if current_time - timestamp < 86400
            ]
        
        for chat_id in list(self.group_activity_cache.keys()):
            self.group_activity_cache[chat_id] = [
                timestamp for timestamp in self.group_activity_cache[chat_id]
                if current_time - timestamp < 86400
            ]
        
        logger.info("Дневные лимиты сброшены")
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """Получает статистику политик"""
        return {
            'user_limits': {
                'max_daily_messages': self.user_limits.max_daily_messages,
                'min_delay_between_messages': self.user_limits.min_delay_between_messages,
                'max_message_length': self.user_limits.max_message_length,
                'max_consecutive_messages': self.user_limits.max_consecutive_messages
            },
            'group_limits': {
                'max_daily_messages_per_chat': self.group_limits.max_daily_messages_per_chat,
                'min_message_length': self.group_limits.min_message_length,
                'max_participation_rate': self.group_limits.max_participation_rate
            },
            'active_users': len(self.user_activity_cache),
            'active_groups': len(self.group_activity_cache)
        }
