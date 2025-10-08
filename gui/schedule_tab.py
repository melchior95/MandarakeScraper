"""
Schedule management tab UI.

Displays list of schedules and provides management controls.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional, TYPE_CHECKING

from gui.schedule_manager import ScheduleManager
from gui.schedule_dialog import ScheduleDialog
from gui.schedule_states import Schedule

if TYPE_CHECKING:
    from gui.schedule_executor import ScheduleExecutor


class ScheduleTab(ttk.Frame):
    """Schedule management tab."""

    def __init__(self, parent: ttk.Notebook, executor_ref: 'ScheduleExecutor') -> None:
        """
        Initialize schedule tab.

        Args:
            parent: Parent widget
            executor_ref: Reference to ScheduleExecutor instance
        """
        super().__init__(parent)
        self.executor = executor_ref
        self.manager = ScheduleManager()

        self._build_ui()
        self._load_schedules()

    def _build_ui(self) -> None:
        """Build the UI components."""
        # Top controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(controls_frame, text="Schedules:").pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(controls_frame, text="New Schedule", command=self._on_new_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Edit", command=self._on_edit_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Delete", command=self._on_delete_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Separator(controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(controls_frame, text="Activate", command=lambda: self._on_toggle_active(True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Deactivate", command=lambda: self._on_toggle_active(False)).pack(side=tk.LEFT, padx=2)
        ttk.Separator(controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(controls_frame, text="Run Now", command=self._on_run_now).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Refresh", command=self._load_schedules).pack(side=tk.LEFT, padx=2)

        # Treeview frame
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview columns
        columns = (
            "active",
            "type",
            "frequency",
            "days",
            "start_time",
            "next_run",
            "end_date",
            "configs",
            "auto_purchase",
            "last_price",
            "max_price",
            "last_check"
        )

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            selectmode="extended",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)

        # Configure columns
        self.tree.column("#0", width=200, minwidth=150)  # Name column
        self.tree.column("active", width=60, minwidth=50)
        self.tree.column("type", width=80, minwidth=60)
        self.tree.column("frequency", width=100, minwidth=80)
        self.tree.column("days", width=150, minwidth=100)
        self.tree.column("start_time", width=80, minwidth=60)
        self.tree.column("next_run", width=150, minwidth=120)
        self.tree.column("end_date", width=100, minwidth=80)
        self.tree.column("configs", width=250, minwidth=150)
        self.tree.column("auto_purchase", width=120, minwidth=100)
        self.tree.column("last_price", width=90, minwidth=70)
        self.tree.column("max_price", width=90, minwidth=70)
        self.tree.column("last_check", width=120, minwidth=100)

        # Headings
        self.tree.heading("#0", text="Name")
        self.tree.heading("active", text="Active")
        self.tree.heading("type", text="Type")
        self.tree.heading("frequency", text="Frequency")
        self.tree.heading("days", text="Days")
        self.tree.heading("start_time", text="Start Time")
        self.tree.heading("next_run", text="Next Run")
        self.tree.heading("end_date", text="End Date")
        self.tree.heading("configs", text="Config Files")
        self.tree.heading("auto_purchase", text="Auto-Purchase")
        self.tree.heading("last_price", text="Last Price")
        self.tree.heading("max_price", text="Max Price")
        self.tree.heading("last_check", text="Last Check")

        # Bind events
        self.tree.bind("<Double-Button-1>", lambda e: self._on_edit_schedule())

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="No schedules loaded")
        self.status_label.pack(side=tk.LEFT)

    def _load_schedules(self):
        """Load schedules from storage and populate treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load schedules
        schedules = self.manager.get_all_schedules()

        # Sort by ID (most recent first)
        schedules.sort(key=lambda x: x.schedule_id, reverse=True)

        # Populate treeview
        for schedule in schedules:
            self._add_schedule_to_tree(schedule)

        # Update status
        active_count = len([s for s in schedules if s.active])
        self.status_label.config(
            text=f"Loaded {len(schedules)} schedules ({active_count} active)"
        )

    def _load_schedules(self) -> None:
        """Load schedules from storage and populate treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load schedules
        schedules = self.manager.get_all_schedules()

        # Sort by ID (most recent first)
        schedules.sort(key=lambda x: x.schedule_id, reverse=True)

        # Populate treeview
        for schedule in schedules:
            self._add_schedule_to_tree(schedule)

        # Update status
        active_count = len([s for s in schedules if s.active])
        self.status_label.config(
            text=f"Loaded {len(schedules)} schedules ({active_count} active)"
        )

    def _add_schedule_to_tree(self, schedule: Schedule) -> None:
        """Add a single schedule to the treeview."""
        # Format values
        active_str = "Yes" if schedule.active else "No"
        type_str = schedule.schedule_type.value.capitalize()
        frequency_str = f"Every {schedule.frequency_hours}h"
        days_str = schedule.get_display_days()
        start_time_str = f"{schedule.start_time_pst} PST"

        # Format next run
        next_run_str = "Not scheduled"
        if schedule.next_run:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(schedule.next_run)
                next_run_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                next_run_str = schedule.next_run

        end_date_str = schedule.end_date if schedule.end_date else "No end"

        # Format config files (show count)
        config_count = len(schedule.config_files)
        configs_str = f"{config_count} config(s)"

        # Format auto-purchase columns
        if schedule.auto_purchase_enabled:
            auto_purchase_str = "Monitoring..." if schedule.active else "Disabled"
            last_price_str = f"¥{schedule.auto_purchase_last_price:,}" if schedule.auto_purchase_last_price else "-"
            max_price_str = f"¥{schedule.auto_purchase_max_price:,}" if schedule.auto_purchase_max_price else "-"

            # Format last check time
            if schedule.auto_purchase_last_check:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(schedule.auto_purchase_last_check)
                    last_check_str = dt.strftime("%m-%d %H:%M")
                except (ValueError, AttributeError):
                    last_check_str = "-"
            else:
                last_check_str = "Never"
        else:
            auto_purchase_str = "-"
            last_price_str = "-"
            max_price_str = "-"
            last_check_str = "-"

        values = (
            active_str,
            type_str,
            frequency_str,
            days_str,
            start_time_str,
            next_run_str,
            end_date_str,
            configs_str,
            auto_purchase_str,
            last_price_str,
            max_price_str,
            last_check_str
        )

        # Insert item
        item_id = self.tree.insert("", "end", text=schedule.name, values=values)

        # Store schedule ID as tag
        self.tree.item(item_id, tags=(str(schedule.schedule_id),))

        # Color-code active/inactive
        if schedule.active:
            self.tree.item(item_id, tags=(str(schedule.schedule_id), "active"))
        else:
            self.tree.item(item_id, tags=(str(schedule.schedule_id), "inactive"))

        # Configure tags
        self.tree.tag_configure("active", background="#e8f5e9")  # Light green
        self.tree.tag_configure("inactive", background="#f5f5f5")  # Light gray

    def _on_new_schedule(self) -> None:
        """Handle new schedule button."""
        dialog = ScheduleDialog(self)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            # Create schedule
            created = self.manager.create_schedule(
                name=result.name,
                schedule_type=result.schedule_type,
                days=result.days,
                frequency_hours=result.frequency_hours,
                start_time_pst=result.start_time_pst,
                end_date=result.end_date,
                config_files=result.config_files,
                active=result.active,
                comparison_method=result.comparison_method
            )
            self._load_schedules()
            messagebox.showinfo("Success", f"Created schedule: {created.name}")

    def _on_edit_schedule(self) -> None:
        """Handle edit schedule button."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select a schedule to edit")
            return

        if len(selected_items) > 1:
            messagebox.showinfo("Multiple Selection", "Please select only one schedule to edit")
            return

        # Get schedule ID from tags
        item = selected_items[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            return

        schedule_id = int(tags[0])
        schedule = self.manager.storage.get_by_id(schedule_id)

        if not schedule:
            messagebox.showerror("Error", "Schedule not found")
            return

        # Open edit dialog
        dialog = ScheduleDialog(self, schedule)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            self.manager.update_schedule(result)
            self._load_schedules()
            messagebox.showinfo("Success", f"Updated schedule: {result.name}")

    def _on_delete_schedule(self) -> None:
        """Handle delete schedule button."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select schedule(s) to delete")
            return

        # Get schedule IDs
        schedule_ids = []
        for item in selected_items:
            tags = self.tree.item(item, "tags")
            if tags:
                schedule_ids.append(int(tags[0]))

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(schedule_ids)} schedule(s)? This cannot be undone."
        ):
            return

        # Delete schedules
        for schedule_id in schedule_ids:
            self.manager.delete_schedule(schedule_id)

        self._load_schedules()
        messagebox.showinfo("Success", f"Deleted {len(schedule_ids)} schedule(s)")

    def _on_toggle_active(self, active: bool) -> None:
        """Handle activate/deactivate button."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select schedule(s) to toggle")
            return

        # Get schedule IDs
        schedule_ids = []
        for item in selected_items:
            tags = self.tree.item(item, "tags")
            if tags:
                schedule_ids.append(int(tags[0]))

        # Toggle active state
        for schedule_id in schedule_ids:
            self.manager.toggle_active(schedule_id, active)

        self._load_schedules()
        action = "Activated" if active else "Deactivated"
        messagebox.showinfo("Success", f"{action} {len(schedule_ids)} schedule(s)")

    def _on_run_now(self) -> None:
        """Handle run now button - manually trigger schedule execution."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select a schedule to run")
            return

        if len(selected_items) > 1:
            messagebox.showinfo("Multiple Selection", "Please select only one schedule to run")
            return

        # Get schedule ID
        item = selected_items[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            return

        schedule_id = int(tags[0])
        schedule = self.manager.storage.get_by_id(schedule_id)

        if not schedule:
            messagebox.showerror("Error", "Schedule not found")
            return

        if not messagebox.askyesno(
            "Confirm Run",
            f"Run schedule '{schedule.name}' now?\n\n"
            f"This will process {len(schedule.config_files)} config file(s)."
        ):
            return

        # Execute schedule
        self.executor.execute_schedule_now(schedule_id)
        messagebox.showinfo(
            "Running",
            f"Schedule '{schedule.name}' is now executing in the background.\n\n"
            f"Results will appear in the Alerts tab as they complete."
        )
