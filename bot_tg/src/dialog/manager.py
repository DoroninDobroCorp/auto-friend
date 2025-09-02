"""
Менеджер диалогов для управления общением
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random
from ..config import settings
from ..memory.store import store
from ..nlp.llm_client import llm_client
from ..moderation.safety import moderator

logger = logging.getLogger(__name__)


class DialogManager:
    """Менеджер диалогов для управления общением"""
    
    def __init__(self):
        self.last_messages = {}  # Кэш последних сообщений для анти-повтора
        
    async def process_private_message(self, user_id: int, message_text: str, 
                                    user_info: Dict[str, Any]) -> Optional[str]:
        """
        Обработать личное сообщение
        
        Args:
            user_id: ID пользователя
            message_text: Текст сообщения
            user_info: Информация о пользователе
        
        Returns:
            Optional[str]: Ответ или None если не нужно отвечать
        """
        # Проверяем паузу
        if await store.is_user_paused(user_id):
            logger.info(f"Пользователь {user_id} на паузе")
            return None
        
        # Проверяем дневной лимит
        if not await store.check_daily_limit(user_id):
            logger.info(f"Достигнут дневной лимит для пользователя {user_id}")
            return "Извините, но я достиг лимита сообщений на сегодня. Попробуйте завтра! 😊"
        
        # Проверяем безопасность
        is_safe, reason, replacement = moderator.check_message_safety(message_text)
        if not is_safe:
            logger.info(f"Сообщение заблокировано: {reason}")
            return replacement
        
        # Получаем историю сообщений
        messages = await store.get_user_messages(user_id, limit=10)
        
        # Проверяем анти-повтор
        if self._is_repeated_message(user_id, message_text):
            logger.info(f"Обнаружен повтор для пользователя {user_id}")
            return "Я уже отвечал на это сообщение. Может, у тебя есть другие вопросы? 😊"
        
        # Формируем контекст для LLM
        conversation_history = self._format_conversation_history(messages)
        
        # Генерируем ответ
        response = await llm_client.generate_response(
            messages=conversation_history,
            user_info=user_info
        )
        print(response, 'response')
        # Проверяем безопасность ответа
        is_response_safe, _, _ = moderator.check_message_safety(response)
        if not is_response_safe:
            print(is_response_safe, 'is_response_safe')
            response = "Извините, у меня технические проблемы. Попробуйте позже."
        
        # Сохраняем сообщения
        await store.save_message(user_id, 0, message_text, False)  # Входящее
        await store.save_message(user_id, 0, response, True)       # Исходящее
        
        # Увеличиваем счётчик
        await store.increment_daily_limit(user_id)
        
        # Проверяем уведомление об ассистенте
        if not await store.is_assistant_notified(user_id):
            response += "\n\n💡 Иногда отвечает ассистент-бот"
            await store.set_assistant_notified(user_id)
        
        # Планируем follow-up
        await self._schedule_follow_up(user_id, user_info, message_text)
        
        return response
    
    def _format_conversation_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Форматировать историю сообщений для LLM"""
        formatted = []
        
        for msg in reversed(messages):  # Обратный порядок для хронологии
            role = "user" if not msg['is_outgoing'] else "assistant"
            formatted.append({
                "role": role,
                "content": msg['text']
            })
        
        return formatted
    
    def _is_repeated_message(self, user_id: int, message_text: str) -> bool:
        """Проверить, не повторяется ли сообщение"""
        if user_id not in self.last_messages:
            self.last_messages[user_id] = []
            return False
        
        # Проверяем схожесть с последними сообщениями
        for last_msg in self.last_messages[user_id][-3:]:  # Последние 3 сообщения
            if self._simple_similarity(message_text, last_msg) > 0.8:
                return True
        
        # Добавляем в историю
        self.last_messages[user_id].append(message_text)
        if len(self.last_messages[user_id]) > 10:
            self.last_messages[user_id] = self.last_messages[user_id][-10:]
        
        return False
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Простая проверка схожести текстов"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def _schedule_follow_up(self, user_id: int, user_info: Dict[str, Any], 
                                last_message: str):
        """Запланировать follow-up сообщение"""
        # Определяем количество дней (1-3)
        days_ahead = random.randint(
            settings.follow_up_min_days, 
            settings.follow_up_max_days
        )
        
        # Генерируем шаблон follow-up
        user_name = user_info.get('first_name', 'пользователь')
        follow_up_text = await llm_client.generate_follow_up(user_name, last_message)
        
        # Создаём follow-up
        await store.create_follow_up(user_id, follow_up_text, days_ahead)
        logger.info(f"Запланирован follow-up для пользователя {user_id} через {days_ahead} дней")
    
    async def process_follow_ups(self) -> List[Dict[str, Any]]:
        """Обработать запланированные follow-up сообщения"""
        pending_follow_ups = await store.get_pending_follow_ups()
        sent_follow_ups = []
        
        for follow_up in pending_follow_ups:
            user_id = follow_up['user_id']
            
            # Проверяем паузу
            if await store.is_user_paused(user_id):
                logger.info(f"Follow-up пропущен - пользователь {user_id} на паузе")
                continue
            
            # Проверяем тихие часы
            if moderator.is_quiet_hours():
                logger.info(f"Follow-up отложен - тихие часы")
                continue
            
            # Проверяем дневной лимит
            if not await store.check_daily_limit(user_id):
                logger.info(f"Follow-up отложен - достигнут лимит для {user_id}")
                continue
            
            # Отправляем follow-up
            sent_follow_ups.append({
                'user_id': user_id,
                'message': follow_up['message_template'],
                'follow_up_id': follow_up['id']
            })
            
            # Увеличиваем счётчик
            await store.increment_daily_limit(user_id)
        
        return sent_follow_ups
    
    async def process_group_message(self, chat_id: int, user_id: int, 
                                  message_text: str, chat_title: str = "") -> Optional[str]:
        """
        Обработать сообщение в группе
        
        Args:
            chat_id: ID чата
            user_id: ID автора сообщения
            message_text: Текст сообщения
            chat_title: Название чата
        
        Returns:
            Optional[str]: Ответ или None если не нужно отвечать
        """
        if not settings.enable_group_mode:
            return None
        
        # Проверяем фильтры группы
        if not moderator.filter_group_message(message_text):
            return None
        
        # Проверяем кулдаун
        if not await store.check_group_cooldown(chat_id, user_id):
            logger.info(f"Групповой ответ пропущен - кулдаун для чата {chat_id}")
            return None
        
        # Генерируем ответ
        response = await llm_client.generate_group_response(message_text, chat_title)
        
        # Проверяем безопасность
        is_safe, _, _ = moderator.check_message_safety(response)
        if not is_safe:
            return None
        
        # Обновляем активность
        await store.update_group_activity(chat_id, user_id)
        
        return response
    
    async def handle_command(self, user_id: int, command: str) -> str:
        """Обработать команду пользователя"""
        command = command.lower().strip()
        
        if command == '/help':
            return self._get_help_message()
        
        elif command == '/pause':
            await store.set_user_paused(user_id, True)
            return "✅ Общение приостановлено. Используйте /resume для возобновления."
        
        elif command == '/resume':
            await store.set_user_paused(user_id, False)
            return "✅ Общение возобновлено! Рад снова с тобой общаться 😊"
        
        elif command == '/forget':
            await store.clear_user_history(user_id)
            self.last_messages.pop(user_id, None)
            return "✅ История общения очищена. Начинаем с чистого листа!"
        
        elif command == '/status':
            return await self._get_status_message(user_id)
        
        else:
            return "❓ Неизвестная команда. Используйте /help для списка команд."
    
    def _get_help_message(self) -> str:
        """Получить сообщение с помощью"""
        return """
🤖 **Доступные команды:**

/pause - Приостановить общение
/resume - Возобновить общение  
/forget - Очистить историю
/status - Показать статус
/help - Это сообщение

💡 **Примечание:** Иногда отвечает ассистент-бот для более быстрого ответа.
        """.strip()
    
    async def _get_status_message(self, user_id: int) -> str:
        """Получить статус пользователя"""
        is_paused = await store.is_user_paused(user_id)
        can_send = await store.check_daily_limit(user_id)
        
        status = "⏸️ На паузе" if is_paused else "✅ Активен"
        limit_status = "✅ Можно отправлять" if can_send else "❌ Лимит исчерпан"
        
        return f"""
📊 **Статус общения:**

Состояние: {status}
Лимит сообщений: {limit_status}

Используйте команды для управления общением.
        """.strip()


# Глобальный экземпляр менеджера диалогов
dialog_manager = DialogManager()

