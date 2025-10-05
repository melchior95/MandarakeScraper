"""
Schedule state definitions and data models.

Defines the core data structures for the scheduling system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, time


class ScheduleType(Enum):
    """Type of schedule repetition."""
    DAILY = "daily"
    WEEKLY = "weekly"


class DayOfWeek(Enum):
    """Days of the week for weekly schedules."""
    SU = "Sunday"
    MO = "Monday"
    TU = "Tuesday"
    WE = "Wednesday"
    TH = "Thursday"
    FR = "Friday"
    SA = "Saturday"


@dataclass
class Schedule:
    """
    Represents a scheduled task.

    Attributes:
        schedule_id: Unique identifier
        name: User-friendly name
        active: Whether schedule is currently active
        schedule_type: Daily or weekly
        days: List of days (for weekly), e.g. ["FR", "MO"]
        frequency_hours: Run every X hours
        start_time_pst: Start time in PST (HH:MM format)
        end_date: When schedule expires (YYYY-MM-DD)
        config_files: List of config JSON filenames to run sequentially
        csv_newly_listed: Filter CSV to newly listed items only
        csv_in_stock: Filter CSV to in-stock items only
        csv_2nd_keyword: Add secondary keyword to eBay search
        comparison_method: Comparison method ("text" or "image")
        created_at: Creation timestamp
        last_run: Last execution timestamp
        next_run: Next scheduled execution timestamp
    """
    schedule_id: int
    name: str
    active: bool
    schedule_type: ScheduleType
    days: List[str] = field(default_factory=list)  # ["SU", "MO", "TU", etc.]
    frequency_hours: int = 24
    start_time_pst: str = "09:00"  # HH:MM format
    end_date: Optional[str] = None  # YYYY-MM-DD
    config_files: List[str] = field(default_factory=list)
    csv_newly_listed: bool = False
    csv_in_stock: bool = True
    csv_2nd_keyword: bool = False
    comparison_method: str = "text"  # "text" or "image"
    created_at: Optional[str] = None
    last_run: Optional[str] = None
    next_run: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'schedule_id': self.schedule_id,
            'name': self.name,
            'active': self.active,
            'type': self.schedule_type.value,
            'days': self.days,
            'frequency_hours': self.frequency_hours,
            'start_time_pst': self.start_time_pst,
            'end_date': self.end_date,
            'config_files': self.config_files,
            'csv_newly_listed': self.csv_newly_listed,
            'csv_in_stock': self.csv_in_stock,
            'csv_2nd_keyword': self.csv_2nd_keyword,
            'comparison_method': self.comparison_method,
            'created_at': self.created_at,
            'last_run': self.last_run,
            'next_run': self.next_run
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Schedule':
        """Create Schedule from dictionary."""
        return cls(
            schedule_id=data['schedule_id'],
            name=data['name'],
            active=data['active'],
            schedule_type=ScheduleType(data['type']),
            days=data.get('days', []),
            frequency_hours=data.get('frequency_hours', 24),
            start_time_pst=data.get('start_time_pst', '09:00'),
            end_date=data.get('end_date'),
            config_files=data.get('config_files', []),
            csv_newly_listed=data.get('csv_newly_listed', False),
            csv_in_stock=data.get('csv_in_stock', True),
            csv_2nd_keyword=data.get('csv_2nd_keyword', False),
            comparison_method=data.get('comparison_method', 'text'),
            created_at=data.get('created_at'),
            last_run=data.get('last_run'),
            next_run=data.get('next_run')
        )

    def is_valid(self) -> bool:
        """Validate schedule configuration."""
        if not self.name:
            return False
        if self.schedule_type == ScheduleType.WEEKLY and not self.days:
            return False
        if self.frequency_hours < 1:
            return False
        if not self.config_files:
            return False
        return True

    def get_display_days(self) -> str:
        """Get human-readable day list."""
        if self.schedule_type == ScheduleType.DAILY:
            return "Every day"
        if not self.days:
            return "No days selected"
        return ", ".join(self.days)
