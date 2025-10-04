#!/usr/bin/env python3
"""Settings and Preferences Manager for modular GUI settings management."""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional, List
import webbrowser


class SettingsPreferencesManager:
    """Manages application settings, preferences, and user configurations."""

    def __init__(self, main_window):
        """
        Initialize Settings and Preferences Manager.
        
        Args:
            main_window: The main GUI window instance
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
    def show_settings_summary(self):
        """Show a dialog with current settings summary."""
        summary = self.main_window.settings.get_settings_summary()

        # Create summary window
        summary_window = tk.Toplevel(self.main_window)
        summary_window.title("Settings Summary")
        summary_window.geometry("600x500")
        summary_window.transient(self.main_window)

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

    def reset_settings(self):
        """Reset all settings to defaults."""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?\n\nThis action cannot be undone."):
            if self.main_window.settings.reset_to_defaults():
                messagebox.showinfo("Success", "Settings have been reset to defaults.\n\nRestart the application to see all changes.")
            else:
                messagebox.showerror("Error", "Failed to reset settings.")

    def export_settings(self):
        """Export current settings to a file."""
        file_path = filedialog.askopenfilename if hasattr(self.main_window, 'filedialog') else tk.filedialog.askopenfilename
        
        export_path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if export_path:
            if self.main_window.settings.export_settings(export_path):
                messagebox.showinfo("Success", f"Settings exported to:\n{export_path}")
            else:
                messagebox.showerror("Error", "Failed to export settings.")

    def import_settings(self):
        """Import settings from a file."""
        file_path = filedialog.askopenfilename if hasattr(self.main_window, 'filedialog') else tk.filedialog.askopenfilename
        
        import_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if import_path:
            if messagebox.askyesno("Import Settings", "Importing settings will overwrite your current settings.\n\nAre you sure you want to continue?"):
                if self.main_window.settings.import_settings(import_path):
                    messagebox.showinfo("Success", "Settings imported successfully.\n\nRestart the application to see all changes.")
                else:
                    messagebox.showerror("Error", "Failed to import settings.")

    def show_image_search_help(self):
        """Show image search help dialog."""
        help_text = """
IMAGE SEARCH HELP

🎯 QUICK START:
1. Click "Select Image..." to upload a product photo
2. Use the search functionality to find similar items

📊 RESULTS:
- Shows sold item counts and price ranges
- Calculates profit margins with different scenarios
- Estimates fees and shipping costs
- Provides market recommendations
        """

        # Create help window
        help_window = tk.Toplevel(self.main_window)
        help_window.title("Image Search Help")
        help_window.geometry("500x400")
        help_window.transient(self.main_window)

        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)

    def show_about_dialog(self):
        """Show about dialog."""
        about_text = f"""
Mandarake Scraper GUI v1.0.0

A comprehensive tool for analyzing Mandarake listings
and comparing prices with eBay sold listings.

Features:
• Advanced image search with comparison methods
• Profit margin calculations and market analysis
• Persistent settings and window preferences

Settings file: {self.main_window.settings.settings_file}
Last updated: {self.main_window.settings.get_setting('meta.last_updated', 'Never')}
        """

        messagebox.showinfo("About Mandarake Scraper", about_text)

    def show_ransac_info(self):
        """Show RANSAC information dialog."""
        info_text = """
RANSAC GEOMETRIC VERIFICATION

What it does:
• Verifies that matched image features have consistent spatial relationships
• Uses RANSAC (Random Sample Consensus) algorithm to detect true matches
• Adds ~40-50% processing time but significantly improves accuracy

When to use:
✓ When you need maximum accuracy for difficult matches
✓ When comparing similar-looking items that are different editions
✓ When false positives are costly (e.g., expensive items)

When to skip:
• For quick exploratory searches
• When processing large batches (hundreds of items)
• When visual similarity is good enough

Current algorithm (without RANSAC):
• Template matching: 60% weight
• Feature matching: 25% weight
• SSIM: 10% weight
• Histogram: 5% weight
• Consistency bonus: up to 25% boost

