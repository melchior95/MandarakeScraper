"""
Schedule manager - business logic for schedule operations.

Handles schedule creation, updates, and next-run calculations.
"""

from datetime import datetime, timedelta, time as dt_time
from typing import List, Optional
import pytz

from gui.schedule_states import Schedule, ScheduleType
from gui.schedule_storage import ScheduleStorage


class ScheduleManager:
    """Manages schedule business logic."""

    def __init__(self, storage_path: str = "schedules.json"):
        """
        Initialize manager.

        Args:
            storage_path: Path to storage file
        """
        self.storage = ScheduleStorage(storage_path)
        self.pst_tz = pytz.timezone('America/Los_Angeles')

    def create_schedule(
        self,
        name: str,
        schedule_type: ScheduleType,
        days: List[str],
        frequency_hours: int,
        start_time_pst: str,
        end_date: Optional[str],
        config_files: List[str],
        active: bool = True,
        comparison_method: str = "text"
    ) -> Schedule:
        """
        Create a new schedule.

        Args:
            name: Schedule name
            schedule_type: DAILY or WEEKLY
            days: List of day codes (e.g. ["FR", "MO"])
            frequency_hours: Run every X hours
            start_time_pst: Start time (HH:MM)
            end_date: End date (YYYY-MM-DD)
            config_files: List of config JSON files
            active: Whether schedule is active
            comparison_method: Comparison method ("text" or "image")

        Returns:
            Created schedule
        """
        schedule = Schedule(
            schedule_id=0,  # Will be auto-assigned
            name=name,
            active=active,
            schedule_type=schedule_type,
            days=days,
            frequency_hours=frequency_hours,
            start_time_pst=start_time_pst,
            end_date=end_date,
            config_files=config_files,
            comparison_method=comparison_method
        )

        # Calculate next run time
        schedule.next_run = self.calculate_next_run(schedule)

        return self.storage.add_schedule(schedule)

    def update_schedule(self, schedule: Schedule):
        """
        Update existing schedule.

        Args:
            schedule: Schedule with updated data
        """
        # Recalculate next run time
        schedule.next_run = self.calculate_next_run(schedule)
        self.storage.update_schedule(schedule)

    def delete_schedule(self, schedule_id: int):
        """Delete schedule by ID."""
        self.storage.delete_schedule(schedule_id)

    def get_all_schedules(self) -> List[Schedule]:
        """Get all schedules."""
        return self.storage.load_all()

    def get_active_schedules(self) -> List[Schedule]:
        """Get only active schedules."""
        return self.storage.get_active_schedules()

    def toggle_active(self, schedule_id: int, active: bool):
        """Toggle schedule active state."""
        self.storage.toggle_active(schedule_id, active)

    def mark_schedule_executed(self, schedule_id: int):
        """
        Mark schedule as executed and calculate next run.

        Args:
            schedule_id: Schedule ID
        """
        schedule = self.storage.get_by_id(schedule_id)
        if schedule:
            schedule.last_run = datetime.now(self.pst_tz).isoformat()
            schedule.next_run = self.calculate_next_run(schedule)
            self.storage.update_schedule(schedule)

    def calculate_next_run(self, schedule: Schedule) -> Optional[str]:
        """
        Calculate next run time based on schedule rules.

        Args:
            schedule: Schedule to calculate for

        Returns:
            ISO format datetime string or None if expired
        """
        now = datetime.now(self.pst_tz)

        # Check if schedule has expired
        if schedule.end_date:
            end_dt = datetime.strptime(schedule.end_date, '%Y-%m-%d')
            end_dt = self.pst_tz.localize(end_dt.replace(hour=23, minute=59, second=59))
            if now > end_dt:
                return None

        # Parse start time
        try:
            hour, minute = map(int, schedule.start_time_pst.split(':'))
            start_time = dt_time(hour, minute)
        except (ValueError, AttributeError):
            start_time = dt_time(9, 0)  # Default to 9 AM

        # If this is first run (no last_run), start from today/next valid day
        if not schedule.last_run:
            next_run = self._get_first_run(schedule, now, start_time)
        else:
            # Calculate next run from last run + frequency
            last_run_dt = datetime.fromisoformat(schedule.last_run)
            next_run = last_run_dt + timedelta(hours=schedule.frequency_hours)

            # For weekly schedules, ensure next run is on a valid day
            if schedule.schedule_type == ScheduleType.WEEKLY:
                next_run = self._adjust_to_valid_weekday(schedule, next_run, start_time)

        # Ensure next run is in the future
        if next_run <= now:
            next_run = now + timedelta(hours=schedule.frequency_hours)
            if schedule.schedule_type == ScheduleType.WEEKLY:
                next_run = self._adjust_to_valid_weekday(schedule, next_run, start_time)

        # Check if next run exceeds end date
        if schedule.end_date:
            if next_run > end_dt:
                return None

        return next_run.isoformat()

    def _get_first_run(
        self,
        schedule: Schedule,
        now: datetime,
        start_time: dt_time
    ) -> datetime:
        """Get first run time for a new schedule."""
        # Start with today at the specified time
        first_run = now.replace(
            hour=start_time.hour,
            minute=start_time.minute,
            second=0,
            microsecond=0
        )

        # If time has passed today, start tomorrow
        if first_run <= now:
            first_run += timedelta(days=1)

        # For weekly schedules, find next valid day
        if schedule.schedule_type == ScheduleType.WEEKLY:
            first_run = self._adjust_to_valid_weekday(schedule, first_run, start_time)

        return first_run

    def _adjust_to_valid_weekday(
        self,
        schedule: Schedule,
        target_dt: datetime,
        start_time: dt_time
    ) -> datetime:
        """Adjust datetime to next valid weekday for weekly schedules."""
        if not schedule.days:
            return target_dt

        # Map day codes to weekday numbers (0=Monday, 6=Sunday)
        day_map = {
            'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3,
            'FR': 4, 'SA': 5, 'SU': 6
        }

        valid_weekdays = [day_map[day] for day in schedule.days if day in day_map]
        if not valid_weekdays:
            return target_dt

        # Find next valid weekday
        current_weekday = target_dt.weekday()
        for i in range(7):
            check_day = (current_weekday + i) % 7
            if check_day in valid_weekdays:
                next_valid = target_dt + timedelta(days=i)
                return next_valid.replace(
                    hour=start_time.hour,
                    minute=start_time.minute,
                    second=0,
                    microsecond=0
                )

        return target_dt

    def get_schedules_due_for_execution(self) -> List[Schedule]:
        """
        Get all active schedules that are due to run now.

        Returns:
            List of schedules ready to execute
        """
        active_schedules = self.get_active_schedules()
        now = datetime.now(self.pst_tz)
        due = []

        for schedule in active_schedules:
            if not schedule.next_run:
                continue

            next_run_dt = datetime.fromisoformat(schedule.next_run)
            # Make timezone-aware if needed
            if next_run_dt.tzinfo is None:
                next_run_dt = self.pst_tz.localize(next_run_dt)

            if next_run_dt <= now:
                due.append(schedule)

        return due

    def update_auto_purchase_check_time(self, schedule_id: int):
        """
        Update last check time for auto-purchase schedule.

        Args:
            schedule_id: ID of schedule to update
        """
        schedule = self.storage.get_by_id(schedule_id)
        if schedule:
            now = datetime.now()
            schedule.auto_purchase_last_check = now.isoformat()
            schedule.auto_purchase_next_check = (
                now + timedelta(minutes=schedule.auto_purchase_check_interval)
            ).isoformat()
            self.storage.update_schedule(schedule)

    def mark_auto_purchase_completed(
        self,
        schedule_id: int,
        purchased_price: int,
        order_id: Optional[str] = None
    ):
        """
        Mark auto-purchase as completed and disable monitoring.

        Args:
            schedule_id: ID of schedule
            purchased_price: Price paid in JPY
            order_id: Order confirmation ID
        """
        schedule = self.storage.get_by_id(schedule_id)
        if schedule:
            schedule.auto_purchase_enabled = False
            schedule.active = False  # Stop monitoring
            schedule.name = f"{schedule.name} ✓ PURCHASED"
            self.storage.update_schedule(schedule)

            # Log to purchase history
            self._log_auto_purchase(schedule_id, purchased_price, order_id)

    def _log_auto_purchase(self, schedule_id: int, purchased_price: int, order_id: Optional[str]):
        """
        Log auto-purchase to history file.

        Args:
            schedule_id: Schedule ID
            purchased_price: Price paid
            order_id: Order confirmation ID
        """
        import json
        from pathlib import Path

        log_file = Path("auto_purchase_log.json")

        # Load existing logs
        if log_file.exists():
            logs = json.loads(log_file.read_text(encoding='utf-8'))
        else:
            logs = []

        # Get schedule details
        schedule = self.storage.get_by_id(schedule_id)
        if schedule:
            # Add new log entry
            log_entry = {
                'schedule_id': schedule_id,
                'item_name': schedule.name,
                'purchased_at': datetime.now().isoformat(),
                'purchased_price': purchased_price,
                'order_id': order_id or 'N/A',
                'url': schedule.auto_purchase_url or schedule.auto_purchase_keyword
            }
            logs.append(log_entry)

            # Save logs
            log_file.write_text(
                json.dumps(logs, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
