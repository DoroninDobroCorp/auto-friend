"""
Управление временем и расписанием
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class TimeManager:
    """Менеджер времени для системы"""
    
    def __init__(self, timezone: str = "Europe/Moscow", quiet_hours: tuple = (23, 8)):
        self.timezone = timezone
        self.quiet_hours_start, self.quiet_hours_end = quiet_hours
        self._validate_quiet_hours()
    
    def _validate_quiet_hours(self):
        """Проверяет корректность тихих часов"""
        if not (0 <= self.quiet_hours_start <= 23 and 0 <= self.quiet_hours_end <= 23):
            raise ValueError("Часы должны быть в диапазоне 0-23")
    
    def now(self) -> datetime:
        """Получает текущее время в настроенном часовом поясе"""
        return datetime.now(ZoneInfo(self.timezone))
    
    def is_quiet_time(self, dt: Optional[datetime] = None) -> bool:
        """Проверяет, является ли время тихим"""
        dt = dt or self.now()
        current_hour = dt.hour
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Простой случай: начало < конец (например 23:00 - 07:00)
            return self.quiet_hours_start <= current_hour < self.quiet_hours_end
        else:
            # Сложный случай: начало > конец (например 23:00 - 07:00)
            return current_hour >= self.quiet_hours_start or current_hour < self.quiet_hours_end
    
    def next_allowed_time(self, dt: Optional[datetime] = None) -> datetime:
        """Получает следующее разрешенное время"""
        dt = dt or self.now()
        
        if not self.is_quiet_time(dt):
            return dt
        
        # Перемещаемся к концу тихих часов
        if self.quiet_hours_start <= self.quiet_hours_end:
            return dt.replace(hour=self.quiet_hours_end, minute=0, second=0, microsecond=0)
        else:
            # Переход через полночь
            if dt.hour < self.quiet_hours_end:
                return dt.replace(hour=self.quiet_hours_end, minute=0, second=0, microsecond=0)
            else:
                target = (dt + timedelta(days=1)).replace(
                    hour=self.quiet_hours_end, minute=0, second=0, microsecond=0
                )
                return target
    
    def schedule_followup(self, min_days: int = 1, max_days: int = 3, 
                         preferred_hours: tuple = (9, 20)) -> datetime:
        """Планирует время для follow-up сообщения"""
        # Случайное количество дней
        days = random.randint(min_days, max_days)
        target_date = self.now() + timedelta(days=days)
        
        # Случайное время в предпочтительных часах
        preferred_start, preferred_end = preferred_hours
        hour = random.randint(preferred_start, preferred_end)
        minute = random.randint(5, 55)  # Избегаем ровных часов
        
        target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Проверяем, не попадает ли в тихие часы
        if self.is_quiet_time(target_date):
            target_date = self.next_allowed_time(target_date)
        
        return target_date
    
    def schedule_daily_task(self, hour: int, minute: int = 0) -> datetime:
        """Планирует ежедневную задачу"""
        now = self.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Если время уже прошло сегодня, планируем на завтра
        if target_time <= now:
            target_time += timedelta(days=1)
        
        return target_time
    
    def schedule_weekly_task(self, weekday: int, hour: int, minute: int = 0) -> datetime:
        """Планирует еженедельную задачу"""
        now = self.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Вычисляем дни до следующего указанного дня недели
        days_ahead = weekday - now.weekday()
        if days_ahead <= 0:  # Целевой день уже прошел на этой неделе
            days_ahead += 7
        
        target_time += timedelta(days=days_ahead)
        return target_time
    
    def get_time_until_next_allowed(self, dt: Optional[datetime] = None) -> timedelta:
        """Получает время до следующего разрешенного периода"""
        dt = dt or self.now()
        next_allowed = self.next_allowed_time(dt)
        return next_allowed - dt
    
    def is_business_hours(self, dt: Optional[datetime] = None) -> bool:
        """Проверяет, являются ли часы рабочими (9:00-18:00)"""
        dt = dt or self.now()
        return 9 <= dt.hour < 18
    
    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """Проверяет, является ли день выходным"""
        dt = dt or self.now()
        return dt.weekday() >= 5  # 5 = суббота, 6 = воскресенье
    
    def get_optimal_sending_time(self, user_preferences: Dict[str, Any] = None) -> datetime:
        """Получает оптимальное время для отправки сообщения"""
        now = self.now()
        
        if user_preferences:
            # Учитываем предпочтения пользователя
            preferred_hour = user_preferences.get('preferred_hour', 10)
            preferred_minute = user_preferences.get('preferred_minute', 0)
            
            target_time = now.replace(hour=preferred_hour, minute=preferred_minute, 
                                    second=0, microsecond=0)
            
            # Если время уже прошло, планируем на завтра
            if target_time <= now:
                target_time += timedelta(days=1)
        else:
            # Используем умолчания
            target_time = self.schedule_followup(1, 2, (9, 17))
        
        # Проверяем тихие часы
        if self.is_quiet_time(target_time):
            target_time = self.next_allowed_time(target_time)
        
        return target_time
    
    def format_time_until(self, target_time: datetime) -> str:
        """Форматирует время до указанного момента"""
        now = self.now()
        time_diff = target_time - now
        
        if time_diff.total_seconds() < 0:
            return "прошло"
        
        days = time_diff.days
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        
        if days > 0:
            return f"через {days} дн. {hours} ч."
        elif hours > 0:
            return f"через {hours} ч. {minutes} мин."
        else:
            return f"через {minutes} мин."
    
    def get_timezone_info(self) -> Dict[str, Any]:
        """Получает информацию о часовом поясе"""
        now = self.now()
        return {
            'timezone': self.timezone,
            'current_time': now.strftime('%H:%M:%S'),
            'current_date': now.strftime('%Y-%m-%d'),
            'weekday': now.strftime('%A'),
            'is_quiet_time': self.is_quiet_time(now),
            'is_business_hours': self.is_business_hours(now),
            'is_weekend': self.is_weekend(now),
            'quiet_hours': f"{self.quiet_hours_start:02d}:00 - {self.quiet_hours_end:02d}:00"
        }
    
    def adjust_for_timezone(self, dt: datetime, target_timezone: str) -> datetime:
        """Переводит время в другой часовой пояс"""
        source_tz = ZoneInfo(self.timezone)
        target_tz = ZoneInfo(target_timezone)
        
        # Сначала делаем время "наивным" (без часового пояса)
        naive_dt = dt.replace(tzinfo=None)
        
        # Привязываем к исходному часовому поясу
        source_dt = naive_dt.replace(tzinfo=source_tz)
        
        # Переводим в целевой часовой пояс
        target_dt = source_dt.astimezone(target_tz)
        
        return target_dt
