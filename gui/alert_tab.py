"""
Alert/Review tab UI - displays alerts in a treeview with bulk actions.

This tab shows comparison results that meet similarity/profit thresholds
and allows users to manage the reselling workflow.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from typing import Callable, Dict, List, Optional

from gui.alert_manager import AlertManager
from gui.alert_states import (
    AlertState,
    AlertBulkActions,
    get_state_color,
    get_state_display_name
)


class AlertTab(ttk.Frame):
    """Alert/Review tab for managing items through reselling workflow."""

    def __init__(self, parent):
        """
        Initialize Alert tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.alert_manager = AlertManager()
        self.selected_alert_ids = []

        # Threshold variables
        self.min_similarity_var = tk.DoubleVar(value=70.0)
        self.min_profit_var = tk.DoubleVar(value=20.0)

        # UI state
        self.state_filter_var = tk.StringVar(value="all")

        self._build_ui()
        self._load_alerts()

    def _build_ui(self):
        """Build the UI components."""
        # Top controls frame - everything on the left
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        # All filters on the left side
        filters_frame = ttk.LabelFrame(controls_frame, text="Filters:", padding=5)
        filters_frame.pack(side=tk.LEFT, padx=(0, 5))

        # State filter
        ttk.Label(filters_frame, text="State:").pack(side=tk.LEFT, padx=5)
        state_combo = ttk.Combobox(
            filters_frame,
            textvariable=self.state_filter_var,
            values=["all", "pending", "yay", "nay", "purchased", "shipped", "received", "posted", "sold"],
            state="readonly",
            width=12
        )
        state_combo.pack(side=tk.LEFT, padx=5)
        state_combo.bind("<<ComboboxSelected>>", lambda e: self._load_alerts())

        # Separator
        ttk.Separator(filters_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Similarity filter
        ttk.Label(filters_frame, text="Min Similarity %:").pack(side=tk.LEFT, padx=5)
        similarity_spinbox = ttk.Spinbox(
            filters_frame,
            from_=0,
            to=100,
            textvariable=self.min_similarity_var,
            width=8
        )
        similarity_spinbox.pack(side=tk.LEFT, padx=5)
        self.min_similarity_var.trace_add("write", lambda *args: self._load_alerts())

        # Profit filter
        ttk.Label(filters_frame, text="Min Profit %:").pack(side=tk.LEFT, padx=5)
        profit_spinbox = ttk.Spinbox(
            filters_frame,
            from_=-100,
            to=1000,
            textvariable=self.min_profit_var,
            width=8
        )
        profit_spinbox.pack(side=tk.LEFT, padx=5)
        self.min_profit_var.trace_add("write", lambda *args: self._load_alerts())

        # Refresh button
        ttk.Button(filters_frame, text="Refresh", command=self._load_alerts).pack(side=tk.LEFT, padx=10)

        # Bulk actions frame
        actions_frame = ttk.Frame(self)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(actions_frame, text="Bulk Actions:").pack(side=tk.LEFT, padx=5)

        # Action buttons
        ttk.Button(actions_frame, text="Mark Yay", command=lambda: self._bulk_action("yay")).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Mark Nay", command=lambda: self._bulk_action("nay")).pack(side=tk.LEFT, padx=2)
        ttk.Separator(actions_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(actions_frame, text="Purchase", command=lambda: self._bulk_action("purchased")).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Shipped", command=lambda: self._bulk_action("shipped")).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Received", command=lambda: self._bulk_action("received")).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Posted", command=lambda: self._bulk_action("posted")).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Sold", command=lambda: self._bulk_action("sold")).pack(side=tk.LEFT, padx=2)

        ttk.Separator(actions_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(actions_frame, text="Delete Selected", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

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
            "state",
            "similarity",
            "profit",
            "mandarake_title",
            "ebay_title",
            "mandarake_price",
            "ebay_price",
            "shipping",
            "sold_date"
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
        self.tree.column("#0", width=50, minwidth=50)  # ID column
        self.tree.column("state", width=100, minwidth=80)
        self.tree.column("similarity", width=80, minwidth=60)
        self.tree.column("profit", width=80, minwidth=60)
        self.tree.column("mandarake_title", width=250, minwidth=150)
        self.tree.column("ebay_title", width=250, minwidth=150)
        self.tree.column("mandarake_price", width=100, minwidth=80)
        self.tree.column("ebay_price", width=80, minwidth=60)
        self.tree.column("shipping", width=80, minwidth=60)
        self.tree.column("sold_date", width=100, minwidth=80)

        # Headings
        self.tree.heading("#0", text="ID")
        self.tree.heading("state", text="State")
        self.tree.heading("similarity", text="Similarity %")
        self.tree.heading("profit", text="Profit %")
        self.tree.heading("mandarake_title", text="Mandarake Title")
        self.tree.heading("ebay_title", text="eBay Title")
        self.tree.heading("mandarake_price", text="Mandarake Price")
        self.tree.heading("ebay_price", text="eBay Price")
        self.tree.heading("shipping", text="Shipping")
        self.tree.heading("sold_date", text="Sold Date")

        # Bind events
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="No alerts loaded")
        self.status_label.pack(side=tk.LEFT)

    def _load_alerts(self):
        """Load alerts from storage and populate treeview with filters applied."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get state filter
        state_filter_str = self.state_filter_var.get()
        state_filter = None
        if state_filter_str != "all":
            try:
                state_filter = AlertState(state_filter_str)
            except ValueError:
                pass

        # Load alerts
        if state_filter:
            alerts = self.alert_manager.get_alerts_by_state(state_filter)
        else:
            alerts = self.alert_manager.get_all_alerts()

        # Apply similarity and profit filters (for display only)
        try:
            min_similarity = self.min_similarity_var.get()
            min_profit = self.min_profit_var.get()

            filtered_alerts = [
                alert for alert in alerts
                if alert.get('similarity', 0) >= min_similarity and
                   alert.get('profit_margin', 0) >= min_profit
            ]
        except:
            # If filter values are invalid, show all
            filtered_alerts = alerts

        # Sort by ID (most recent first)
        filtered_alerts.sort(key=lambda x: x.get('alert_id', 0), reverse=True)

        # Populate treeview
        for alert in filtered_alerts:
            self._add_alert_to_tree(alert)

        # Update status
        if len(filtered_alerts) < len(alerts):
            self.status_label.config(text=f"Showing {len(filtered_alerts)} of {len(alerts)} alerts (filtered)")
        else:
            self.status_label.config(text=f"Loaded {len(alerts)} alerts")

    def _add_alert_to_tree(self, alert: Dict):
        """Add a single alert to the treeview."""
        alert_id = alert.get('alert_id', 0)
        state = alert.get('state', AlertState.PENDING)

        # Format values
        similarity = alert.get('similarity', 0)
        similarity_str = f"{similarity:.1f}%" if similarity > 0 else "-"

        profit = alert.get('profit_margin', 0)
        profit_str = f"{profit:.1f}%" if profit != 0 else "-"

        values = (
            get_state_display_name(state),
            similarity_str,
            profit_str,
            alert.get('mandarake_title', 'N/A'),
            alert.get('ebay_title', 'N/A'),
            alert.get('mandarake_price', '¥0'),
            alert.get('ebay_price', '$0'),
            alert.get('shipping', '$0'),
            alert.get('sold_date', '')
        )

        # Insert item
        item_id = self.tree.insert("", "end", text=str(alert_id), values=values, tags=(state.value,))

        # Color-code by state
        color = get_state_color(state)
        self.tree.tag_configure(state.value, background=color)

    def _bulk_action(self, action: str):
        """
        Perform bulk action on selected items.

        Args:
            action: Action name (yay, nay, purchased, shipped, etc.)
        """
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select items to perform bulk action")
            return

        # Get alert IDs
        alert_ids = [int(self.tree.item(item, "text")) for item in selected_items]

        # Map action to state
        state_map = {
            "yay": AlertState.YAY,
            "nay": AlertState.NAY,
            "purchased": AlertState.PURCHASED,
            "shipped": AlertState.SHIPPED,
            "received": AlertState.RECEIVED,
            "posted": AlertState.POSTED,
            "sold": AlertState.SOLD
        }

        new_state = state_map.get(action)
        if not new_state:
            return

        # Confirm action
        state_name = get_state_display_name(new_state)
        if not messagebox.askyesno("Confirm", f"Mark {len(alert_ids)} items as '{state_name}'?"):
            return

        # Perform bulk update
        success_count = self.alert_manager.bulk_update_state(alert_ids, new_state)

        # Reload
        self._load_alerts()
        messagebox.showinfo("Success", f"Updated {success_count} alerts to '{state_name}'")

    def _delete_selected(self):
        """Delete selected alerts."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select items to delete")
            return

        alert_ids = [int(self.tree.item(item, "text")) for item in selected_items]

        if not messagebox.askyesno("Confirm Delete", f"Delete {len(alert_ids)} alerts? This cannot be undone."):
            return

        self.alert_manager.delete_alerts(alert_ids)
        self._load_alerts()
        messagebox.showinfo("Success", f"Deleted {len(alert_ids)} alerts")

    def _on_double_click(self, event):
        """Handle double-click on alert item - open links."""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        alert_id = int(self.tree.item(item, "text"))
        alert = self.alert_manager.storage.get_alert_by_id(alert_id)

        if not alert:
            return

        # Ask which link to open
        choice = messagebox.askquestion(
            "Open Link",
            f"Alert #{alert_id}\n\nWhich link would you like to open?",
            icon='question',
            type=messagebox.YESNOCANCEL
        )

        if choice == 'yes':  # Open Mandarake
            link = alert.get('mandarake_link', '')
            if link:
                webbrowser.open(link)
        elif choice == 'no':  # Open eBay
            link = alert.get('ebay_link', '')
            if link:
                webbrowser.open(link)

    def _on_right_click(self, event):
        """Handle right-click - show context menu."""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Create context menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Open Mandarake Link", command=lambda: self._open_mandarake_link(item))
        menu.add_command(label="Open eBay Link", command=lambda: self._open_ebay_link(item))
        menu.add_separator()
        menu.add_command(label="Mark as Yay", command=lambda: self._quick_action(item, AlertState.YAY))
        menu.add_command(label="Mark as Nay", command=lambda: self._quick_action(item, AlertState.NAY))
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: self._delete_item(item))

        menu.post(event.x_root, event.y_root)

    def _open_mandarake_link(self, item):
        """Open Mandarake link for item."""
        alert_id = int(self.tree.item(item, "text"))
        alert = self.alert_manager.storage.get_alert_by_id(alert_id)
        if alert and alert.get('mandarake_link'):
            webbrowser.open(alert['mandarake_link'])

    def _open_ebay_link(self, item):
        """Open eBay link for item."""
        alert_id = int(self.tree.item(item, "text"))
        alert = self.alert_manager.storage.get_alert_by_id(alert_id)
        if alert and alert.get('ebay_link'):
            webbrowser.open(alert['ebay_link'])

    def _quick_action(self, item, state: AlertState):
        """Quick action from context menu."""
        alert_id = int(self.tree.item(item, "text"))
        self.alert_manager.update_alert_state(alert_id, state)
        self._load_alerts()

    def _delete_item(self, item):
        """Delete single item."""
        alert_id = int(self.tree.item(item, "text"))
        if messagebox.askyesno("Confirm Delete", f"Delete alert #{alert_id}?"):
            self.alert_manager.delete_alerts([alert_id])
            self._load_alerts()

    def add_filtered_alerts(self, comparison_results: List[Dict]):
        """
        Add pre-filtered comparison results to alerts.

        Called from eBay Search tab with results already filtered by thresholds.

        Args:
            comparison_results: List of comparison result dictionaries (already filtered)
        """
        # Process results without applying additional thresholds (already filtered)
        created_alerts = self.alert_manager.process_comparison_results(
            comparison_results,
            min_similarity=0,  # No additional filtering
            min_profit=-999999  # No additional filtering
        )

        # Reload alerts to show new ones
        self._load_alerts()
