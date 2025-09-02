"""
Управление базой данных
"""

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from .exceptions import DatabaseError

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = "ai_assistant.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        with self._connect() as conn:
            conn.executescript("""
                -- Пользователи
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    platform_user_id TEXT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    consent INTEGER DEFAULT 0,
                    paused INTEGER DEFAULT 0,
                    last_contact_at TEXT,
                    daily_msg_count INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    bot_notified INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(platform, platform_user_id)
                );
                
                -- Сообщения
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER,
                    direction TEXT NOT NULL, -- 'in' или 'out'
                    content TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                -- Чаты (группы)
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    platform_chat_id TEXT NOT NULL,
                    title TEXT,
                    chat_type TEXT DEFAULT 'group',
                    daily_msg_count INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(platform, platform_chat_id)
                );
                
                -- Запланированные сообщения
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER,
                    content TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                -- Статистика
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_messages INTEGER DEFAULT 0,
                    total_users INTEGER DEFAULT 0,
                    total_chats INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(date)
                );
                
                -- Индексы
                CREATE INDEX IF NOT EXISTS idx_users_platform_uid ON users(platform, platform_user_id);
                CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
                CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
                CREATE INDEX IF NOT EXISTS idx_chats_platform_cid ON chats(platform, platform_chat_id);
                CREATE INDEX IF NOT EXISTS idx_scheduled_messages_scheduled_at ON scheduled_messages(scheduled_at);
            """)
    
    @contextmanager
    def _connect(self):
        """Контекстный менеджер для подключения к БД"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                yield conn
                conn.commit()
            finally:
                conn.close()
    
    def execute(self, query: str, params: Tuple = ()) -> Any:
        """Выполняет SQL запрос"""
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, params)
                return cursor
        except Exception as e:
            raise DatabaseError(f"Ошибка выполнения запроса: {e}")
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """Выполняет множество SQL запросов"""
        try:
            with self._connect() as conn:
                conn.executemany(query, params_list)
        except Exception as e:
            raise DatabaseError(f"Ошибка выполнения множественных запросов: {e}")
    
    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """Получает одну запись"""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Получает все записи"""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Вставляет запись и возвращает ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, tuple(data.values()))
                return cursor.lastrowid
        except Exception as e:
            raise DatabaseError(f"Ошибка вставки в {table}: {e}")
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: Tuple) -> int:
        """Обновляет записи"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, tuple(data.values()) + where_params)
                return cursor.rowcount
        except Exception as e:
            raise DatabaseError(f"Ошибка обновления в {table}: {e}")
    
    def delete(self, table: str, where: str, where_params: Tuple) -> int:
        """Удаляет записи"""
        query = f"DELETE FROM {table} WHERE {where}"
        
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, where_params)
                return cursor.rowcount
        except Exception as e:
            raise DatabaseError(f"Ошибка удаления из {table}: {e}")
    
    def table_exists(self, table_name: str) -> bool:
        """Проверяет существование таблицы"""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetch_one(query, (table_name,))
        return result is not None
    
    def get_table_info(self, table_name: str) -> List[Tuple]:
        """Получает информацию о структуре таблицы"""
        query = "PRAGMA table_info(?)"
        return self.fetch_all(query, (table_name,))
    
    def backup(self, backup_path: str) -> None:
        """Создает резервную копию базы данных"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
        except Exception as e:
            raise DatabaseError(f"Ошибка создания резервной копии: {e}")
    
    def vacuum(self) -> None:
        """Оптимизирует базу данных"""
        try:
            with self._connect() as conn:
                conn.execute("VACUUM;")
        except Exception as e:
            raise DatabaseError(f"Ошибка оптимизации БД: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику базы данных"""
        stats = {}
        
        # Количество пользователей
        result = self.fetch_one("SELECT COUNT(*) FROM users")
        stats['total_users'] = result[0] if result else 0
        
        # Количество сообщений
        result = self.fetch_one("SELECT COUNT(*) FROM messages")
        stats['total_messages'] = result[0] if result else 0
        
        # Количество чатов
        result = self.fetch_one("SELECT COUNT(*) FROM chats")
        stats['total_chats'] = result[0] if result else 0
        
        # Размер базы данных
        import os
        stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
        
        return stats
