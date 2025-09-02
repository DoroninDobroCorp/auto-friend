"""
Telegram клиент с использованием Telethon
"""
import asyncio
import datetime
import logging
from typing import Optional, Dict, Any
from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Message

from src.reports.generator import ReportGenerator
from ..config import settings
from ..memory.store import store
from ..dialog.manager import dialog_manager

logger = logging.getLogger(__name__)


class TelegramUserbot:
    """Telegram userbot клиент"""
    
    def __init__(self):
        self.client = TelegramClient(
            'userbot_session',
            settings.api_id,
            settings.api_hash
        )
        self.me: Optional[User] = None
        
    async def start(self):
        """Запустить клиент"""
        await self.client.start(phone=settings.phone_number)
        self.me = await self.client.get_me()
        logger.info(f"Userbot запущен: {self.me.first_name} (@{self.me.username})")
        
        # Регистрируем обработчики событий
        self._register_handlers()
        
    async def run_forever(self):
        """Запустить клиент на постоянную работу"""
        await self.start()
        
        # Запускаем обработку follow-up в фоне
        asyncio.create_task(self._follow_up_worker())
        
        # Запускаем генерацию отчётов в фоне
        asyncio.create_task(self._report_worker())
        
        logger.info("Userbot работает...")
        await self.client.run_until_disconnected()
    
    def _register_handlers(self):
        """Зарегистрировать обработчики событий"""
        
        @self.client.on(events.NewMessage(incoming=True))
        async def handle_new_message(event: events.NewMessage.Event):
            """Обработать новое входящее сообщение"""
            try:
                await self._process_message(event.message)
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {e}")
        
        @self.client.on(events.MessageEdited(incoming=True))
        async def handle_edited_message(event: events.MessageEdited.Event):
            """Обработать отредактированное сообщение"""
            try:
                await self._process_message(event.message)
            except Exception as e:
                logger.error(f"Ошибка при обработке отредактированного сообщения: {e}")
    
    async def _process_message(self, message: Message):
        """Обработать сообщение"""
        # Игнорируем собственные сообщения
        if message.from_id == self.me.id:
            return
        
        # Получаем информацию о чате
        chat = await message.get_chat()
        sender = await message.get_sender()
        
        if not sender:
            logger.warning("Не удалось получить информацию об отправителе")
            return
        
        # Обрабатываем личные сообщения
        if isinstance(chat, User):
            await self._handle_private_message(message, sender)
        
        # Обрабатываем групповые сообщения
        elif isinstance(chat, Chat):
            await self._handle_group_message(message, sender, chat)
    
    async def _handle_private_message(self, message: Message, sender: User):
        """Обработать личное сообщение"""
        user_id = sender.id
        message_text = message.text or ""
        
        # Получаем или создаём пользователя
        user_info = await store.get_or_create_user(
            user_id=user_id,
            username=sender.username,
            first_name=sender.first_name,
            last_name=sender.last_name
        )
        
        # Проверяем команды
        if message_text.startswith('/'):
            response = await dialog_manager.handle_command(user_id, message_text)
            if response:
                await self._send_message(user_id, response)
            return
        
        # Обрабатываем обычное сообщение
        response = await dialog_manager.process_private_message(
            user_id, message_text, user_info
        )
        
        if response:
            await self._send_message(user_id, response)
    
    async def _handle_group_message(self, message: Message, sender: User, chat: Chat):
        """Обработать групповое сообщение"""
        if not settings.enable_group_mode:
            return
        
        chat_id = chat.id
        user_id = sender.id
        message_text = message.text or ""
        
        # Проверяем упоминания
        if self.me.username and f"@{self.me.username}" in message_text:
            # Отправляем личное сообщение при упоминании
            await self._send_private_intro(user_id, sender.first_name)
            return
        
        # Проверяем приглашения в ЛС
        if any(phrase in message_text.lower() for phrase in ['в лс', 'в личку', 'напиши в лс']):
            await self._send_private_intro(user_id, sender.first_name)
            return
        
        # Обрабатываем групповое сообщение
        response = await dialog_manager.process_group_message(
            chat_id, user_id, message_text, chat.title
        )
        
        if response:
            await self._send_group_message(chat_id, response)
    
    async def _send_message(self, user_id: int, text: str):
        """Отправить личное сообщение"""
        try:
            await self.client.send_message(user_id, text)
            logger.info(f"Отправлено сообщение пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
    
    async def _send_group_message(self, chat_id: int, text: str):
        """Отправить сообщение в группу"""
        try:
            await self.client.send_message(chat_id, text)
            logger.info(f"Отправлено сообщение в группу {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения в группу {chat_id}: {e}")
    
    async def _send_private_intro(self, user_id: int, user_name: str):
        """Отправить приветственное личное сообщение"""
        intro_text = f"""
            Привет, {user_name}! 👋

            Я ассистент, который помогает с общением. Рад познакомиться!

            Можешь написать мне в любое время, и я постараюсь помочь. Также у меня есть команды - используй /help для их просмотра.

            До встречи! 😊
        """.strip()
        
        await self._send_message(user_id, intro_text)
    
    async def _follow_up_worker(self):
        """Фоновый обработчик follow-up сообщений"""
        while True:
            try:
                # Обрабатываем follow-up каждые 30 минут
                await asyncio.sleep(30 * 60)
                
                follow_ups = await dialog_manager.process_follow_ups()
                
                for follow_up in follow_ups:
                    await self._send_message(
                        follow_up['user_id'], 
                        follow_up['message']
                    )
                    
                    # Отмечаем как отправленное
                    await store.mark_follow_up_sent(follow_up['follow_up_id'])
                    
                    logger.info(f"Отправлен follow-up пользователю {follow_up['user_id']}")
                
            except Exception as e:
                logger.error(f"Ошибка в follow-up worker: {e}")
    
    async def _report_worker(self):
        """Фоновый генератор отчётов"""
        while True:
            try:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
                now = datetime.datetime.now()  # Получаем текущее календарное время
                # Генерируем отчёт каждый день в 00:05
                if now.hour == 0 and now.minute == 5:
                    await ReportGenerator.generate_daily_report()
                    logger.info("Сгенерирован ежедневный отчёт")
                
            except Exception as e:
                logger.error(f"Ошибка в report worker: {e}")
    
    async def stop(self):
        """Остановить клиент"""
        await self.client.disconnect()
        logger.info("Userbot остановлен")


# Глобальный экземпляр userbot
userbot = TelegramUserbot()

