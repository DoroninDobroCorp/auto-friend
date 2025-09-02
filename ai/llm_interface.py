#!/usr/bin/env python3
"""
Универсальный интерфейс для работы с LLM провайдерами
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Базовый класс для LLM провайдеров"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_available_flag = False
        self._test_connection()
    
    @abstractmethod
    def _test_connection(self) -> bool:
        """Тестирует подключение к провайдеру"""
        pass
    
    @abstractmethod
    def _make_request(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Выполняет запрос к провайдеру"""
        pass
    
    @abstractmethod
    def get_models(self) -> List[str]:
        """Возвращает список доступных моделей"""
        pass
    
    def is_available(self) -> bool:
        """Проверяет доступность провайдера"""
        return self.is_available_flag
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Генерирует ответ с помощью LLM"""
        if not self.is_available():
            return self._generate_fallback_response(prompt, context)
        
        # Формируем системный промпт
        system_prompt = self._format_system_prompt(context)
        
        # Генерируем ответ
        response = self._make_request(prompt, system_prompt)
        
        if response:
            return response
        else:
            return self._generate_fallback_response(prompt, context)
    
    def generate_conversation_response(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Генерирует ответ в контексте разговора"""
        if not conversation_history:
            return self.generate_response(user_message)
        
        # Формируем полный контекст разговора
        full_prompt = self._format_conversation_prompt(user_message, conversation_history)
        
        return self.generate_response(full_prompt)
    
    def _format_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Форматирует системный промпт"""
        if not context or 'persona' not in context:
            return None
        
        persona = context['persona']
        return f"""Ты {persona.get('name', 'AI-ассистент')}, {persona.get('bio', 'помощник по программированию')}.

Твой стиль общения: {persona.get('style', 'дружелюбный и профессиональный')}.
Язык общения: {persona.get('language', 'русский')}.

Важные правила:
1. Всегда указывай, что ты AI-ассистент
2. Отвечай по существу и полезно
3. Если не знаешь ответ, честно скажи об этом
4. Используй эмодзи для дружелюбности
5. Специализируйся на программировании и технологиях"""
    
    def _format_conversation_prompt(self, user_message: str, conversation_history: List[Dict[str, str]]) -> str:
        """Форматирует промпт для разговора"""
        full_prompt = ""
        for msg in conversation_history[-5:]:  # Последние 5 сообщений
            role = "Пользователь" if msg['role'] == 'user' else "Ассистент"
            full_prompt += f"{role}: {msg['content']}\n"
        
        full_prompt += f"Пользователь: {user_message}\nАссистент:"
        return full_prompt
    
    def _generate_fallback_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Генерирует эвристический ответ при недоступности LLM"""
        prompt_lower = prompt.lower()
        
        # Простые эвристические ответы
        if "привет" in prompt_lower:
            return "Привет! 👋 Рад вас видеть! Как дела?"
        elif "как дела" in prompt_lower:
            return "Спасибо, у меня все хорошо! Занимаюсь интересными проектами. А у вас как дела?"
        elif "?" in prompt:
            return "Интересный вопрос! Я AI-ассистент, специализируюсь на программировании. Постараюсь дать полезный ответ."
        elif "спасибо" in prompt_lower:
            return "Пожалуйста! 😊 Рад быть полезным!"
        elif "пока" in prompt_lower or "до свидания" in prompt_lower:
            return "До свидания! Было приятно пообщаться! 👋"
        else:
            return f"Спасибо за сообщение! Я AI-ассистент. Ваше сообщение интересное: '{prompt[:30]}...' Что еще вас интересует?"

class LLMFactory:
    """Фабрика для создания LLM провайдеров"""
    
    @staticmethod
    def create_provider(provider_type: str, config: Dict[str, Any]) -> LLMProvider:
        """Создает провайдера по типу"""
        if provider_type == "yandex":
            from ai.yandex_llm import YandexLLMProvider
            return YandexLLMProvider(config)
        elif provider_type == "openai":
            from ai.openai_llm import OpenAILLMProvider
            return OpenAILLMProvider(config)
        elif provider_type == "offline":
            from ai.offline_llm import OfflineLLMProvider
            return OfflineLLMProvider(config)
        else:
            logger.error(f"Неизвестный тип провайдера: {provider_type}")
            from ai.offline_llm import OfflineLLMProvider
            return OfflineLLMProvider(config)
