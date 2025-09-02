"""
LLM клиент для генерации ответов
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from ..config import settings
import httpx


logger = logging.getLogger(__name__)


class LLMClient:
    """Клиент для работы с OpenAI API"""
    
    def __init__(self):
            PROXY_URL = "socks5://127.0.0.1:800"  # ваш рабочий прокси
            
            # Создаём асинхронный http клиент для OpenAI
            try:
                # для новых версий httpx
                transport = httpx.AsyncHTTPTransport(proxy=httpx.Proxy(PROXY_URL))
                async_client = httpx.AsyncClient(transport=transport, trust_env=False)
            except Exception:
                # для старых версий httpx
                async_client = httpx.AsyncClient(proxies={"all://": PROXY_URL}, trust_env=False)
            
            # Инициализация AsyncOpenAI с кастомным клиентом
            self.client = openai.AsyncOpenAI(
                api_key=settings.openai_api_key,
                http_client=async_client
            )
            self.model = settings.openai_model
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, 
                              messages: List[Dict[str, str]], 
                              context: str = "",
                              user_info: Dict[str, Any] = None) -> str:
        """
        Сгенерировать ответ на основе истории сообщений
        
        Args:
            messages: История сообщений в формате [{"role": "user", "content": "..."}]
            context: Дополнительный контекст
            user_info: Информация о пользователе
        
        Returns:
            str: Сгенерированный ответ
        """
        try:
            # Формируем системный промпт
            system_prompt = self._build_system_prompt(context, user_info)
            
            # Добавляем системное сообщение в начало
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=500,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return "Извините, у меня технические проблемы. Попробуйте позже."
    
    def _build_system_prompt(self, context: str = "", user_info: Dict[str, Any] = None) -> str:
        """Построить системный промпт"""
        base_prompt = """
Ты - дружелюбный и полезный ассистент инфлюенсера. Твоя задача - поддерживать естественное, ненавязчивое общение.

Правила поведения:
1. Будь дружелюбным, но не навязчивым
2. Отвечай по существу, но не слишком формально
3. Используй эмодзи умеренно
4. Не давай медицинских, юридических или финансовых советов
5. Избегай политических тем
6. Не спамь и не рекламируй
7. Если не знаешь ответа, честно скажи об этом

Стиль общения:
- Используй "ты" (неформальное обращение)
- Будь позитивным и поддерживающим
- Задавай уточняющие вопросы при необходимости
- Показывай эмпатию и понимание
"""
        
        if context:
            base_prompt += f"\nКонтекст: {context}"
        
        if user_info:
            name = user_info.get('first_name', '')
            if name:
                base_prompt += f"\nПользователь: {name}"
        
        return base_prompt
    
    async def generate_follow_up(self, user_name: str, last_topic: str = "") -> str:
        """
        Сгенерировать follow-up сообщение
        
        Args:
            user_name: Имя пользователя
            last_topic: Последняя тема разговора
        
        Returns:
            str: Текст follow-up сообщения
        """
        templates = [
            f"Привет, {user_name}! 👋 Как дела?",
            f"Эй, {user_name}! Надеюсь, у тебя всё хорошо 😊",
            f"Привет! {user_name}, как проходит день?",
            f"Здравствуй, {user_name}! Чем занимаешься?",
            f"Привет! {user_name}, как настроение? ✨"
        ]
        
        if last_topic:
            # Если есть тема, добавляем к ней
            topic_templates = [
                f"Привет, {user_name}! 👋 Как продвигается с {last_topic}?",
                f"Эй, {user_name}! Удалось ли разобраться с {last_topic}?",
                f"Привет! {user_name}, есть ли прогресс по {last_topic}? 😊"
            ]
            templates.extend(topic_templates)
        
        # Выбираем случайный шаблон
        import random
        return random.choice(templates)
    
    async def generate_group_response(self, 
                                    question: str, 
                                    chat_context: str = "") -> str:
        """
        Сгенерировать ответ для группы
        
        Args:
            question: Вопрос или тема для ответа
            chat_context: Контекст чата
        
        Returns:
            str: Ответ для группы
        """
        system_prompt = """
Ты - эксперт, который помогает в групповых обсуждениях. Твои ответы должны быть:
1. Полезными и информативными
2. Краткими (не более 2-3 предложений)
3. Дружелюбными
4. Не навязчивыми
5. Соответствующими контексту группы

Избегай:
- Слишком длинных ответов
- Спама или рекламы
- Политических тем
- Медицинских/юридических советов
"""
        
        messages = [
            {"role": "user", "content": f"Вопрос: {question}\nКонтекст чата: {chat_context}"}
        ]
        
        return await self.generate_response(messages, system_prompt)
    
    async def check_message_similarity(self, message1: str, message2: str) -> float:
        """
        Проверить схожесть двух сообщений (для анти-повтора)
        
        Args:
            message1: Первое сообщение
            message2: Второе сообщение
        
        Returns:
            float: Коэффициент схожести (0-1)
        """
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=[message1, message2]
            )
            
            # Получаем эмбеддинги
            embedding1 = response.data[0].embedding
            embedding2 = response.data[1].embedding
            
            # Вычисляем косинусное сходство
            similarity = self._cosine_similarity(embedding1, embedding2)
            return similarity
            
        except Exception as e:
            logger.error(f"Ошибка при проверке схожести: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Вычислить косинусное сходство между векторами"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


# Глобальный экземпляр LLM клиента
llm_client = LLMClient()

