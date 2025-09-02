#!/usr/bin/env python3
"""
Оптимизированный Telegram бот для естественных диалогов и группового участия
"""

import logging
import random
import time
from typing import Dict, List, Optional
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from core.config import Config
from ai.universal_llm import UniversalLLMService
from ai.content_filter import ContentFilter

class OptimizedTelegramBot:
    """Оптимизированный бот для естественных диалогов"""
    
    def __init__(self):
        self.config = Config.load()
        self.logger = logging.getLogger(__name__)
        
        # Инициализация LLM сервиса
        llm_config = {
            'ai_provider': self.config.ai.ai_provider,
            'persona_name': self.config.persona.name,
            'yandex_api_key': self.config.ai.yandex_api_key,
            'yandex_folder_id': self.config.ai.yandex_folder_id,
            'yandex_model': self.config.ai.yandex_model,
            'openai_api_key': self.config.ai.openai_api_key,
            'openai_base_url': self.config.ai.openai_base_url,
            'openai_model': self.config.ai.openai_model,
            'temperature': self.config.ai.temperature,
            'max_tokens': self.config.ai.max_tokens
        }
        
        self.llm_service = UniversalLLMService(llm_config)
        
        # Фильтр контента
        self.content_filter = ContentFilter({
            'forbidden_keywords': self.config.filter.forbidden_keywords,
            'forbidden_adult_keywords': self.config.filter.forbidden_adult_keywords,
            'forbidden_obscene_keywords': self.config.filter.forbidden_obscene_keywords
        })
        
        # История разговоров и статистика
        self.conversation_history = {}
        self.group_participation = {}
        self.user_last_message = {}
        
        # Настройки группового участия
        self.group_keywords = self.config.group.reply_keywords
        self.min_message_length = self.config.group.min_message_length
        self.max_daily_group_messages = self.config.limits.max_daily_messages_per_group
        
        self.logger.info(f"🤖 Оптимизированный бот запущен: {self.config.persona.name}")
        self.logger.info(f"👥 Групповой режим: {'🟢 Включен' if self.config.group.enabled else '🔴 Выключен'}")
        
        # Информация о провайдере
        provider_info = self.llm_service.get_provider_info()
        self.logger.info(f"🤖 AI провайдер: {provider_info['type']} ({'доступен' if provider_info['available'] else 'недоступен'})")
    
    def start_command(self, update: Update, context: CallbackContext):
        """Приветствие"""
        user = update.effective_user
        chat_type = update.effective_chat.type
        
        if chat_type == 'private':
            message = f"""Привет, {user.first_name}! 👋

Я {self.config.persona.name} - ваш AI-ассистент по программированию! 🐍

**Что я умею:**
• Помогаю с программированием (особенно Python)
• Объясняю сложные концепции простыми словами
• Отвечаю на вопросы о технологиях
• Помогаю в изучении новых языков программирования

**Команды:**
/start - это сообщение
/help - справка
/status - статус системы

Начните общение, отправив мне сообщение! 💬💻"""
        else:
            message = f"""Привет, {user.first_name}! 👋

Я {self.config.persona.name} - AI-ассистент по программированию! 🐍

**В группах я:**
• Отвечаю на вопросы о программировании
• Участвую в обсуждениях по технологиям
• Помогаю с кодом и алгоритмами
• Всегда указываю, что я AI-ассистент

**Упоминания:** Используйте @{self.config.bot.username} для прямого обращения! 💬"""
        
        update.message.reply_text(message)
    
    def help_command(self, update: Update, context: CallbackContext):
        """Справка"""
        chat_type = update.effective_chat.type
        
        if chat_type == 'private':
            help_text = f"""🤖 **Справка по командам:**

/start - приветствие и описание
/help - эта справка
/status - статус системы

**Как я работаю:**
• Отвечаю на ваши сообщения с помощью AI
• Поддерживаю разные LLM провайдеры
• Всегда указываю, что я ассистент

**Настройки:**
• Максимум сообщений в день: {self.config.limits.max_daily_messages_per_user}
• Задержка между сообщениями: {self.config.limits.min_delay_between_messages} сек

Есть вопросы? Просто напишите мне! 💬"""
        else:
            help_text = f"""🤖 **Справка для групповых чатов:**

**Как я работаю в группах:**
• Отвечаю на вопросы о программировании
• Участвую в обсуждениях по технологиям
• Помогаю с кодом и алгоритмами
• Всегда указываю, что я AI-ассистент

**Ключевые слова для участия:**
{', '.join(self.group_keywords[:5])}

**Упоминания:** Используйте @{self.config.bot.username} для прямого обращения! 💬"""
        
        update.message.reply_text(help_text)
    
    def status_command(self, update: Update, context: CallbackContext):
        """Статус системы"""
        provider_info = self.llm_service.get_provider_info()
        
        status_text = f"""📊 **Статус системы:**

**AI компоненты:**
• Провайдер: {provider_info['type'].upper()}
• Статус: {'🟢 Доступен' if provider_info['available'] else '🔴 Недоступен'}
• Модели: {', '.join(provider_info['models'][:3])}

**Групповой режим:**
• Статус: {'🟢 Включен' if self.config.group.enabled else '🔴 Выключен'}
• Ключевые слова: {len(self.group_keywords)} шт.
• Мин. длина сообщения: {self.min_message_length} символов
• Макс. сообщений в день: {self.max_daily_group_messages}

**Бот:**
• Имя: {self.config.bot.name}
• Username: @{self.config.bot.username}
• Групповой режим: {'🟢 Включен' if self.config.group.enabled else '🔴 Выключен'}

**Лимиты:**
• Макс. сообщений пользователю в день: {self.config.limits.max_daily_messages_per_user}
• Макс. сообщений в группе в день: {self.config.limits.max_daily_messages_per_group}
• Мин. задержка между сообщениями: {self.config.limits.min_delay_between_messages} сек"""
        
        update.message.reply_text(status_text)
    
    def test_mention_command(self, update: Update, context: CallbackContext):
        """Тестирование упоминаний в группах"""
        chat_type = update.effective_chat.type
        
        if chat_type == 'private':
            update.message.reply_text("❌ Эта команда работает только в группах!")
            return
        
        # Показываем информацию о том, как упоминать бота
        test_text = f"""🧪 **Тестирование упоминаний:**

**Способы упомянуть бота:**
1. @{self.config.bot.username} - прямое упоминание
2. {self.config.bot.name} - по имени
3. "Эй, бот" - общее обращение
4. "Помоги, ассистент" - просьба о помощи

**Попробуйте написать:**
• @{self.config.bot.username} привет!
• {self.config.bot.name}, как дела?
• Эй, бот, помоги с Python
• Слушай, ассистент, что думаешь о программировании?

**Логи упоминаний:**
Проверьте логи для детальной информации о том, как бот обрабатывает упоминания."""
        
        update.message.reply_text(test_text)
    
    def handle_private_message(self, update: Update, context: CallbackContext):
        """Обработка личных сообщений"""
        user = update.effective_user
        message_text = update.message.text
        user_id = str(user.id)
        
        self.logger.info(f"Личное сообщение от {user.id}: {message_text[:50]}...")
        
        # Проверяем контент
        content_ok, content_reason, _ = self.content_filter.check_message(message_text)
        if not content_ok:
            update.message.reply_text(f"⚠️ {content_reason}")
            return
        
        try:
            # Получаем историю разговора
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Добавляем сообщение пользователя
            self.conversation_history[user_id].append({
                'role': 'user',
                'content': message_text,
                'timestamp': time.time()
            })
            
            # Ограничиваем историю
            if len(self.conversation_history[user_id]) > 10:
                self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
            
            # Генерируем ответ
            response = self.llm_service.generate_conversation_response(
                message_text, 
                self.conversation_history[user_id]
            )
            
            # Добавляем ответ в историю
            self.conversation_history[user_id].append({
                'role': 'assistant',
                'content': response,
                'timestamp': time.time()
            })
            
            # Отправляем ответ
            update.message.reply_text(response)
            
            self.logger.info(f"AI ответ отправлен пользователю {user.id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации ответа: {e}")
            update.message.reply_text("Извините, произошла ошибка. Попробуйте позже.")
    
    def handle_group_message(self, update: Update, context: CallbackContext):
        """Обработка групповых сообщений"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        message_text = update.message.text
        chat_id_str = str(chat_id)
        
        self.logger.debug(f"Получено групповое сообщение от {user.id} в чате {chat_id}: {message_text[:50]}...")
        
        # Проверяем, включен ли групповой режим
        if not self.config.group.enabled:
            self.logger.debug(f"Групповой режим отключен для чата {chat_id}")
            return
        
        # Проверяем, упомянут ли бот (несколько способов)
        bot_mentioned = False
        bot_username = self.config.bot.username
        
        # Способ 1: Проверяем по username из конфигурации
        if bot_username and f"@{bot_username}" in message_text:
            bot_mentioned = True
            self.logger.info(f"Бот упомянут по username '{bot_username}' пользователем {user.id} в чате {chat_id}")
        
        # Способ 2: Проверяем по username из context.bot
        elif context.bot.username and f"@{context.bot.username}" in message_text:
            bot_mentioned = True
            self.logger.info(f"Бот упомянут по context username '{context.bot.username}' пользователем {user.id} в чате {chat_id}")
        
        # Способ 3: Проверяем по имени бота из конфигурации
        elif self.config.bot.name and self.config.bot.name.lower() in message_text.lower():
            bot_mentioned = True
            self.logger.info(f"Бот упомянут по имени '{self.config.bot.name}' пользователем {user.id} в чате {chat_id}")
        
        # Способ 4: Проверяем по упоминанию "бот" или "ассистент"
        elif any(word in message_text.lower() for word in ["бот", "ассистент", "помощник"]):
            # Дополнительная проверка - должно быть обращение
            if any(word in message_text.lower() for word in ["@", "эй", "слушай", "помоги", "ответь"]):
                bot_mentioned = True
                self.logger.info(f"Бот упомянут по общему обращению пользователем {user.id} в чате {chat_id}")
        
        if bot_mentioned:
            self.logger.info(f"🎯 Бот упомянут! Сообщение: '{message_text[:100]}...'")
        
        # Проверяем, стоит ли участвовать в обсуждении
        should_participate = self._should_participate_in_group(message_text)
        if should_participate:
            self.logger.info(f"Решено участвовать в обсуждении в чате {chat_id}")
        
        # Если бот не упомянут и не стоит участвовать - выходим
        if not bot_mentioned and not should_participate:
            self.logger.debug(f"Не участвуем в чате {chat_id}: бот не упомянут и нет повода для участия")
            return
        
        # Проверяем лимиты для группы
        if not self._can_participate_in_group(chat_id_str):
            self.logger.info(f"Достигнут лимит сообщений для чата {chat_id}")
            return
        
        # Проверяем контент
        content_ok, content_reason, _ = self.content_filter.check_message(message_text)
        if not content_ok:
            self.logger.info(f"Контент не прошел проверку в чате {chat_id}: {content_reason}")
            return
        
        self.logger.info(f"Групповое участие: {user.id} в чате {chat_id}")
        
        try:
            if bot_mentioned:
                # Прямое обращение к боту
                self.logger.info(f"Генерируем ответ на прямое обращение в чате {chat_id}")
                response = self.llm_service.generate_response(message_text)
            else:
                # Участие в обсуждении
                self.logger.info(f"Генерируем ответ для участия в обсуждении в чате {chat_id}")
                response = self._generate_group_participation_response(message_text)
            
            # Отправляем ответ
            update.message.reply_text(response)
            
            # Обновляем статистику участия
            self.group_participation[chat_id_str] = self.group_participation.get(chat_id_str, 0) + 1
            
            self.logger.info(f"Групповой ответ отправлен в чат {chat_id}. Всего сообщений сегодня: {self.group_participation[chat_id_str]}")
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации группового ответа в чате {chat_id}: {e}")
            # Не отправляем сообщение об ошибке в группу, чтобы не спамить
    
    def _should_participate_in_group(self, message: str) -> bool:
        """Определяет, стоит ли участвовать в групповом обсуждении"""
        if not message or len(message) < self.min_message_length:
            self.logger.debug(f"Сообщение слишком короткое: {len(message)} < {self.min_message_length}")
            return False
        
        message_lower = message.lower()
        
        # Проверяем ключевые слова
        for keyword in self.group_keywords:
            if keyword.lower() in message_lower:
                self.logger.info(f"Найдено ключевое слово: {keyword}")
                return True
        
        # Проверяем наличие вопроса
        if "?" in message:
            self.logger.info("Найден вопрос в сообщении")
            return True
        
        # Проверяем тематические слова
        tech_keywords = ["python", "программирование", "код", "разработка", "технологии", "алгоритм", "функция", "класс", "переменная", "база данных", "api", "веб", "сайт", "приложение", "мобильное", "искусственный интеллект", "машинное обучение", "data science", "автоматизация", "тестирование", "деплой", "git", "github", "docker", "kubernetes", "cloud", "aws", "azure", "gcp"]
        for keyword in tech_keywords:
            if keyword in message_lower:
                self.logger.info(f"Найдено техническое ключевое слово: {keyword}")
                return True
        
        # Проверяем просьбы о помощи
        help_words = ["помогите", "помоги", "совет", "вопрос", "подскажите", "объясните", "как сделать", "что делать", "не работает", "ошибка", "проблема", "задача", "проект", "идея"]
        for word in help_words:
            if word in message_lower:
                self.logger.info(f"Найдена просьба о помощи: {word}")
                return True
        
        self.logger.debug(f"Сообщение не подходит для участия: {message[:50]}...")
        return False
    
    def _can_participate_in_group(self, chat_id: str) -> bool:
        """Проверяет, можно ли участвовать в группе"""
        daily_count = self.group_participation.get(chat_id, 0)
        return daily_count < self.max_daily_group_messages
    
    def _generate_group_participation_response(self, message: str) -> str:
        """Генерирует ответ для участия в групповом обсуждении"""
        message_lower = message.lower()
        
        # Ответы для тем программирования
        if any(word in message_lower for word in ["python", "программирование", "код", "разработка"]):
            responses = [
                "Интересная тема! 🐍 Python действительно отличный язык для начинающих. Что именно вас интересует?",
                "Согласен! 💻 Программирование - это навык будущего. С чего хотели бы начать изучение?",
                "Отличный вопрос! 🚀 Python отлично подходит для веб-разработки, AI и автоматизации. Есть конкретная задача?",
                "Как AI-ассистент, могу сказать, что Python - мой любимый язык! 😊 Что хотите обсудить?",
                "Отличная тема! ⚡ Python универсален - от простых скриптов до сложных AI систем. Какое направление вас привлекает?",
                "Согласен! 🌟 Python - идеальный выбор для изучения программирования. Есть ли конкретный проект, который хотите реализовать?"
            ]
            return random.choice(responses)
        
        # Ответы для вопросов
        elif "?" in message:
            responses = [
                "Хороший вопрос! 🤔 Как AI-ассистент, постараюсь дать полезный ответ.",
                "Интересно! 💭 Что именно вас интересует в этой теме?",
                "Отличный вопрос! 🎯 Расскажите подробнее, чтобы я мог лучше помочь.",
                "Любопытно! 🔍 Как AI-ассистент, готов обсудить эту тему.",
                "Интересный вопрос! 💡 Я специализируюсь на программировании и технологиях. Что хотите узнать?",
                "Отличный вопрос! 🚀 Как AI-ассистент, готов помочь с любыми вопросами по технологиям."
            ]
            return random.choice(responses)
        
        # Ответы для просьб о помощи
        elif any(word in message_lower for word in ["помогите", "помоги", "совет", "вопрос", "подскажите", "объясните", "как сделать", "что делать", "не работает", "ошибка", "проблема", "задача", "проект", "идея"]):
            responses = [
                "Конечно! 🤝 Как AI-ассистент, готов помочь с вопросами по программированию и технологиям.",
                "Отличный вопрос! 💡 Что именно вас интересует в области технологий?",
                "Готов помочь! 🚀 Расскажите подробнее о вашей задаче.",
                "Интересно! 🤔 Как AI-ассистент, специализируюсь на программировании. Чем могу помочь?",
                "Конечно! 💪 Я здесь, чтобы помочь с любыми вопросами по технологиям. Что вас интересует?",
                "Готов поддержать! 🌟 Как AI-ассистент, могу помочь с программированием, алгоритмами и технологиями."
            ]
            return random.choice(responses)
        
        # Ответы для технических тем
        elif any(word in message_lower for word in ["веб", "сайт", "приложение", "api", "база данных", "docker", "git", "github", "cloud", "aws", "azure", "gcp", "kubernetes", "devops", "тестирование", "автоматизация"]):
            responses = [
                "Отличная тема! 🌐 Современные технологии разработки очень интересны. Что конкретно вас интересует?",
                "Согласен! 🚀 DevOps и облачные технологии - это будущее разработки. Есть ли конкретная задача?",
                "Интересно! 💻 Современные инструменты разработки значительно упрощают жизнь. Что хотите обсудить?",
                "Как AI-ассистент, могу сказать, что эти технологии очень перспективны! 😊 Что именно вас привлекает?",
                "Отличная область! ⚡ Современные технологии позволяют создавать масштабируемые решения. Какое направление вас интересует?",
                "Согласен! 🌟 Эти технологии открывают множество возможностей. Есть ли конкретный проект?"
            ]
            return random.choice(responses)
        
        # Ответы для AI/ML тем
        elif any(word in message_lower for word in ["искусственный интеллект", "машинное обучение", "ai", "ml", "нейронная сеть", "алгоритм", "data science", "анализ данных", "tensorflow", "pytorch", "scikit-learn"]):
            responses = [
                "Превосходная тема! 🤖 AI и машинное обучение - это будущее технологий. Что именно вас интересует?",
                "Отлично! 🧠 Машинное обучение открывает невероятные возможности. С чего хотели бы начать?",
                "Интересно! 🌟 AI технологии развиваются очень быстро. Какое направление вас привлекает?",
                "Как AI-ассистент, могу сказать, что эта область очень увлекательна! 😊 Что хотите обсудить?",
                "Отличная тема! 🚀 AI и ML меняют мир. Есть ли конкретная задача или проект?",
                "Согласен! 💡 Эти технологии открывают новые горизонты. Что именно вас интересует?"
            ]
            return random.choice(responses)
        
        # Общие ответы для участия
        else:
            responses = [
                "Интересная мысль! 🤔 Как AI-ассистент, готов обсудить эту тему.",
                "Согласен! 👍 Программирование и технологии - увлекательные области.",
                "Отличная точка зрения! 💡 Что еще вас интересует в этой сфере?",
                "Понятно! 🎯 Как AI-ассистент, готов помочь с вопросами по технологиям.",
                "Интересно! 🌟 Технологии развиваются очень быстро. Что именно вас привлекает?",
                "Согласен! 💪 Современные технологии открывают множество возможностей. Какое направление вас интересует?"
            ]
            return random.choice(responses)
    
    def handle_message(self, update: Update, context: CallbackContext):
        """Основной обработчик сообщений"""
        chat_type = update.effective_chat.type
        
        if chat_type == 'private':
            self.handle_private_message(update, context)
        elif chat_type in ['group', 'supergroup']:
            self.handle_group_message(update, context)
    
    def run(self):
        """Запуск бота"""
        try:
            self.logger.info("🚀 Запуск оптимизированного Telegram бота...")
            
            # Создаем updater
            self.updater = Updater(token=self.config.bot.token, use_context=True)
            self.dispatcher = self.updater.dispatcher
            
            # Регистрируем обработчики
            self.dispatcher.add_handler(CommandHandler("start", self.start_command))
            self.dispatcher.add_handler(CommandHandler("help", self.help_command))
            self.dispatcher.add_handler(CommandHandler("status", self.status_command))
            self.dispatcher.add_handler(CommandHandler("test_mention", self.test_mention_command))
            
            # Обработчик всех сообщений
            self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
            
            self.logger.info("✅ Обработчики зарегистрированы")
            self.logger.info(f"🤖 Бот @{self.config.bot.username} запущен")
            self.logger.info("📱 Ожидаю сообщения...")
            
            # Запускаем бота
            self.updater.start_polling()
            self.updater.idle()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска бота: {e}")
            raise

def main():
    """Главная функция"""
    bot = OptimizedTelegramBot()
    bot.run()

if __name__ == "__main__":
    main()
