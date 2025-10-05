#!/usr/bin/env python3
"""Event Handlers Manager for modular GUI event handling."""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import json
import logging
import webbrowser
from typing import Dict, Any, Optional, Callable

from gui.constants import (
    STORE_OPTIONS,
    MAIN_CATEGORY_OPTIONS,
    RECENT_OPTIONS,
    CATEGORY_KEYWORDS,
)


class EventHandlersManager:
    """Manages all GUI event handlers and user interactions."""

    def __init__(self, main_window):
        """
        Initialize Event Handlers Manager.
        
        Args:
            main_window: The main GUI window instance
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
    def handle_config_selected(self, event=None):
        """Handle config selection from tree."""
        selection = self.main_window.config_tree.selection()
        if not selection:
            return
        item = selection[0]
        path = self.main_window.config_paths.get(item)
        if not path:
            return
        try:
            # Temporarily disable auto-save during config loading
            self.main_window._loading_config = True

            with path.open('r', encoding='utf-8') as f:
                config = json.load(f)
            self.main_window._populate_from_config(config)
            self.main_window.last_saved_path = path
            self.main_window.status_var.set(f"Loaded config: {path.name}")

            # Re-enable auto-save after loading is complete
            self.main_window._loading_config = False
        except Exception as exc:
            self.main_window._loading_config = False
            messagebox.showerror('Error', f'Failed to load config: {exc}')

    def handle_store_changed(self, event=None):
        """Handle store selection change - reload categories and shops."""
        store = self.main_window.current_store.get()

        if store == "Mandarake":
            # Reload Mandarake categories and shops
            self.main_window._populate_detail_categories()
            self.main_window._populate_shop_list()
            # Update main category dropdown
            self.main_window.main_category_combo['values'] = [f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS]
            # Auto-select "Everything" category
            self.main_window.main_category_var.set("Everything (00)")
            # Set results per page from settings (default 48)
            mandarake_results_per_page = self.main_window.settings.get_setting('scrapers.mandarake.results_per_page', 48)
            self.main_window.results_per_page_var.set(str(mandarake_results_per_page))
            # Trigger category selection to populate detailed categories
            self.main_window._on_main_category_selected()
        elif store == "Suruga-ya":
            # Load Suruga-ya categories and shops
            from store_codes.surugaya_codes import SURUGAYA_MAIN_CATEGORIES
            # Update main category dropdown with Suruga-ya categories
            category_values = [f"{name} ({code})" for code, name in sorted(SURUGAYA_MAIN_CATEGORIES.items())]
            self.main_window.main_category_combo['values'] = category_values
            # Auto-select first category (Games)
            if category_values:
                self.main_window.main_category_var.set(category_values[0])
            # Load Suruga-ya shops
            self.main_window._populate_surugaya_shops()
            # Set results per page to 50 (Suruga-ya fixed)
            self.main_window.results_per_page_var.set('50')
            # Trigger category selection to populate detailed categories
            self.main_window._on_main_category_selected()

    def handle_main_category_selected(self, event=None):
        """Handle main category selection."""
        from gui import utils
        code = utils.extract_code(self.main_window.main_category_var.get())

        # Check which store is selected
        store = self.main_window.current_store.get()

        if store == "Suruga-ya":
            # Use Suruga-ya hierarchical categories
            self.main_window._populate_surugaya_categories(code)
        else:
            # Use Mandarake categories
            self.main_window._populate_detail_categories(code)

        # Auto-select the first detail category (the main category itself)
        if self.main_window.detail_listbox.size() > 0:
            self.main_window.detail_listbox.selection_clear(0, tk.END)
            self.main_window.detail_listbox.selection_set(0)

        self.main_window._update_preview()

    def handle_shop_selected(self, event=None):
        """Handle shop selection from listbox."""
        selection = self.main_window.shop_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        shop_code = self.main_window.shop_code_map[index]

        self.main_window._update_preview()

    def handle_keyword_commit(self, event=None):
        """Commit keyword changes when focus leaves the field."""
        if not hasattr(self.main_window, 'last_saved_path') or not self.main_window.last_saved_path:
            return

        # Don't rename during initial load
        if not getattr(self.main_window, '_settings_loaded', False):
            return

        # Don't rename while loading a config
        if getattr(self.main_window, '_loading_config', False):
            return

        try:
            # Trim trailing spaces from keyword
            current_keyword = self.main_window.keyword_var.get()
            trimmed_keyword = current_keyword.rstrip()

            # Only update if there were trailing spaces
            if current_keyword != trimmed_keyword:
                self.main_window.keyword_var.set(trimmed_keyword)

            # Now check if filename should be updated
            config = self.main_window._collect_config()
            if config:
                from gui import utils
                suggested_filename = utils.suggest_config_filename(config)
                current_filename = self.main_window.last_saved_path.name

                # If the suggested filename is different, rename the file
                if suggested_filename != current_filename:
                    new_path = self.main_window.last_saved_path.parent / suggested_filename

                    # Only rename if new path doesn't exist or is the same file
                    if not new_path.exists() or new_path == self.main_window.last_saved_path:
                        old_path = self.main_window.last_saved_path

                        # Find the tree item with the old path and update its mapping
                        for item in self.main_window.config_tree.get_children():
                            if self.main_window.config_paths.get(item) == old_path:
                                self.main_window.config_paths[item] = new_path
                                break

                        # Delete old file if renaming
                        if new_path != self.main_window.last_saved_path and self.main_window.last_saved_path.exists():
                            self.main_window.last_saved_path.unlink()

                        # Update the path
                        self.main_window.last_saved_path = new_path
                        print(f"[COMMIT] Renamed config to: {suggested_filename}")

                        # Save and update tree
                        self.main_window._save_config_to_path(config, self.main_window.last_saved_path, update_tree=True)
        except Exception as e:
            print(f"[COMMIT] Error: {e}")

    def handle_save_on_enter(self, event=None):
        """Autosave config with new filename when Enter is pressed in keyword field."""
        # Commit keyword changes first
        self.handle_keyword_commit(event)

        # Save config with autoname
        config = self.main_window._collect_config()
        if not config:
            return

        try:
            config_path = self.main_window._save_config_autoname(config)
            # Add to recent files
            self.main_window.settings.add_recent_config_file(str(config_path))
            self.main_window._update_recent_menu()

            # Reload the tree to ensure the new file appears
            self.main_window._load_config_tree()

            # Select the newly saved config in the tree
            for item in self.main_window.config_tree.get_children():
                values = self.main_window.config_tree.item(item, 'values')
                if values and values[0] == config_path.name:
                    self.main_window.config_tree.selection_set(item)
                    self.main_window.config_tree.see(item)
                    break

            self.main_window.status_var.set(f"✓ Saved: {config_path.name}")
        except Exception as exc:
            self.main_window.status_var.set(f"Save failed: {exc}")

    def handle_url_load(self):
        """Parse URL from either Mandarake or Suruga-ya and populate config fields."""
        url = self.main_window.mandarake_url_var.get().strip()
        if not url:
            messagebox.showinfo("No URL", "Please enter a store URL")
            return

        try:
            # Detect store type from URL
            if 'suruga-ya.jp' in url:
                # Parse Suruga-ya URL
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url)
                params = parse_qs(parsed.query)

                config = {
                    'search_url': url,  # Store the original URL
                    'store': 'suruga-ya',
                    'keyword': params.get('search_word', [''])[0],
                    'category': params.get('category', [''])[0] or params.get('category2', [''])[0],
                    'category1': params.get('category1', [''])[0],
                    'category2': params.get('category2', [''])[0],
                    'shop': params.get('tenpo_code', ['all'])[0],
                    'exclude_word': params.get('exclude_word', [''])[0],
                    'condition': params.get('sale_classified', ['all'])[0],
                    'adult_only': params.get('adult_s', [''])[0] == '1',
                }

                # Update store selector
                self.main_window.current_store.set("Suruga-ya")
                self.handle_store_changed()  # Load Suruga-ya categories

            elif 'mandarake.co.jp' in url:
                # Parse Mandarake URL
                from mandarake_scraper import parse_mandarake_url
                config = parse_mandarake_url(url)
                config['search_url'] = url  # Store the original URL
                config['store'] = 'mandarake'

                # Update store selector
                self.main_window.current_store.set("Mandarake")
                self.handle_store_changed()  # Load Mandarake categories
            else:
                messagebox.showerror("Error", "URL must be from Mandarake or Suruga-ya")
                return

            self.main_window._populate_from_config(config)
            self.main_window.status_var.set(f"Loaded URL parameters from {config['store']}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to parse URL: {e}")

    def handle_new_config(self):
        """Create a new config from current form values."""
        import time

        # Ensure "All Stores" is selected if nothing is selected
        if not self.main_window.shop_listbox.curselection():
            self.main_window.shop_listbox.selection_clear(0, tk.END)
            self.main_window.shop_listbox.selection_set(0)

        # Always collect current form values
        config = self.main_window._collect_config()

        # If collection failed, use current GUI values as defaults
        if not config:
            config = {
                'keyword': self.main_window.keyword_var.get().strip(),
                'hide_sold_out': self.main_window.hide_sold_var.get(),
                'language': self.main_window.language_var.get(),
                'fast': self.main_window.fast_var.get(),
                'resume': self.main_window.resume_var.get(),
                'debug': self.main_window.debug_var.get(),
            }
            # Add shop if selected
            shop_value = self.main_window._resolve_shop()
            if shop_value:
                config['shop'] = shop_value

        # Generate filename based on current values
        timestamp = int(time.time())
        configs_dir = Path('configs')
        configs_dir.mkdir(parents=True, exist_ok=True)

        # Use auto-generated filename based on settings, or timestamp if no keyword
        has_keyword = bool(config.get('keyword', '').strip())
        if has_keyword:
            from gui import utils
            suggested_filename = utils.suggest_config_filename(config)
            path = configs_dir / suggested_filename
            # If filename already exists, add timestamp
            if path.exists():
                keyword_part = config.get('keyword', 'new').replace(' ', '_') or 'new'
                filename = f"{keyword_part}_{timestamp}.json"
                path = configs_dir / filename
        else:
            # No keyword - use timestamp-based filename
            filename = f'new_config_{timestamp}.json'
            path = configs_dir / filename

        # Save the config
        self.main_window._save_config_to_path(config, path, update_tree=False)

        # Add to tree at the end with correct values
        keyword = config.get('keyword', '')
        category = config.get('category_name', config.get('category', ''))
        shop = config.get('shop_name', config.get('shop', ''))
        hide = 'Yes' if config.get('hide_sold_out') else 'No'
        results_per_page = config.get('results_per_page', 48)
        max_pages = config.get('max_pages', '')
        recent_hours = config.get('recent_hours')
        timeframe = self.main_window._label_for_recent_hours(recent_hours) if recent_hours else ''
        language = config.get('language', 'en')
        store = config.get('store', 'Mandarake').title()

        values = (store, keyword, category, shop, hide, results_per_page, max_pages, timeframe, language, path.name)
        item = self.main_window.config_tree.insert('', 'end', values=values)
        self.main_window.config_paths[item] = path

        # Select the new item
        self.main_window.config_tree.selection_set(item)
        self.main_window.config_tree.see(item)

        # Set this as the current config for auto-save
        self.main_window.last_saved_path = path

        # Set status
        self.main_window.status_var.set(f"New config created: {path.name}")

        # Focus keyword entry for immediate typing
        self.main_window.keyword_entry.focus()

    def handle_delete_selected_config(self):
        """Delete the selected config file(s)."""
        selection = self.main_window.config_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to delete")
            return

        # Get all selected paths
        paths = [self.main_window.config_paths.get(item) for item in selection if self.main_window.config_paths.get(item)]
        if not paths:
            return

        # Confirm deletion
        if len(paths) == 1:
            message = f"Are you sure you want to delete:\n{paths[0].name}?"
        else:
            file_list = '\n'.join(p.name for p in paths)
            message = f"Are you sure you want to delete {len(paths)} configs?\n\n{file_list}"

        response = messagebox.askyesno("Confirm Delete", message)

        if response:
            deleted_count = 0
            errors = []
            for path in paths:
                try:
                    path.unlink()  # Delete the file
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{path.name}: {e}")

            self.main_window._load_config_tree()  # Reload the tree

            if errors:
                messagebox.showerror("Errors", f"Failed to delete:\n" + '\n'.join(errors))

            self.main_window.status_var.set(f"Deleted {deleted_count} config(s)")

    def handle_move_config(self, direction: int):
        """Move selected config up (-1) or down (1) in the list."""
        selection = self.main_window.config_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to move")
            return

        item = selection[0]
        path = self.main_window.config_paths.get(item)
        if not path:
            return

        # Get current order from treeview
        tree_children = self.main_window.config_tree.get_children()
        current_order = [self.main_window.config_paths.get(child).name for child in tree_children]

        try:
            current_index = current_order.index(path.name)
        except ValueError:
            return

        new_index = current_index + direction

        # Check bounds
        if new_index < 0 or new_index >= len(current_order):
            return

        # Swap positions in order list
        current_order[current_index], current_order[new_index] = current_order[new_index], current_order[current_index]

        # Save new order to metadata file
        order_file = Path('.config_order.json')
        try:
            with order_file.open('w', encoding='utf-8') as f:
                json.dump(current_order, f, indent=2)

            self.main_window._load_config_tree()  # Reload the tree

            # Re-select the moved item
            for tree_item in self.main_window.config_tree.get_children():
                if self.main_window.config_paths.get(tree_item) == path:
                    self.main_window.config_tree.selection_set(tree_item)
                    self.main_window.config_tree.see(tree_item)
                    break

            self.main_window.status_var.set(f"Moved: {path.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")

    def handle_recent_hours_changed(self, *args):
        """Handle latest additions timeframe change - refresh CSV view if loaded."""
        # Only refresh if CSV is loaded
        if hasattr(self.main_window, 'csv_compare_data') and self.main_window.csv_compare_data:
            if self.main_window.csv_comparison_manager:
                self.main_window.csv_comparison_manager.filter_csv_items()

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

    def handle_config_schedule_tab_changed(self, event):
        """Handle config/schedule tab change to show appropriate buttons."""
        selected_tab = self.main_window.config_schedule_notebook.index(self.main_window.config_schedule_notebook.select())

        if selected_tab == 0:  # Configs tab
            # Show config buttons, hide schedule frame buttons
            self.main_window.config_buttons_frame.grid()
            self.main_window.schedule_frame.hide_buttons()
        else:  # Schedules tab
            # Hide config buttons, show schedule frame buttons
            self.main_window.config_buttons_frame.grid_remove()
            self.main_window.schedule_frame.show_buttons_in_parent(self.main_window.config_buttons_frame.master, row=1)

    def handle_search_url_click(self, event=None):
        """Open the search URL in the default browser."""
        url_text = self.main_window.url_var.get()
        # Extract URL (remove any notes in parentheses)
        url = url_text.split(" (")[0].strip()
        if url and url.startswith("http"):
            webbrowser.open(url)
        else:
            messagebox.showinfo("No URL", "Enter search criteria to generate a URL")

    def handle_keyword_context_menu(self, event):
        """Show context menu on keyword entry."""
        try:
            # Always show menu - user can select text before right-clicking
            self.main_window.keyword_menu.post(event.x_root, event.y_root)
        except tk.TclError as e:
            logging.debug(f"Failed to show keyword menu: {e}")

    def handle_add_to_publisher_list(self):
        """Add selected text from keyword entry to publisher list."""
        try:
            if self.main_window.keyword_entry.selection_present():
                selected_text = self.main_window.keyword_entry.selection_get().strip()
                if selected_text and len(selected_text) > 1:
                    self.main_window.publisher_list.add(selected_text)
                    self.main_window._save_publisher_list()
                    messagebox.showinfo("Publisher Added", f"'{selected_text}' has been added to the publisher list.")
                    print(f"[PUBLISHERS] Added: {selected_text}")
        except Exception as e:
            print(f"[PUBLISHERS] Error adding publisher: {e}")

    def handle_config_tree_context_menu(self, event):
        """Show context menu on config tree."""
        # Select the item under the cursor
        item = self.main_window.config_tree.identify_row(event.y)
        if item:
            self.main_window.config_tree.selection_set(item)
            self.main_window.config_tree_menu.post(event.x_root, event.y_root)

    def handle_config_tree_double_click(self, event):
        """Handle double-click on config tree to edit category."""
        # Identify which column was clicked
        column = self.main_window.config_tree.identify_column(event.x)
        item = self.main_window.config_tree.identify_row(event.y)

        if not item:
            return

        # Check if category column was clicked (column #3)
        # Columns: store, keyword, category, shop, hide_sold, results_per_page, max_pages, latest_additions, language, file
        if column != '#3':  # Category is the 3rd column
            return

        # Get config path
        config_path = self.main_window.config_paths.get(item)
        if not config_path:
            return

        # Load config
        try:
            with config_path.open('r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return

        # Get current category value and store type
        store = config.get('store', 'mandarake')
        category_code = config.get('category', '')
        category_name = config.get('category_name', '')

        # Import category data
        if store == 'suruga-ya':
            from store_codes.surugaya_codes import SURUGAYA_CATEGORIES, SURUGAYA_DETAILED_CATEGORIES
            all_categories = SURUGAYA_CATEGORIES
        else:
            from mandarake_codes import MANDARAKE_CATEGORIES
            all_categories = MANDARAKE_CATEGORIES

        # Check if unknown category (no name)
        if not category_name and category_code:
            # Unknown code - allow user to add a name
            dialog = tk.Toplevel(self.main_window)
            dialog.title("Add Category Name")
            dialog.geometry("400x150")
            dialog.transient(self.main_window)
            dialog.grab_set()

            ttk.Label(dialog, text=f"Unknown category code: {category_code}").pack(pady=10)
            ttk.Label(dialog, text="Enter a name for this category:").pack(pady=5)

            name_var = tk.StringVar()
            name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
            name_entry.pack(pady=5)
            name_entry.focus()

            def save_name():
                name = name_var.get().strip()
                if name:
                    # Save to config
                    config['category_name'] = name
                    with config_path.open('w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)

                    # Update tree
                    self.main_window._update_tree_item(config_path, config)
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Category name saved: {name}")

            ttk.Button(dialog, text="Save", command=save_name).pack(pady=10)

        else:
            # Known category - show selection dialog
            dialog = tk.Toplevel(self.main_window)
            dialog.title("Edit Category")
            dialog.geometry("500x400")
            dialog.transient(self.main_window)
            dialog.grab_set()

            ttk.Label(dialog, text="Select a category or enter a code:").pack(pady=10)

            # Entry for manual code input
            code_frame = ttk.Frame(dialog)
            code_frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(code_frame, text="Code:").pack(side=tk.LEFT)
            code_var = tk.StringVar(value=category_code)
            code_entry = ttk.Entry(code_frame, textvariable=code_var, width=20)
            code_entry.pack(side=tk.LEFT, padx=5)

            # Listbox for category selection
            ttk.Label(dialog, text="Or select from list:").pack(pady=5)

            list_frame = ttk.Frame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            category_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
            category_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=category_list.yview)

            # Populate category list
            category_items = []
            for code, name in sorted(all_categories.items(), key=lambda x: x[1]):
                display = f"{code} - {name}"
                category_items.append((code, display))
                category_list.insert(tk.END, display)

            def on_select(event):
                selection = category_list.curselection()
                if selection:
                    selected_code = category_items[selection[0]][0]
                    code_var.set(selected_code)

            category_list.bind('<<ListboxSelect>>', on_select)

            # Select current category in list
            for i, (code, _) in enumerate(category_items):
                if code == category_code:
                    category_list.selection_set(i)
                    category_list.see(i)
                    break

            def save_category():
                new_code = code_var.get().strip()
                if new_code:
                    # Update config
                    config['category'] = new_code
                    # Get category name from lookup
                    config['category_name'] = all_categories.get(new_code, '')

                    with config_path.open('w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)

                    # Update tree
                    self.main_window._update_tree_item(config_path, config)
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Category updated: {new_code}")

            ttk.Button(dialog, text="Save", command=save_category).pack(pady=10)

    def handle_load_csv_from_config(self):
        """Load CSV file associated with selected config."""
        selection = self.main_window.config_tree.selection()
        if not selection:
            self.main_window.status_var.set("No config selected")
            return

        item = selection[0]
        config_path = self.main_window.config_paths.get(item)
        if not config_path:
            self.main_window.status_var.set("Config path not found")
            return

        try:
            # Load the config to get the CSV path
            with config_path.open('r', encoding='utf-8') as f:
                config = json.load(f)

            # Get the CSV path from config
            csv_path_str = config.get('csv')
            if not csv_path_str:
                self.main_window.status_var.set("No CSV path in config")
                return

            csv_path = Path(csv_path_str)
            if not csv_path.exists():
                self.main_window.status_var.set(f"CSV does not exist: {csv_path.name}")
                return

            # Load CSV using modular worker
            success = self.main_window._load_csv_worker(csv_path, autofill_from_config=config)

            if success:
                self.main_window.status_var.set(f"CSV loaded successfully: {len(self.main_window.csv_compare_data)} items")
            else:
                self.main_window.status_var.set(f"Error loading CSV: {csv_path.name}")

        except Exception as e:
            self.main_window.status_var.set(f"Error loading CSV: {e}")
            print(f"[CONFIG MENU] Error loading CSV: {e}")

    def handle_deselect_if_empty(self, event, tree):
        """Deselect tree items if clicking on empty area."""
        # Check if click is on an item
        item = tree.identify_row(event.y)
        if not item:
            # Clicked on empty area, deselect all
            tree.selection_remove(tree.selection())

    def handle_global_space_key(self, event):
        """Global space key handler to prevent treeview selection toggle when typing."""
        focus_widget = self.main_window.focus_get()

        # If an Entry widget has focus, allow space to work normally
        if isinstance(focus_widget, (tk.Entry, ttk.Entry)):
            return None  # Let space work in entry

        # If a Treeview or Listbox has focus, block space to prevent toggle
        if isinstance(focus_widget, (ttk.Treeview, tk.Listbox)):
            return "break"  # Prevent selection toggle

        # For any other widget, allow default behavior
        return None

    def setup_tree_column_drag(self, tree):
        """Enable drag-to-reorder for treeview columns."""
        tree._drag_data = {'column': None, 'x': 0}

        def on_header_press(event):
            region = tree.identify_region(event.x, event.y)
            if region == 'heading':
                col = tree.identify_column(event.x)
                tree._drag_data['column'] = col
                tree._drag_data['x'] = event.x

        def on_header_motion(event):
            if tree._drag_data['column']:
                # Visual feedback: change cursor
                tree.configure(cursor='exchange')

        def on_header_release(event):
            if tree._drag_data['column']:
                src_col = tree._drag_data['column']
                region = tree.identify_region(event.x, event.y)
                if region == 'heading':
                    dst_col = tree.identify_column(event.x)
                    if src_col != dst_col:
                        self._reorder_columns(tree, src_col, dst_col)
                tree.configure(cursor='')
                tree._drag_data['column'] = None

        tree.bind('<ButtonPress-1>', on_header_press, add='+')
        tree.bind('<B1-Motion>', on_header_motion, add='+')
        tree.bind('<ButtonRelease-1>', on_header_release, add='+')

    def _reorder_columns(self, tree, src_col, dst_col):
        """Reorder treeview columns while preserving headings and widths."""
        # Get current column order
        cols = list(tree['columns'])

        # Convert column identifiers (#1, #2, etc.) to indices
        src_idx = int(src_col.replace('#', '')) - 1
        dst_idx = int(dst_col.replace('#', '')) - 1

        # Save current headings and widths for all columns
        column_info = {}
        for col in cols:
            column_info[col] = {
                'heading': tree.heading(col)['text'],
                'width': tree.column(col)['width'],
                'minwidth': tree.column(col)['minwidth'],
                'stretch': tree.column(col)['stretch'],
                'anchor': tree.column(col)['anchor']
            }

        # Reorder the columns list
        col_to_move = cols.pop(src_idx)
        cols.insert(dst_idx, col_to_move)

        # Apply new column order
        tree['columns'] = cols
        tree['displaycolumns'] = cols

        # Restore headings and widths for all columns
        for col in cols:
            info = column_info[col]
            tree.heading(col, text=info['heading'])
            tree.column(col,
                       width=info['width'],
                       minwidth=info['minwidth'],
                       stretch=info['stretch'],
                       anchor=info['anchor'])
