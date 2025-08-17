from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass
class Cadence:
    quiet_start: int  # hour 0-23
    quiet_end: int    # hour 0-23
    timezone: str

    def now(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))

    def is_quiet(self, dt: datetime | None = None) -> bool:
        dt = dt or self.now()
        h = dt.hour
        if self.quiet_start <= self.quiet_end:
            return self.quiet_start <= h < self.quiet_end
        # wraps over midnight
        return h >= self.quiet_start or h < self.quiet_end

    def next_allowed_time(self, dt: datetime | None = None) -> datetime:
        dt = dt or self.now()
        if not self.is_quiet(dt):
            return dt
        # Move to quiet_end today or tomorrow
        if self.quiet_start <= self.quiet_end:
            return dt.replace(hour=self.quiet_end, minute=0, second=0, microsecond=0)
        # wraps over midnight; if we're before quiet_end, set to quiet_end today; else next day's quiet_end
        if dt.hour < self.quiet_end:
            return dt.replace(hour=self.quiet_end, minute=0, second=0, microsecond=0)
        target = (dt + timedelta(days=1)).replace(hour=self.quiet_end, minute=0, second=0, microsecond=0)
        return target

    def schedule_followup_in_days(self, min_days: int = 1, max_days: int = 3) -> datetime:
        days = random.randint(min_days, max_days)
        dt = self.now() + timedelta(days=days)
        dt = dt.replace(minute=random.randint(5, 50), second=0, microsecond=0, hour=random.randint(9, 20))
        if self.is_quiet(dt):
            dt = self.next_allowed_time(dt)
        return dt
