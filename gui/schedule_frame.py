"""
Embedded schedule management frame.

Displays schedules with inline editing capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional

from gui.schedule_manager import ScheduleManager
from gui.schedule_dialog import ScheduleDialog
from gui.schedule_states import Schedule, ScheduleType


class ScheduleFrame(ttk.Frame):
    """Embedded schedule management frame with inline editing."""

    def __init__(self, parent, executor_ref):
        """
        Initialize schedule frame.

        Args:
            parent: Parent widget
            executor_ref: Reference to ScheduleExecutor instance
        """
        super().__init__(parent)
        self.executor = executor_ref
        self.manager = ScheduleManager()

        self._build_ui()
        self._load_schedules()

    def _build_ui(self):
        """Build the UI components."""
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
            "csv_newly_listed",
            "csv_in_stock",
            "csv_2nd_keyword"
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
        self.tree.column("start_time", width=100, minwidth=80)
        self.tree.column("next_run", width=150, minwidth=120)
        self.tree.column("end_date", width=100, minwidth=80)
        self.tree.column("configs", width=250, minwidth=150)
        self.tree.column("csv_newly_listed", width=80, minwidth=60)
        self.tree.column("csv_in_stock", width=80, minwidth=60)
        self.tree.column("csv_2nd_keyword", width=80, minwidth=60)

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
        self.tree.heading("csv_newly_listed", text="Newly Listed")
        self.tree.heading("csv_in_stock", text="In-Stock")
        self.tree.heading("csv_2nd_keyword", text="2nd Keyword")

        # Bind events
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_single_click)

        # Bottom controls (initially packed in self)
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(self.controls_frame, text="New Schedule", command=self._on_new_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text="Edit", command=self._on_edit_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text="Delete", command=self._on_delete_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(self.controls_frame, text="Run Now", command=self._on_run_now).pack(side=tk.LEFT, padx=2)

        # Status
        self.status_label = ttk.Label(self.controls_frame, text="")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # External button frame (for showing in parent)
        self.external_buttons_frame = None

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
        self.status_label.config(text=f"{len(schedules)} schedules ({active_count} active)")

    def _add_schedule_to_tree(self, schedule: Schedule):
        """Add a single schedule to the treeview."""
        # Format values
        active_str = "✓" if schedule.active else ""
        type_str = schedule.schedule_type.value.capitalize()
        frequency_str = f"{schedule.frequency_hours}h"
        days_str = schedule.get_display_days()
        start_time_str = schedule.start_time_pst

        # Format next run
        next_run_str = "-"
        if schedule.next_run:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(schedule.next_run)
                next_run_str = dt.strftime("%m/%d %H:%M")
            except (ValueError, AttributeError):
                next_run_str = schedule.next_run

        end_date_str = schedule.end_date if schedule.end_date else "-"

        # Format config files (show count)
        config_count = len(schedule.config_files)
        configs_str = f"{config_count} file(s)"

        # Format CSV options
        newly_listed_str = "✓" if schedule.csv_newly_listed else ""
        in_stock_str = "✓" if schedule.csv_in_stock else ""
        csv_2nd_keyword_str = "✓" if schedule.csv_2nd_keyword else ""

        values = (
            active_str,
            type_str,
            frequency_str,
            days_str,
            start_time_str,
            next_run_str,
            end_date_str,
            configs_str,
            newly_listed_str,
            in_stock_str,
            csv_2nd_keyword_str
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

    def _on_single_click(self, event):
        """Handle single click for inline editing of certain columns."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item:
            return

        # Get schedule
        tags = self.tree.item(item, "tags")
        if not tags:
            return
        schedule_id = int(tags[0])
        schedule = self.manager.storage.get_by_id(schedule_id)
        if not schedule:
            return

        # Column index to name mapping
        col_map = {
            "#1": "active",
            "#2": "type",
            "#3": "frequency",
            "#5": "start_time",
            "#9": "csv_newly_listed",
            "#10": "csv_in_stock",
            "#11": "csv_2nd_keyword"
        }

        col_name = col_map.get(column)
        if not col_name:
            return

        # Handle inline editing
        if col_name == "active":
            self._toggle_active_inline(schedule)
        elif col_name == "type":
            self._edit_type_inline(schedule, item)
        elif col_name == "frequency":
            self._edit_frequency_inline(schedule, item)
        elif col_name == "start_time":
            self._edit_start_time_inline(schedule, item)
        elif col_name == "csv_newly_listed":
            self._toggle_csv_newly_listed(schedule)
        elif col_name == "csv_in_stock":
            self._toggle_csv_in_stock(schedule)
        elif col_name == "csv_2nd_keyword":
            self._toggle_csv_2nd_keyword(schedule)

    def _on_double_click(self, event):
        """Handle double click - rename schedule or open full edit."""
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item:
            return

        # Get schedule
        tags = self.tree.item(item, "tags")
        if not tags:
            return
        schedule_id = int(tags[0])
        schedule = self.manager.storage.get_by_id(schedule_id)
        if not schedule:
            return

        # If double-click on name column, rename
        if column == "#0":
            self._rename_schedule(schedule, item)
        # Only open edit dialog on days (#4) or configs (#8) columns
        elif column in ("#4", "#8"):
            self._on_edit_schedule()

    def _toggle_active_inline(self, schedule: Schedule):
        """Toggle active state inline."""
        schedule.active = not schedule.active
        self.manager.update_schedule(schedule)
        self._load_schedules()

    def _toggle_csv_newly_listed(self, schedule: Schedule):
        """Toggle CSV newly listed filter."""
        schedule.csv_newly_listed = not schedule.csv_newly_listed
        self.manager.update_schedule(schedule)
        self._load_schedules()

    def _toggle_csv_in_stock(self, schedule: Schedule):
        """Toggle CSV in-stock filter."""
        schedule.csv_in_stock = not schedule.csv_in_stock
        self.manager.update_schedule(schedule)
        self._load_schedules()

    def _toggle_csv_2nd_keyword(self, schedule: Schedule):
        """Toggle CSV 2nd keyword."""
        schedule.csv_2nd_keyword = not schedule.csv_2nd_keyword
        self.manager.update_schedule(schedule)
        self._load_schedules()

    def _edit_type_inline(self, schedule: Schedule, item):
        """Edit type inline with dropdown."""
        # Get current type
        current = schedule.schedule_type.value

        # Create popup menu
        menu = tk.Menu(self.tree, tearoff=0)
        menu.add_command(label="Daily", command=lambda: self._set_type(schedule, "daily"))
        menu.add_command(label="Weekly", command=lambda: self._set_type(schedule, "weekly"))

        # Show menu at cursor
        x, y, _, _ = self.tree.bbox(item, "#2")
        menu.post(self.tree.winfo_rootx() + x, self.tree.winfo_rooty() + y)

    def _set_type(self, schedule: Schedule, type_val: str):
        """Set schedule type."""
        schedule.schedule_type = ScheduleType(type_val)
        self.manager.update_schedule(schedule)
        self._load_schedules()

    def _edit_frequency_inline(self, schedule: Schedule, item):
        """Edit frequency inline."""
        new_freq = simpledialog.askinteger(
            "Edit Frequency",
            "Enter frequency in hours:",
            initialvalue=schedule.frequency_hours,
            minvalue=1,
            maxvalue=168
        )
        if new_freq:
            schedule.frequency_hours = new_freq
            self.manager.update_schedule(schedule)
            self._load_schedules()

    def _edit_start_time_inline(self, schedule: Schedule, item):
        """Edit start time inline."""
        new_time = simpledialog.askstring(
            "Edit Start Time",
            "Enter start time (HH:MM):",
            initialvalue=schedule.start_time_pst
        )
        if new_time:
            schedule.start_time_pst = new_time
            self.manager.update_schedule(schedule)
            self._load_schedules()

    def _rename_schedule(self, schedule: Schedule, item):
        """Rename schedule."""
        # Create dialog at mouse position
        dialog = tk.Toplevel(self)
        dialog.title("Rename Schedule")

        # Position near mouse
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        dialog.geometry(f"300x150+{x+10}+{y+10}")

        # Make modal
        dialog.transient(self)
        dialog.grab_set()

        # Add label and entry
        ttk.Label(dialog, text="Enter new name:").pack(padx=10, pady=(10, 5))

        name_var = tk.StringVar(value=schedule.name)
        entry = ttk.Entry(dialog, textvariable=name_var, width=35)
        entry.pack(padx=10, pady=5)
        entry.select_range(0, tk.END)
        entry.focus_set()

        result = {"name": None}

        def on_ok():
            result["name"] = name_var.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

        # Bind Enter to OK
        entry.bind("<Return>", lambda e: on_ok())
        entry.bind("<Escape>", lambda e: on_cancel())

        self.wait_window(dialog)

        if result["name"]:
            schedule.name = result["name"]
            self.manager.update_schedule(schedule)
            self._load_schedules()

    def _on_new_schedule(self):
        """Handle new schedule button."""
        dialog = ScheduleDialog(self)
        self._position_dialog_near_mouse(dialog)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            created = self.manager.create_schedule(
                name=result.name,
                schedule_type=result.schedule_type,
                days=result.days,
                frequency_hours=result.frequency_hours,
                start_time_pst=result.start_time_pst,
                end_date=result.end_date,
                config_files=result.config_files,
                active=result.active
            )
            self._load_schedules()

    def _on_edit_schedule(self):
        """Handle edit schedule button."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select a schedule to edit")
            return

        if len(selected_items) > 1:
            messagebox.showinfo("Multiple Selection", "Please select only one schedule to edit")
            return

        # Get schedule
        item = selected_items[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            return

        schedule_id = int(tags[0])
        schedule = self.manager.storage.get_by_id(schedule_id)

        if not schedule:
            messagebox.showerror("Error", "Schedule not found")
            return

        # Open edit dialog near mouse pointer
        dialog = ScheduleDialog(self, schedule)
        self._position_dialog_near_mouse(dialog)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            self.manager.update_schedule(result)
            self._load_schedules()

    def _on_delete_schedule(self):
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

    def _on_run_now(self):
        """Handle run now button."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select a schedule to run")
            return

        if len(selected_items) > 1:
            messagebox.showinfo("Multiple Selection", "Please select only one schedule to run")
            return

        # Get schedule
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
            f"Schedule '{schedule.name}' is running in background.\n\n"
            f"Results will appear in the Alerts tab."
        )

    def show_buttons_in_parent(self, parent, row=10):
        """Show buttons in parent frame instead of self."""
        # Hide internal buttons
        self.controls_frame.pack_forget()

        # Create external button frame if needed
        if self.external_buttons_frame:
            self.external_buttons_frame.destroy()

        self.external_buttons_frame = ttk.Frame(parent)
        self.external_buttons_frame.grid(row=row, column=0, columnspan=5, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        ttk.Button(self.external_buttons_frame, text="New Schedule", command=self._on_new_schedule).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.external_buttons_frame, text="Edit", command=self._on_edit_schedule).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.external_buttons_frame, text="Delete", command=self._on_delete_schedule).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.external_buttons_frame, text="Run Now", command=self._on_run_now).pack(side=tk.LEFT, padx=5)

    def hide_buttons(self):
        """Hide external buttons and show internal buttons."""
        if self.external_buttons_frame:
            self.external_buttons_frame.grid_remove()

        # Show internal buttons
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)

    def _position_dialog_near_mouse(self, dialog):
        """Position dialog in center of main window."""
        # Update dialog to get accurate size
        dialog.update_idletasks()

        # Get main window (root) position and size
        root = self.winfo_toplevel()
        root_x = root.winfo_x()
        root_y = root.winfo_y()
        root_width = root.winfo_width()
        root_height = root.winfo_height()

        # Get dialog size
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        # Calculate center position
        x = root_x + (root_width - dialog_width) // 2
        y = root_y + (root_height - dialog_height) // 2

        # Position dialog
        dialog.geometry(f"+{x}+{y}")
