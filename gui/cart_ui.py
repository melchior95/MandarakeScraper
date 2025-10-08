"""
Cart UI Components

Dialog windows for cart management in the Alert tab.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Callable


class ThresholdWarningDialog:
    """Dialog to warn about shops below minimum threshold."""

    def __init__(self, parent, warnings: List[Dict], on_proceed: Callable, on_cancel: Callable):
        """
        Initialize threshold warning dialog.

        Args:
            parent: Parent window
            warnings: List of warning dicts with shop info
            on_proceed: Callback to call when user proceeds anyway
            on_cancel: Callback to call when user cancels
        """
        self.result = False
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Cart Threshold Warning")
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.on_proceed = on_proceed
        self.on_cancel = on_cancel

        self._build_ui(warnings)

        # Position at cursor
        from gui.ui_helpers import position_dialog_at_cursor
        position_dialog_at_cursor(self.dialog)

    def _build_ui(self, warnings: List[Dict]):
        """Build dialog UI."""
        # Header
        header_frame = ttk.Frame(self.dialog, padding=10)
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame,
            text="⚠️ Some shops are below minimum threshold",
            font=("", 12, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            header_frame,
            text="The following shops have cart totals below the minimum order value.\n"
                 "You may incur additional shipping costs or may not be able to checkout.",
            wraplength=550
        ).pack(anchor=tk.W, pady=(5, 0))

        # Warnings list
        list_frame = ttk.Frame(self.dialog, padding=(10, 0, 10, 10))
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        columns = ("shop", "current", "minimum", "shortage")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)

        tree.heading("shop", text="Shop")
        tree.heading("current", text="Current Total")
        tree.heading("minimum", text="Minimum Required")
        tree.heading("shortage", text="Shortage")

        tree.column("shop", width=200)
        tree.column("current", width=120, anchor=tk.E)
        tree.column("minimum", width=120, anchor=tk.E)
        tree.column("shortage", width=120, anchor=tk.E)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate warnings
        for warning in warnings:
            shop_name = warning['shop_name']
            current = f"¥{warning['total']:,}"
            minimum = f"¥{warning['threshold']:,}"
            shortage = f"¥{warning['threshold'] - warning['total']:,}"

            tree.insert("", tk.END, values=(shop_name, current, minimum, shortage))

        # Buttons
        button_frame = ttk.Frame(self.dialog, padding=10)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Add Anyway",
            command=self._on_proceed
        ).pack(side=tk.RIGHT)

        # Bind close button
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_proceed(self):
        """User chose to proceed anyway."""
        self.result = True
        self.dialog.destroy()
        if self.on_proceed:
            self.on_proceed()

    def _on_cancel(self):
        """User cancelled."""
        self.result = False
        self.dialog.destroy()
        if self.on_cancel:
            self.on_cancel()


class CartProgressDialog:
    """Progress dialog for adding items to cart."""

    def __init__(self, parent, total_items: int):
        """
        Initialize progress dialog.

        Args:
            parent: Parent window
            total_items: Total number of items to add
        """
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Adding Items to Cart")
        self.dialog.geometry("500x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.total_items = total_items
        self.cancelled = False

        self._build_ui()

        # Position at cursor
        from gui.ui_helpers import position_dialog_at_cursor
        position_dialog_at_cursor(self.dialog)

        # Prevent closing
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Preparing...",
            font=("", 10)
        )
        self.status_label.pack(pady=(0, 10))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(0, 5))

        # Progress text (X of Y)
        self.progress_text = ttk.Label(main_frame, text=f"0 of {self.total_items}")
        self.progress_text.pack()

        # Cancel button
        self.cancel_btn = ttk.Button(main_frame, text="Cancel", command=self._on_cancel)
        self.cancel_btn.pack(pady=(15, 0))

    def update_progress(self, current: int, total: int, message: str):
        """
        Update progress.

        Args:
            current: Current item number
            total: Total items
            message: Status message
        """
        if self.cancelled:
            return

        # Update progress bar
        percent = (current / total * 100) if total > 0 else 0
        self.progress_var.set(percent)

        # Update labels
        self.status_label.config(text=message)
        self.progress_text.config(text=f"{current} of {total}")

        # Force update
        self.dialog.update()

    def _on_cancel(self):
        """User cancelled operation."""
        self.cancelled = True
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Cancelling...")

    def finish(self):
        """Close the dialog."""
        self.dialog.destroy()


def show_cart_results(parent, result: Dict):
    """
    Show results after adding items to cart.

    Args:
        parent: Parent window
        result: Result dict from cart_manager.add_yays_to_cart()
    """
    added_count = len(result.get('added', []))
    failed_count = len(result.get('failed', []))
    warnings = result.get('warnings', [])

    # Build message
    if result.get('success'):
        if added_count > 0:
            title = "Success"
            message = f"✅ Successfully added {added_count} item(s) to cart!"

            if failed_count > 0:
                message += f"\n\n⚠️ {failed_count} item(s) failed to add."

            if warnings:
                message += "\n\n⚠️ Some shops are below minimum threshold."

            messagebox.showinfo(title, message, parent=parent)
        else:
            messagebox.showwarning(
                "No Items Added",
                "No items were added to cart.",
                parent=parent
            )
    else:
        error_msg = result.get('error', 'Unknown error')
        messagebox.showerror(
            "Error",
            f"Failed to add items to cart:\n\n{error_msg}",
            parent=parent
        )
