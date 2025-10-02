"""
Schedule storage layer - JSON persistence.

Handles saving and loading schedules to/from disk.
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from gui.schedule_states import Schedule


class ScheduleStorage:
    """Manages schedule persistence to JSON file."""

    def __init__(self, storage_path: str = "schedules.json"):
        """
        Initialize storage.

        Args:
            storage_path: Path to JSON storage file
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Create storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self.storage_path.write_text('[]', encoding='utf-8')

    def load_all(self) -> List[Schedule]:
        """
        Load all schedules from storage.

        Returns:
            List of Schedule objects
        """
        try:
            data = json.loads(self.storage_path.read_text(encoding='utf-8'))
            return [Schedule.from_dict(item) for item in data]
        except Exception as e:
            print(f"[SCHEDULE STORAGE] Error loading schedules: {e}")
            return []

    def save_all(self, schedules: List[Schedule]):
        """
        Save all schedules to storage.

        Args:
            schedules: List of Schedule objects to save
        """
        try:
            data = [s.to_dict() for s in schedules]
            self.storage_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"[SCHEDULE STORAGE] Error saving schedules: {e}")

    def get_by_id(self, schedule_id: int) -> Optional[Schedule]:
        """
        Get schedule by ID.

        Args:
            schedule_id: Schedule ID to find

        Returns:
            Schedule object or None if not found
        """
        schedules = self.load_all()
        for schedule in schedules:
            if schedule.schedule_id == schedule_id:
                return schedule
        return None

    def add_schedule(self, schedule: Schedule) -> Schedule:
        """
        Add new schedule to storage.

        Args:
            schedule: Schedule to add

        Returns:
            Schedule with assigned ID
        """
        schedules = self.load_all()

        # Auto-assign ID
        if schedule.schedule_id == 0:
            max_id = max([s.schedule_id for s in schedules], default=0)
            schedule.schedule_id = max_id + 1

        # Set created timestamp
        if not schedule.created_at:
            schedule.created_at = datetime.now().isoformat()

        schedules.append(schedule)
        self.save_all(schedules)
        return schedule

    def update_schedule(self, schedule: Schedule):
        """
        Update existing schedule.

        Args:
            schedule: Schedule with updated data
        """
        schedules = self.load_all()
        for i, s in enumerate(schedules):
            if s.schedule_id == schedule.schedule_id:
                schedules[i] = schedule
                break
        self.save_all(schedules)

    def delete_schedule(self, schedule_id: int):
        """
        Delete schedule by ID.

        Args:
            schedule_id: ID of schedule to delete
        """
        schedules = self.load_all()
        schedules = [s for s in schedules if s.schedule_id != schedule_id]
        self.save_all(schedules)

    def get_active_schedules(self) -> List[Schedule]:
        """
        Get all active schedules.

        Returns:
            List of active schedules
        """
        schedules = self.load_all()
        return [s for s in schedules if s.active]

    def toggle_active(self, schedule_id: int, active: bool):
        """
        Toggle schedule active state.

        Args:
            schedule_id: Schedule ID
            active: New active state
        """
        schedule = self.get_by_id(schedule_id)
        if schedule:
            schedule.active = active
            self.update_schedule(schedule)

    def get_next_id(self) -> int:
        """
        Get next available schedule ID.

        Returns:
            Next ID number
        """
        schedules = self.load_all()
        if not schedules:
            return 1
        return max([s.schedule_id for s in schedules]) + 1
