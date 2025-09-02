#!/usr/bin/env python3
"""
Универсальный LLM сервис для работы с разными провайдерами
"""

import logging
from typing import Optional, Dict, Any, List
from ai.llm_interface import LLMFactory

logger = logging.getLogger(__name__)

class UniversalLLMService:
    """Универсальный сервис для работы с LLM провайдерами"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Инициализирует провайдера на основе конфигурации"""
        provider_type = self.config.get('ai_provider', 'offline')
        
        # Формируем конфигурацию для провайдера
        provider_config = {
            'persona_name': self.config.get('persona_name', 'AI-ассистент')
        }
        
        # Добавляем специфичные настройки для каждого провайдера
        if provider_type == "yandex":
            provider_config.update({
                'api_key': self.config.get('yandex_api_key'),
                'folder_id': self.config.get('yandex_folder_id'),
                'model': self.config.get('yandex_model', 'yandexgpt-lite')
            })
        elif provider_type == "openai":
            provider_config.update({
                'api_key': self.config.get('openai_api_key'),
                'base_url': self.config.get('openai_base_url'),
                'model': self.config.get('openai_model', 'gpt-3.5-turbo'),
                'temperature': self.config.get('temperature', 0.7),
                'max_tokens': self.config.get('max_tokens', 1000)
            })
        elif provider_type == "gigachat":
            provider_config.update({
                'api_key': self.config.get('gigachat_api_key'),
                'model': self.config.get('gigachat_model', 'GigaChat:latest')
            })
        
        # Создаем провайдера
        try:
            self.provider = LLMFactory.create_provider(provider_type, provider_config)
            logger.info(f"✅ LLM провайдер '{provider_type}' инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации провайдера '{provider_type}': {e}")
            # Fallback к оффлайн провайдеру
            self.provider = LLMFactory.create_provider('offline', provider_config)
            logger.info("🔄 Переключились на оффлайн провайдер")
    
    def is_available(self) -> bool:
        """Проверяет доступность LLM"""
        return self.provider and self.provider.is_available()
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Генерирует ответ с помощью LLM"""
        if not self.provider:
            return "Извините, LLM сервис недоступен."
        
        return self.provider.generate_response(prompt, context)
    
    def generate_conversation_response(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Генерирует ответ в контексте разговора"""
        if not self.provider:
            return "Извините, LLM сервис недоступен."
        
        return self.provider.generate_conversation_response(user_message, conversation_history)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущем провайдере"""
        if not self.provider:
            return {
                'type': 'none',
                'available': False,
                'models': []
            }
        
        return {
            'type': self.config.get('ai_provider', 'unknown'),
            'available': self.provider.is_available(),
            'models': self.provider.get_models()
        }
    
    def switch_provider(self, provider_type: str) -> bool:
        """Переключает провайдера"""
        try:
            old_provider = self.config.get('ai_provider')
            self.config['ai_provider'] = provider_type
            self._initialize_provider()
            
            if self.provider and self.provider.is_available():
                logger.info(f"✅ Успешно переключились с '{old_provider}' на '{provider_type}'")
                return True
            else:
                logger.warning(f"⚠️ Не удалось переключиться на '{provider_type}', вернулись к '{old_provider}'")
                self.config['ai_provider'] = old_provider
                self._initialize_provider()
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка переключения провайдера: {e}")
            return False
