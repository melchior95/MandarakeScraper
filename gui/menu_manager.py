"""Menu bar management for GUI."""
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from typing import Optional, List
import json


class MenuManager:
    """Manages application menu bar and menu-related operations."""

    def __init__(self, root, settings_manager) -> None:
        """Initialize menu manager.

        Args:
            root: The Tk root window
            settings_manager: SettingsManager instance
        """
        self.root = root
        self.settings = settings_manager
        self.recent_menu: Optional[tk.Menu] = None

    def create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        # Recent files submenu
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Configs", menu=self.recent_menu)
        self.update_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Preferences...", command=self.show_preferences)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.on_closing)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="View Settings Summary", command=self.show_settings_summary)
        settings_menu.add_command(label="Reset to Defaults", command=self.reset_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="⚠️ Configure Auto-Checkout...", command=self.show_checkout_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Export Settings", command=self.export_settings)
        settings_menu.add_command(label="Import Settings", command=self.import_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Image Search Guide", command=self.show_image_search_help)
        help_menu.add_command(label="About", command=self.show_about)

    def update_recent_menu(self) -> None:
        """Update the recent files menu."""
        self.recent_menu.delete(0, tk.END)
        recent_files = self.settings.get_recent_config_files()

        if recent_files:
            for file_path in recent_files:
                file_name = Path(file_path).name
                self.recent_menu.add_command(
                    label=file_name,
                    command=lambda path=file_path: self.load_recent_config(path)
                )
        else:
            self.recent_menu.add_command(label="No recent files", state=tk.DISABLED)

    def load_recent_config(self, file_path: str) -> None:
        """Load a recent config file."""
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.root._populate_from_config(config)
                self.root.last_saved_path = Path(file_path)
                self.root.status_var.set(f"Loaded recent config: {Path(file_path).name}")
            else:
                messagebox.showerror("Error", f"File not found: {file_path}")
                # Remove from recent files
                recent_files = self.settings.get_recent_config_files()
                if file_path in recent_files:
                    recent_files.remove(file_path)
                    self.settings.set_setting("recent.config_files", recent_files)
                    self.update_recent_menu()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def show_settings_summary(self) -> None:
        """Show a dialog with current settings summary."""
        from tkinter import ttk
        summary = self.settings.get_settings_summary()

        # Create summary window
        summary_window = tk.Toplevel(self.root)
        summary_window.title("Settings Summary")
        summary_window.geometry("600x500")
        summary_window.transient(self.root)

        # Text widget with scrollbar
        text_frame = ttk.Frame(summary_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(tk.END, summary)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(summary_window, text="Close", command=summary_window.destroy).pack(pady=10)

    def reset_settings(self) -> None:
        """Reset all settings to defaults."""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?\n\nThis action cannot be undone."):
            if self.settings.reset_to_defaults():
                messagebox.showinfo("Success", "Settings have been reset to defaults.\n\nRestart the application to see all changes.")
            else:
                messagebox.showerror("Error", "Failed to reset settings.")

    def export_settings(self) -> None:
        """Export current settings to a file."""
        file_path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            if self.settings.export_settings(file_path):
                messagebox.showinfo("Success", f"Settings exported to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Failed to export settings.")

    def import_settings(self) -> None:
        """Import settings from a file."""
        file_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            if messagebox.askyesno("Import Settings", "Importing settings will overwrite your current settings.\n\nAre you sure you want to continue?"):
                if self.settings.import_settings(file_path):
                    messagebox.showinfo("Success", "Settings imported successfully.\n\nRestart the application to see all changes.")
                else:
                    messagebox.showerror("Error", "Failed to import settings.")

    def show_preferences(self) -> None:
        """Show the unified preferences dialog."""
        from gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.root, self.settings)
        self.root.wait_window(dialog)

    def show_checkout_settings(self) -> None:
        """Show the automatic checkout configuration dialog."""
        from gui.checkout_settings_dialog import CheckoutSettingsDialog
        from gui.checkout_settings_storage import CheckoutSettingsStorage

        dialog = CheckoutSettingsDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result:
            # Check if auto-checkout was enabled
            storage = CheckoutSettingsStorage()
            if storage.is_auto_checkout_enabled():
                messagebox.showinfo(
                    "Auto-Checkout Enabled",
                    "⚠️ Automatic checkout is now ACTIVE.\n\n"
                    "The system will automatically purchase monitored items\n"
                    "when they come back in stock (subject to your spending limits).\n\n"
                    "You can disable this at any time by opening this dialog again."
                )
            else:
                messagebox.showinfo(
                    "Settings Saved",
                    "Checkout settings have been saved.\n\n"
                    "Automatic checkout is currently disabled.\n"
                    "Enable it when you're ready to start monitoring."
                )

    def show_image_search_help(self):
        """Show image search help dialog."""
        from gui import ui_helpers
        ui_helpers.show_image_search_help(self.root)

    def show_about(self):
        """Show about dialog."""
        about_text = f"""
Mandarake Scraper GUI v1.0.0

A comprehensive tool for analyzing Mandarake listings
and comparing prices with eBay sold listings.

Features:
• Advanced image search with comparison methods
• Profit margin calculations and market analysis
• Persistent settings and window preferences

Settings file: {self.settings.settings_file}
Last updated: {self.settings.get_setting('meta.last_updated', 'Never')}
        """

        messagebox.showinfo("About Mandarake Scraper", about_text)