With RANSAC enabled:
• Adds geometric coherence verification (15-20% weight)
• Penalizes random/scattered feature matches
• Increases match confidence scores
        """

        messagebox.showinfo("RANSAC Geometric Verification", info_text)

    def handle_mimic_changed(self, *args):
        """Handle browser mimic setting change."""
        # Settings saved on close, no need to save on every change
        pass

    def handle_max_csv_items_changed(self, *args):
        """Handle max CSV items setting change with validation."""
        value = self.main_window.max_csv_items_var.get().strip()

        # Allow empty or numeric values only
        if value == '':
            value = '0'

        try:
            max_items = int(value)
            if max_items < 0:
                max_items = 0

            # Update settings
            self.main_window.settings.set_setting('scraper.max_csv_items', max_items)
            self.main_window.settings.save()

        except ValueError:
            # Invalid input - reset to current saved value
            current_value = self.main_window.settings.get_setting('scraper.max_csv_items', 0)
            self.main_window.max_csv_items_var.set(str(current_value))

    def handle_marketplace_toggle(self):
        """Handle marketplace toggle changes."""
        # Save toggle state
        toggles = {
            'mandarake': self.main_window.mandarake_enabled.get(),
            'ebay': self.main_window.ebay_enabled.get(),
            'surugaya': self.main_window.surugaya_enabled.get(),
            'dejapan': self.main_window.dejapan_enabled.get(),
            'alerts': self.main_window.alerts_enabled.get()
        }
        self.main_window.settings.save_marketplace_toggles(toggles)

        # Show restart required message
        messagebox.showinfo(
            "Restart Required",
            "Marketplace changes will take effect after restarting the application."
        )

    def load_gui_settings(self):
        """Load GUI settings from file."""
        settings = {'mimic': False}
        try:
            from gui.constants import SETTINGS_PATH
            if SETTINGS_PATH.exists():
                with SETTINGS_PATH.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        settings.update(data)
        except Exception:
            settings = {'mimic': False}
        
        self.main_window.gui_settings = settings
        try:
            self.main_window._settings_loaded = False
            self.main_window.mimic_var.set(settings.get('mimic', True))  # Default to True for Unicode support

            # Load eBay search settings if they exist
            if hasattr(self.main_window, 'browserless_max_results'):
                self.main_window.browserless_max_results.set(settings.get('ebay_max_results', "10"))
            if hasattr(self.main_window, 'browserless_max_comparisons'):
                self.main_window.browserless_max_comparisons.set(settings.get('ebay_max_comparisons', "MAX"))

            # Load CSV filter settings
            if hasattr(self.main_window, 'csv_in_stock_only'):
                self.main_window.csv_in_stock_only.set(settings.get('csv_in_stock_only', True))
            if hasattr(self.main_window, 'csv_add_secondary_keyword'):
                self.main_window.csv_add_secondary_keyword.set(settings.get('csv_add_secondary_keyword', False))
        finally:
            self.main_window._settings_loaded = True

    def save_gui_settings(self):
        """Save GUI settings to file."""
        if not getattr(self.main_window, '_settings_loaded', False):
            return
        try:
            from gui.constants import SETTINGS_PATH
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Save listbox paned position - use tracked user ratio if available
            listbox_ratio = self.main_window.gui_settings.get('listbox_paned_ratio', 0.65)
            if hasattr(self.main_window, '_user_sash_ratio') and self.main_window._user_sash_ratio is not None:
                listbox_ratio = self.main_window._user_sash_ratio

            data = {
                'mimic': bool(self.main_window.mimic_var.get()),
                'ebay_max_results': self.main_window.browserless_max_results.get() if hasattr(self.main_window, 'browserless_max_results') else "10",
                'ebay_max_comparisons': self.main_window.browserless_max_comparisons.get() if hasattr(self.main_window, 'browserless_max_comparisons') else "MAX",
                'csv_in_stock_only': bool(self.main_window.csv_in_stock_only.get()) if hasattr(self.main_window, 'csv_in_stock_only') else True,
                'csv_add_secondary_keyword': bool(self.main_window.csv_add_secondary_keyword.get()) if hasattr(self.main_window, 'csv_add_secondary_keyword') else False,
                'listbox_paned_ratio': listbox_ratio
            }
            with SETTINGS_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def save_window_settings(self):
        """Save current window settings."""
        try:
            # Get current window geometry
            geometry = self.main_window.geometry()
            width, height, x, y = self._parse_geometry(geometry)

            # Check if maximized
            maximized = self.main_window.state() == 'zoomed'

            # Get paned window sash position (if it exists)
            ebay_paned_pos = None
            if hasattr(self.main_window, 'ebay_paned'):
                try:
                    # Get sash position (distance from top)
                    sash_coords = self.main_window.ebay_paned.sash_coord(0)  # First sash
                    if sash_coords:
                        ebay_paned_pos = sash_coords[1]  # Y coordinate
                except Exception as e:
                    logging.debug(f"Failed to get eBay paned sash position: {e}")

            # Save window settings with paned position
            settings_dict = {
                'width': width,
                'height': height,
                'x': x,
                'y': y,
                'maximized': maximized
            }
            if ebay_paned_pos is not None:
                settings_dict['ebay_paned_pos'] = ebay_paned_pos

            self.main_window.settings.save_window_settings(**settings_dict)
            self.main_window.settings.save_settings()

        except Exception as e:
            logging.error(f"Error saving window settings: {e}")

    def _parse_geometry(self, geometry_string: str) -> tuple:
        """Parse tkinter geometry string into width, height, x, y."""
        try:
            # Format: "800x600+100+50"
            import re
            match = re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', geometry_string)
            if match:
                return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            else:
                return 780, 760, 100, 100
        except (ValueError, AttributeError, TypeError) as e:
            logging.warning(f"Failed to parse geometry string '{geometry_string}': {e}")
            return 780, 760, 100, 100

    def restore_paned_position(self):
        """Restore the paned window sash position from saved settings."""
        try:
            if not hasattr(self.main_window, 'ebay_paned'):
                return

            window_settings = self.main_window.settings.get_window_settings()
            ebay_paned_pos = window_settings.get('ebay_paned_pos')

            if ebay_paned_pos is not None:
                # Set the sash position
                self.main_window.ebay_paned.sash_place(0, 0, ebay_paned_pos)
                print(f"[GUI] Restored eBay paned window position: {ebay_paned_pos}")
        except Exception as e:
            print(f"[GUI] Could not restore paned position: {e}")

    def restore_listbox_paned_position(self):
        """Restore the listbox paned window sash position from saved settings."""
        if not hasattr(self.main_window, 'listbox_paned'):
            return
        try:
            ratio = self.main_window.gui_settings.get('listbox_paned_ratio', 0.65)  # Default 65% for categories, 35% for shops
            total_width = self.main_window.listbox_paned.winfo_width()
            sash_pos = int(total_width * ratio)
            self.main_window.listbox_paned.sash_place(0, sash_pos, 0)
            self.main_window._user_sash_ratio = ratio  # Initialize user ratio to the restored value
        except Exception as e:
            print(f"[LISTBOX PANED] Error restoring position: {e}")

    def update_recent_menu(self):
        """Update the recent files menu."""
        self.main_window.recent_menu.delete(0, tk.END)
        recent_files = self.main_window.settings.get_recent_config_files()

        if recent_files:
            for file_path in recent_files:
                file_name = Path(file_path).name
                self.main_window.recent_menu.add_command(
                    label=file_name,
                    command=lambda path=file_path: self._load_recent_config(path)
                )
        else:
            self.main_window.recent_menu.add_command(label="No recent files", state=tk.DISABLED)

    def _load_recent_config(self, file_path: str):
        """Load a recent config file."""
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.main_window._populate_from_config(config)
                self.main_window.last_saved_path = Path(file_path)
                self.main_window.status_var.set(f"Loaded recent config: {Path(file_path).name}")
            else:
                messagebox.showerror("Error", f"File not found: {file_path}")
                # Remove from recent files
                recent_files = self.main_window.settings.get_recent_config_files()
                if file_path in recent_files:
                    recent_files.remove(file_path)
                    self.main_window.settings.set_setting("recent.config_files", recent_files)
                    self.update_recent_menu()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def show_preferences_dialog(self):
        """Show the unified preferences dialog."""
        from gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.main_window, self.main_window.settings)
        self.main_window.wait_window(dialog)

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self.main_window)
        self.main_window.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        # Recent files submenu
        self.main_window.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Configs", menu=self.main_window.recent_menu)
        self.update_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Preferences...", command=self.show_preferences_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.main_window.on_closing)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="View Settings Summary", command=self.show_settings_summary)
        settings_menu.add_command(label="Reset to Defaults", command=self.reset_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Export Settings", command=self.export_settings)
        settings_menu.add_command(label="Import Settings", command=self.import_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Image Search Guide", command=self.show_image_search_help)
        help_menu.add_command(label="About", command=self.show_about_dialog)
