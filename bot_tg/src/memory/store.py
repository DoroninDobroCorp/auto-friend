"""
Хранилище данных для userbot-а
"""
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseStore:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.database_path
        
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_paused BOOLEAN DEFAULT FALSE,
                    assistant_notified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица сообщений
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_id INTEGER,
                    text TEXT,
                    is_outgoing BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица лимитов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date DATE,
                    message_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица follow-up
            await db.execute("""
                CREATE TABLE IF NOT EXISTS follow_ups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    planned_date DATE,
                    message_template TEXT,
                    status TEXT DEFAULT 'pending',
                    sent_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица активности в группах
            await db.execute("""
                CREATE TABLE IF NOT EXISTS group_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    user_id INTEGER,
                    last_comment_date DATE,
                    last_author_cooldown TIMESTAMP NULL,
                    UNIQUE(chat_id, user_id)
                )
            """)
            
            # Индексы для оптимизации
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_timestamp ON messages(user_id, timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_daily_limits_user_date ON daily_limits(user_id, date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_follow_ups_status_date ON follow_ups(status, planned_date)")
            
            await db.commit()
            logger.info("База данных инициализирована")
    
    async def get_or_create_user(self, user_id: int, username: str = None, 
                                first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Получить или создать пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Проверяем существование пользователя
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = await cursor.fetchone()
            
            if user:
                # Обновляем информацию
                await db.execute("""
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (username, first_name, last_name, user_id))
                await db.commit()
                return dict(user)
            else:
                # Создаём нового пользователя
                await db.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, first_name, last_name))
                await db.commit()
                
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user = await cursor.fetchone()
                return dict(user)
    
    async def save_message(self, user_id: int, message_id: int, text: str, is_outgoing: bool):
        """Сохранить сообщение"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO messages (user_id, message_id, text, is_outgoing)
                VALUES (?, ?, ?, ?)
            """, (user_id, message_id, text, is_outgoing))
            await db.commit()
    
    async def get_user_messages(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить последние сообщения пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
            messages = await cursor.fetchall()
            return [dict(msg) for msg in messages]
    
    async def check_daily_limit(self, user_id: int) -> bool:
        """Проверить дневной лимит сообщений"""
        today = datetime.now().date()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT message_count FROM daily_limits 
                WHERE user_id = ? AND date = ?
            """, (user_id, today))
            result = await cursor.fetchone()
            
            if result:
                return result[0] < settings.max_daily_messages_per_user
            else:
                # Создаём запись для сегодня
                await db.execute("""
                    INSERT INTO daily_limits (user_id, date, message_count)
                    VALUES (?, ?, 0)
                """, (user_id, today))
                await db.commit()
                return True
    
    async def increment_daily_limit(self, user_id: int):
        """Увеличить счётчик дневных сообщений"""
        today = datetime.now().date()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE daily_limits 
                SET message_count = message_count + 1
                WHERE user_id = ? AND date = ?
            """, (user_id, today))
            await db.commit()
    
    async def set_user_paused(self, user_id: int, paused: bool):
        """Установить статус паузы для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET is_paused = ? WHERE user_id = ?
            """, (paused, user_id))
            await db.commit()
    
    async def is_user_paused(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь на паузе"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT is_paused FROM users WHERE user_id = ?
            """, (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else False
    
    async def set_assistant_notified(self, user_id: int):
        """Отметить, что пользователь уведомлён об ассистенте"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET assistant_notified = TRUE WHERE user_id = ?
            """, (user_id,))
            await db.commit()
    
    async def is_assistant_notified(self, user_id: int) -> bool:
        """Проверить, уведомлён ли пользователь об ассистенте"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT assistant_notified FROM users WHERE user_id = ?
            """, (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else False
    
    async def clear_user_history(self, user_id: int):
        """Очистить историю пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM daily_limits WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM follow_ups WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def create_follow_up(self, user_id: int, message_template: str, days_ahead: int):
        """Создать follow-up сообщение"""
        planned_date = datetime.now().date() + timedelta(days=days_ahead)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO follow_ups (user_id, planned_date, message_template)
                VALUES (?, ?, ?)
            """, (user_id, planned_date, message_template))
            await db.commit()
    
    async def get_pending_follow_ups(self) -> List[Dict[str, Any]]:
        """Получить ожидающие follow-up сообщения"""
        today = datetime.now().date()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT f.*, u.username, u.first_name 
                FROM follow_ups f
                JOIN users u ON f.user_id = u.user_id
                WHERE f.status = 'pending' AND f.planned_date <= ?
            """, (today,))
            follow_ups = await cursor.fetchall()
            return [dict(fu) for fu in follow_ups]
    
    async def mark_follow_up_sent(self, follow_up_id: int):
        """Отметить follow-up как отправленное"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE follow_ups 
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (follow_up_id,))
            await db.commit()
    
    async def check_group_cooldown(self, chat_id: int, user_id: int) -> bool:
        """Проверить кулдаун для группы"""
        today = datetime.now().date()
        cooldown_time = datetime.now() - timedelta(minutes=settings.group_cooldown_minutes)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT last_comment_date, last_author_cooldown 
                FROM group_activity 
                WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id))
            result = await cursor.fetchone()
            
            if result:
                last_comment_date, last_cooldown = result
                # Проверяем дневной лимит
                if last_comment_date == today:
                    return False
                # Проверяем кулдаун автора
                if last_cooldown and datetime.fromisoformat(last_cooldown) > cooldown_time:
                    return False
            
            return True
    
    async def update_group_activity(self, chat_id: int, user_id: int):
        """Обновить активность в группе"""
        today = datetime.now().date()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO group_activity 
                (chat_id, user_id, last_comment_date, last_author_cooldown)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (chat_id, user_id, today))
            await db.commit()
    
    async def get_daily_stats(self) -> Dict[str, Any]:
        """Получить статистику за день"""
        today = datetime.now().date()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Уникальные диалоги
            cursor = await db.execute("""
                SELECT COUNT(DISTINCT user_id) as unique_dialogs
                FROM messages 
                WHERE DATE(timestamp) = ?
            """, (today,))
            unique_dialogs = (await cursor.fetchone())[0]
            
            # Исходящие сообщения
            cursor = await db.execute("""
                SELECT COUNT(*) as outgoing_messages
                FROM messages 
                WHERE DATE(timestamp) = ? AND is_outgoing = TRUE
            """, (today,))
            outgoing_messages = (await cursor.fetchone())[0]
            
            # Follow-up статистика
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_follow_ups,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_follow_ups,
                    SUM(CASE WHEN status = 'pending' AND planned_date < ? THEN 1 ELSE 0 END) as delayed_follow_ups
                FROM follow_ups 
                WHERE DATE(created_at) = ?
            """, (today, today))
            follow_up_stats = await cursor.fetchone()
            
            return {
                'date': today,
                'unique_dialogs': unique_dialogs,
                'outgoing_messages': outgoing_messages,
                'follow_ups_created': follow_up_stats[0] if follow_up_stats else 0,
                'follow_ups_sent': follow_up_stats[1] if follow_up_stats else 0,
                'follow_ups_delayed': follow_up_stats[2] if follow_up_stats else 0
            }


# Глобальный экземпляр хранилища
store = DatabaseStore()

