"""
Schedule creation/editing dialog.

Provides UI for creating and editing schedules.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from gui.schedule_states import Schedule, ScheduleType


class ScheduleDialog(tk.Toplevel):
    """Dialog for creating/editing schedules."""

    def __init__(self, parent, schedule: Optional[Schedule] = None):
        """
        Initialize dialog.

        Args:
            parent: Parent window
            schedule: Existing schedule to edit, or None for new
        """
        super().__init__(parent)
        self.title("Edit Schedule" if schedule else "New Schedule")
        self.geometry("600x700")
        self.resizable(False, False)

        self.schedule = schedule
        self.result: Optional[Schedule] = None

        # Variables
        self.name_var = tk.StringVar(value=schedule.name if schedule else "")
        self.active_var = tk.BooleanVar(value=schedule.active if schedule else True)
        self.type_var = tk.StringVar(value=schedule.schedule_type.value if schedule else "daily")
        self.frequency_var = tk.IntVar(value=schedule.frequency_hours if schedule else 24)
        self.start_time_var = tk.StringVar(value=schedule.start_time_pst if schedule else "09:00")
        self.end_date_var = tk.StringVar(value=schedule.end_date if schedule else "")

        # Day checkboxes
        self.day_vars = {
            'SU': tk.BooleanVar(),
            'MO': tk.BooleanVar(),
            'TU': tk.BooleanVar(),
            'WE': tk.BooleanVar(),
            'TH': tk.BooleanVar(),
            'FR': tk.BooleanVar(),
            'SA': tk.BooleanVar()
        }

        # Set selected days if editing
        if schedule and schedule.days:
            for day in schedule.days:
                if day in self.day_vars:
                    self.day_vars[day].set(True)

        self._build_ui()
        self._load_available_configs()

        # Select config files if editing
        if schedule and schedule.config_files:
            self._select_config_files(schedule.config_files)

        # Make modal
        self.transient(parent)
        self.grab_set()

    def _build_ui(self):
        """Build the dialog UI."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Name and active toggle
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(name_frame, textvariable=self.name_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Checkbutton(name_frame, text="Active", variable=self.active_var).pack(side=tk.LEFT, padx=(10, 0))

        # Repeats section
        repeats_frame = ttk.LabelFrame(main_frame, text="REPEATS", padding=10)
        repeats_frame.pack(fill=tk.X, pady=(0, 10))

        # Daily/Weekly buttons
        type_frame = ttk.Frame(repeats_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Radiobutton(
            type_frame,
            text="Daily",
            variable=self.type_var,
            value="daily",
            command=self._on_type_changed
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Radiobutton(
            type_frame,
            text="Weekly",
            variable=self.type_var,
            value="weekly",
            command=self._on_type_changed
        ).pack(side=tk.LEFT)

        # Weekly days (only visible for weekly)
        self.weekly_frame = ttk.LabelFrame(repeats_frame, text="OCCURS ON", padding=10)

        days_grid = ttk.Frame(self.weekly_frame)
        days_grid.pack(fill=tk.X)

        day_labels = [
            ('SU', 'SU'), ('MO', 'MO'), ('TU', 'TU'), ('WE', 'WE'),
            ('TH', 'TH'), ('FR', 'FR'), ('SA', 'SA')
        ]

        for i, (code, label) in enumerate(day_labels):
            ttk.Checkbutton(
                days_grid,
                text=label,
                variable=self.day_vars[code]
            ).grid(row=0, column=i, padx=5)

        # Frequency section
        freq_frame = ttk.Frame(repeats_frame)
        freq_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(freq_frame, text="EVERY").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(
            freq_frame,
            from_=1,
            to=168,
            textvariable=self.frequency_var,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(freq_frame, text="hour(s)").pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(freq_frame, text="Starts on:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(freq_frame, textvariable=self.start_time_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(freq_frame, text="PST (HH:MM)").pack(side=tk.LEFT)

        # End date section
        end_frame = ttk.Frame(repeats_frame)
        end_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(end_frame, text="ENDS ON").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(end_frame, textvariable=self.end_date_var, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(end_frame, text="(YYYY-MM-DD, leave empty for no end)").pack(side=tk.LEFT)

        # Config files section
        configs_frame = ttk.LabelFrame(main_frame, text="CONFIG FILES TO RUN (in order)", padding=10)
        configs_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Split into two columns: available and selected
        cols_frame = ttk.Frame(configs_frame)
        cols_frame.pack(fill=tk.BOTH, expand=True)

        # Available configs (left)
        avail_frame = ttk.Frame(cols_frame)
        avail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Label(avail_frame, text="Available Configs:").pack()

        avail_scroll = ttk.Scrollbar(avail_frame)
        avail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.available_listbox = tk.Listbox(
            avail_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=avail_scroll.set,
            height=12
        )
        self.available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        avail_scroll.config(command=self.available_listbox.yview)

        # Middle buttons
        middle_frame = ttk.Frame(cols_frame)
        middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Label(middle_frame, text="").pack(pady=40)  # Spacer
        ttk.Button(middle_frame, text="Add →", command=self._add_configs).pack(pady=2)
        ttk.Button(middle_frame, text="← Remove", command=self._remove_configs).pack(pady=2)
        ttk.Button(middle_frame, text="Move Up", command=self._move_up).pack(pady=2)
        ttk.Button(middle_frame, text="Move Down", command=self._move_down).pack(pady=2)

        # Selected configs (right)
        selected_frame = ttk.Frame(cols_frame)
        selected_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ttk.Label(selected_frame, text="Selected Configs (in order):").pack()

        selected_scroll = ttk.Scrollbar(selected_frame)
        selected_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.config_listbox = tk.Listbox(
            selected_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=selected_scroll.set,
            height=12
        )
        self.config_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        selected_scroll.config(command=self.config_listbox.yview)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT)

        # Initial state
        self._on_type_changed()

    def _on_type_changed(self):
        """Handle type radio button change."""
        if self.type_var.get() == "weekly":
            self.weekly_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            self.weekly_frame.pack_forget()

    def _load_available_configs(self):
        """Load available config files from configs/ directory."""
        configs_dir = Path("configs")
        if not configs_dir.exists():
            return

        # Get all JSON files
        config_files = sorted([f.name for f in configs_dir.glob("*.json")])

        # Populate available listbox
        for config_file in config_files:
            self.available_listbox.insert(tk.END, config_file)

    def _select_config_files(self, config_files: List[str]):
        """
        Add config files to selected listbox in order.

        Args:
            config_files: List of config filenames to select
        """
        for config_file in config_files:
            self.config_listbox.insert(tk.END, config_file)

    def _add_configs(self):
        """Add selected configs from available to selected list."""
        selected = self.available_listbox.curselection()
        for idx in selected:
            config = self.available_listbox.get(idx)
            # Don't add duplicates
            if config not in self.config_listbox.get(0, tk.END):
                self.config_listbox.insert(tk.END, config)

    def _remove_configs(self):
        """Remove selected configs from selected list."""
        selected = self.config_listbox.curselection()
        # Delete in reverse to maintain indices
        for idx in reversed(selected):
            self.config_listbox.delete(idx)

    def _move_up(self):
        """Move selected config up in order."""
        selected = self.config_listbox.curselection()
        if not selected or selected[0] == 0:
            return

        for idx in selected:
            if idx > 0:
                item = self.config_listbox.get(idx)
                self.config_listbox.delete(idx)
                self.config_listbox.insert(idx - 1, item)
                self.config_listbox.selection_set(idx - 1)

    def _move_down(self):
        """Move selected config down in order."""
        selected = self.config_listbox.curselection()
        if not selected or selected[-1] >= self.config_listbox.size() - 1:
            return

        for idx in reversed(selected):
            if idx < self.config_listbox.size() - 1:
                item = self.config_listbox.get(idx)
                self.config_listbox.delete(idx)
                self.config_listbox.insert(idx + 1, item)
                self.config_listbox.selection_set(idx + 1)

    def _on_save(self):
        """Handle save button click."""
        # Validate inputs
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Please enter a schedule name")
            return

        # Get schedule type
        schedule_type = ScheduleType(self.type_var.get())

        # Get selected days (for weekly)
        selected_days = []
        if schedule_type == ScheduleType.WEEKLY:
            selected_days = [day for day, var in self.day_vars.items() if var.get()]
            if not selected_days:
                messagebox.showerror("Validation Error", "Please select at least one day for weekly schedule")
                return

        # Validate frequency
        frequency = self.frequency_var.get()
        if frequency < 1:
            messagebox.showerror("Validation Error", "Frequency must be at least 1 hour")
            return

        # Validate start time format
        start_time = self.start_time_var.get().strip()
        if not self._validate_time_format(start_time):
            messagebox.showerror("Validation Error", "Start time must be in HH:MM format (e.g., 09:00)")
            return

        # Validate end date format
        end_date = self.end_date_var.get().strip()
        if end_date and not self._validate_date_format(end_date):
            messagebox.showerror("Validation Error", "End date must be in YYYY-MM-DD format (e.g., 2025-02-21)")
            return

        # Get config files from listbox
        config_files = list(self.config_listbox.get(0, tk.END))
        if not config_files:
            messagebox.showerror("Validation Error", "Please add at least one config file")
            return

        # Create/update schedule object
        if self.schedule:
            # Editing existing schedule
            self.schedule.name = name
            self.schedule.active = self.active_var.get()
            self.schedule.schedule_type = schedule_type
            self.schedule.days = selected_days
            self.schedule.frequency_hours = frequency
            self.schedule.start_time_pst = start_time
            self.schedule.end_date = end_date if end_date else None
            self.schedule.config_files = config_files
            self.result = self.schedule
        else:
            # Creating new schedule
            self.result = Schedule(
                schedule_id=0,  # Will be assigned by storage
                name=name,
                active=self.active_var.get(),
                schedule_type=schedule_type,
                days=selected_days,
                frequency_hours=frequency,
                start_time_pst=start_time,
                end_date=end_date if end_date else None,
                config_files=config_files
            )

        self.destroy()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def _validate_time_format(self, time_str: str) -> bool:
        """Validate HH:MM format."""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            hour, minute = map(int, parts)
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError):
            return False

    def _validate_date_format(self, date_str: str) -> bool:
        """Validate YYYY-MM-DD format."""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def get_result(self) -> Optional[Schedule]:
        """
        Get the dialog result.

        Returns:
            Schedule if saved, None if cancelled
        """
        return self.result
