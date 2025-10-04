"""
Advanced Settings Tab

This tab provides:
1. Scraper options (fast mode, resume, debug, browser mimic)
2. eBay search method selection
3. Marketplace toggles (Mandarake, eBay, Suruga-ya, DejaJapan, Alerts)
4. Scheduling settings
5. Output settings (CSV path, image folder, thumbnails)
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from gui.settings_preferences_manager import SettingsPreferencesManager


class AdvancedTab(ttk.Frame):
    """Advanced settings tab for scraper configuration."""

    def __init__(self, parent: ttk.Notebook, settings_manager: 'SettingsPreferencesManager', main_window: Any) -> None:
        """
        Initialize Advanced tab.

        Args:
            parent: Parent widget (notebook)
            settings_manager: Settings manager instance
            main_window: Reference to main window for shared resources
        """
        super().__init__(parent)
        self.settings = settings_manager
        self.main_window = main_window

        # Initialize variables - load from settings
        self.fast_var = tk.BooleanVar(value=False)
        default_resume = settings_manager.get_setting('scrapers.mandarake.resume', True)
        self.resume_var = tk.BooleanVar(value=default_resume)
        self.debug_var = tk.BooleanVar(value=False)
        default_mimic = settings_manager.get_setting('scrapers.mandarake.browser_mimic', True)
        self.mimic_var = tk.BooleanVar(value=default_mimic)
        self.max_csv_items_var = tk.StringVar(
            value=str(settings_manager.get_setting('scraper.max_csv_items', 0))
        )
        default_search_method = settings_manager.get_setting('ebay.search_method', 'scrapy')
        self.ebay_search_method = tk.StringVar(value=default_search_method)
        default_show_thumbnails = settings_manager.get_setting('general.csv_thumbnails_enabled', True)
        self.csv_show_thumbnails = tk.BooleanVar(value=default_show_thumbnails)

        # Marketplace toggles
        marketplace_toggles = settings_manager.get_marketplace_toggles()
        self.mandarake_enabled = tk.BooleanVar(value=marketplace_toggles.get('mandarake', True))
        self.ebay_enabled = tk.BooleanVar(value=marketplace_toggles.get('ebay', True))
        self.surugaya_enabled = tk.BooleanVar(value=marketplace_toggles.get('surugaya', False))
        self.dejapan_enabled = tk.BooleanVar(value=marketplace_toggles.get('dejapan', False))
        self.alerts_enabled = tk.BooleanVar(value=marketplace_toggles.get('alerts', True))

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the Advanced tab UI."""
        pad = {'padx': 5, 'pady': 5}
        current_row = 0

        # Scraper Options Section
        ttk.Label(
            self,
            text="Scraper Options",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Fast mode (skip eBay)",
            variable=self.fast_var
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="Resume interrupted runs",
            variable=self.resume_var
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Debug logging",
            variable=self.debug_var
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="Use browser mimic (recommended for Japanese text)",
            variable=self.mimic_var
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        self.mimic_var.trace_add('write', self._on_mimic_changed)
        current_row += 1

        # Max CSV items control
        ttk.Label(
            self,
            text="Max CSV items (0 = unlimited):"
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        max_csv_entry = ttk.Entry(
            self,
            textvariable=self.max_csv_items_var,
            width=10
        )
        max_csv_entry.grid(row=current_row, column=1, sticky=tk.W, **pad)
        self.max_csv_items_var.trace_add('write', self._on_max_csv_items_changed)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # eBay Search Method Section
        ttk.Label(
            self,
            text="eBay Search Method",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Radiobutton(
            self,
            text="Scrapy (Sold Listings - slower, more complete)",
            variable=self.ebay_search_method,
            value="scrapy"
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        ttk.Radiobutton(
            self,
            text="eBay API (Active Listings - faster, official API)",
            variable=self.ebay_search_method,
            value="api"
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # eBay API Credentials
        ttk.Label(
            self,
            text="eBay API Credentials (for Image Search):",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(10, 5))
        current_row += 1

        # Load saved credentials
        credentials = self.settings.get_ebay_credentials()
        self.ebay_client_id_var = tk.StringVar(value=credentials.get('client_id', ''))
        self.ebay_client_secret_var = tk.StringVar(value=credentials.get('client_secret', ''))

        # Client ID
        ttk.Label(self, text="Client ID (App ID):").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.ebay_client_id_var,
            width=40
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # Client Secret
        ttk.Label(self, text="Client Secret (Cert ID):").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.ebay_client_secret_var,
            width=40,
            show="*"
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # Save credentials button
        save_creds_frame = ttk.Frame(self)
        save_creds_frame.grid(row=current_row, column=0, columnspan=4, sticky=tk.W, **pad)
        ttk.Button(
            save_creds_frame,
            text="Save Credentials",
            command=self._save_ebay_credentials
        ).pack(side=tk.LEFT, padx=5)
        ttk.Label(
            save_creds_frame,
            text="Get from: https://developer.ebay.com/my/keys",
            foreground='blue',
            cursor='hand2',
            font=('TkDefaultFont', 8)
        ).pack(side=tk.LEFT, padx=5)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # Marketplace Toggles Section
        ttk.Label(
            self,
            text="Enabled Marketplaces",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        # Create checkboxes
        ttk.Checkbutton(
            self,
            text="Mandarake",
            variable=self.mandarake_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="eBay",
            variable=self.ebay_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Suruga-ya",
            variable=self.surugaya_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)

        ttk.Checkbutton(
            self,
            text="DejaJapan",
            variable=self.dejapan_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(
            self,
            text="Review/Alerts Tab",
            variable=self.alerts_enabled,
            command=self._on_marketplace_toggle
        ).grid(row=current_row, column=0, sticky=tk.W, **pad)
        current_row += 1

        # Restart warning
        ttk.Label(
            self,
            text="(Restart required for changes to take effect)",
            foreground='gray',
            font=('TkDefaultFont', 8)
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, padx=5)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # Output Settings Section
        ttk.Label(
            self,
            text="Output Settings",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        ttk.Label(self, text="CSV Output:").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.main_window.csv_path_var,
            width=32,
            state='readonly'
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(self, text="(Auto-generated)", foreground='gray').grid(
            row=current_row, column=3, sticky=tk.W, padx=(5, 0)
        )
        current_row += 1

        ttk.Label(self, text="Image Download Folder:").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.main_window.download_dir_var,
            width=32,
            state='readonly'
        ).grid(row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Label(self, text="(Auto-generated)", foreground='gray').grid(
            row=current_row, column=3, sticky=tk.W, padx=(5, 0)
        )
        current_row += 1

        ttk.Label(self, text="Thumbnail width (px):").grid(
            row=current_row, column=0, sticky=tk.W, **pad
        )
        ttk.Entry(
            self,
            textvariable=self.main_window.thumbnails_var,
            width=10
        ).grid(row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        # CSV Thumbnails toggle
        ttk.Checkbutton(
            self,
            text="Show CSV thumbnails",
            variable=self.csv_show_thumbnails,
            command=self._toggle_csv_thumbnails
        ).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, **pad)
        current_row += 1

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=current_row, column=0, columnspan=4, sticky='ew', pady=10
        )
        current_row += 1

        # Maintenance Section
        ttk.Label(
            self,
            text="Maintenance",
            font=('TkDefaultFont', 9, 'bold')
        ).grid(row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        # Cleanup button
        cleanup_frame = ttk.Frame(self)
        cleanup_frame.grid(row=current_row, column=0, columnspan=4, sticky=tk.W, **pad)

        ttk.Button(
            cleanup_frame,
            text="Clean Up Orphaned Files...",
            command=self._run_cleanup
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            cleanup_frame,
            text="(Remove old CSVs, images, debug folders without configs)",
            foreground='gray',
            font=('TkDefaultFont', 8)
        ).pack(side=tk.LEFT, padx=5)
        current_row += 1

    # ==================== Event Handlers ====================

    def _on_mimic_changed(self, *args: Any) -> None:
        """Handle browser mimic setting change."""
        self.main_window._on_mimic_changed(*args)

    def _on_max_csv_items_changed(self, *args: Any) -> None:
        """Handle max CSV items change."""
        self.main_window._on_max_csv_items_changed(*args)

    def _on_marketplace_toggle(self) -> None:
        """Handle marketplace toggle change."""
        self.main_window._on_marketplace_toggle()

    def _toggle_csv_thumbnails(self) -> None:
        """Toggle CSV thumbnails display."""
        self.main_window.toggle_csv_thumbnails()

    def _save_ebay_credentials(self) -> None:
        """Save eBay API credentials to settings."""
        from tkinter import messagebox

        client_id = self.ebay_client_id_var.get().strip()
        client_secret = self.ebay_client_secret_var.get().strip()

        if not client_id or not client_secret:
            messagebox.showwarning(
                "Incomplete Credentials",
                "Please enter both Client ID and Client Secret."
            )
            return

        # Save to settings
        self.settings.save_ebay_credentials(client_id, client_secret)

        messagebox.showinfo(
            "Credentials Saved",
            "eBay API credentials saved successfully!\n\n"
            "You can now use 'Search by Image on eBay (API)' feature."
        )

    def _run_cleanup(self) -> None:
        """Run cleanup utility to remove orphaned files."""
        from pathlib import Path
        from tkinter import messagebox, scrolledtext
        from gui.cleanup_manager import CleanupManager

        # Create cleanup manager
        cleanup_mgr = CleanupManager(root_dir=Path.cwd())

        # Scan for orphaned files
        orphaned = cleanup_mgr.scan_orphaned_files()

        # Calculate total space
        total_size = cleanup_mgr.calculate_space(orphaned)
        size_str = cleanup_mgr.format_size(total_size)

        # Get summary
        summary = cleanup_mgr.get_cleanup_summary(orphaned)
        detailed_report = cleanup_mgr.get_detailed_report(orphaned)

        # Count total items
        total_items = sum(len(items) for items in orphaned.values())

        if total_items == 0:
            messagebox.showinfo("Cleanup", "✨ No orphaned files found!\n\nEverything is clean.")
            return

        # Show preview dialog
        dialog = tk.Toplevel(self)
        dialog.title("Cleanup Preview")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.grab_set()

        # Header
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            header_frame,
            text=f"Found {total_items} item(s) to clean up ({size_str})",
            font=('TkDefaultFont', 10, 'bold')
        ).pack(anchor=tk.W)

        # Summary
        summary_frame = ttk.LabelFrame(dialog, text="Summary", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(summary_frame, text=summary, justify=tk.LEFT).pack(anchor=tk.W)

        # Detailed report in scrolled text
        report_frame = ttk.LabelFrame(dialog, text="Detailed Report", padding=10)
        report_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        report_text = scrolledtext.ScrolledText(
            report_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=('Consolas', 9)
        )
        report_text.pack(fill=tk.BOTH, expand=True)
        report_text.insert('1.0', detailed_report)
        report_text.config(state='disabled')

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        result = [False]  # Use list to capture result from nested function

        def on_delete():
            # Confirm deletion
            confirm = messagebox.askyesno(
                "Confirm Cleanup",
                f"Delete {total_items} item(s)?\n\n"
                f"This will free up {size_str} of disk space.\n\n"
                "This action cannot be undone!",
                icon='warning'
            )
            if confirm:
                result[0] = True
                dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(
            button_frame,
            text=f"Delete All ({size_str})",
            command=on_delete
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel
        ).pack(side=tk.LEFT, padx=5)

        # Wait for dialog to close
        dialog.wait_window()

        # Perform cleanup if confirmed
        if result[0]:
            success_count, error_count = cleanup_mgr.delete_orphaned_files(orphaned)

            if error_count > 0:
                messagebox.showwarning(
                    "Cleanup Complete",
                    f"✓ Deleted {success_count} item(s)\n"
                    f"✗ Failed to delete {error_count} item(s)\n\n"
                    f"Freed up approximately {size_str}"
                )
            else:
                messagebox.showinfo(
                    "Cleanup Complete",
                    f"✓ Successfully deleted {success_count} item(s)\n\n"
                    f"Freed up {size_str} of disk space!"
                )
