#!/usr/bin/env python3
"""
Модуль для работы с Yandex GPT API
"""

import logging
import os
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

from ai.llm_interface import LLMProvider

class YandexLLMProvider(LLMProvider):
    """Провайдер для работы с Yandex GPT"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('api_key')
        self.folder_id = config.get('folder_id')
        self.model = config.get('model', 'yandexgpt-lite')
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        super().__init__(config)
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к Yandex GPT"""
        try:
            # Простой тест
            response = self._make_request("Привет! Как дела?")
            if response:
                self.is_available_flag = True
                logger.info("✅ Yandex GPT клиент успешно инициализирован")
                return True
        except Exception as e:
            logger.error(f"Ошибка тестирования Yandex GPT: {e}")
        
        self.is_available_flag = False
        logger.warning("⚠️ Yandex GPT недоступен, будет использоваться оффлайн режим")
        return False
    
    def _make_request(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Выполняет запрос к Yandex GPT API"""
        try:
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Формируем сообщения
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "text": system_prompt
                })
            
            messages.append({
                "role": "user",
                "text": prompt
            })
            
            data = {
                "modelUri": f"gpt://{self.folder_id}/{self.model}",
                "completionOptions": {
                    "temperature": 0.7,
                    "maxTokens": 1000,
                    "stream": False
                },
                "messages": messages
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["result"]["alternatives"][0]["message"]["text"]
            else:
                logger.error(f"Ошибка Yandex GPT API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка запроса к Yandex GPT: {e}")
            return None
    

    
    def get_models(self) -> list:
        """Получает список доступных моделей"""
        return ["yandexgpt-lite", "yandexgpt", "yandexgpt-instruct"]
