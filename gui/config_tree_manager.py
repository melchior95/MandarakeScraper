"""
Config Tree Manager

Handles all configuration tree widget operations including:
- Tree filtering by store
- Column drag-to-reorder
- Context menu actions
- Category editing dialog
- CSV loading from config
- Search query autofill
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import re


class ConfigTreeManager:
    """Manager for configuration tree widget operations."""

    def __init__(self, config_tree, config_paths, main_window):
        """
        Initialize Config Tree Manager.

        Args:
            config_tree: The treeview widget displaying configs
            config_paths: Dict mapping tree item IDs to config file paths
            main_window: Reference to main window for accessing other widgets
        """
        self.tree = config_tree
        self.config_paths = config_paths
        self.main = main_window
        self._last_menu_event = None  # Store event for dialog positioning

    def filter_tree(self, filter_value):
        """
        Filter config tree based on store filter selection.

        Args:
            filter_value: Store name to filter by, or "All" to show everything
        """
        if not hasattr(self.main, 'config_store_filter') or not self.tree:
            return

        # Get all items
        all_items = list(self.config_paths.keys())

        # Show/hide items based on filter
        for item in all_items:
            # Get the store value (first column)
            values = self.tree.item(item, 'values')
            if values:
                store = values[0]  # Store is the first column

                # Show item if it matches filter or filter is "All"
                if filter_value == 'All' or store == filter_value:
                    self.tree.reattach(item, '', 'end')
                else:
                    self.tree.detach(item)

        print(f"[CONFIG FILTER] Filtered by: {filter_value}")

    def setup_column_drag(self, tree):
        """
        Enable drag-to-reorder for treeview columns.

        Args:
            tree: The treeview widget to enable dragging on
        """
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
                        self.reorder_columns(tree, src_col, dst_col)
                tree.configure(cursor='')
                tree._drag_data['column'] = None

        tree.bind('<ButtonPress-1>', on_header_press, add='+')
        tree.bind('<B1-Motion>', on_header_motion, add='+')
        tree.bind('<ButtonRelease-1>', on_header_release, add='+')

    def reorder_columns(self, tree, src_col, dst_col):
        """
        Reorder treeview columns while preserving headings and widths.

        Args:
            tree: The treeview widget
            src_col: Source column identifier (e.g., '#1')
            dst_col: Destination column identifier (e.g., '#2')
        """
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

    def show_context_menu(self, event, menu):
        """
        Show context menu on config tree.

        Args:
            event: Mouse event
            menu: The context menu to display
        """
        # Select the item under the cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            # Store event coordinates for Edit Category dialog positioning
            self._last_menu_event = event
            menu.post(event.x_root, event.y_root)

    def edit_category_from_menu(self):
        """Edit category from right-click menu."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        config_path = self.config_paths.get(item)
        if not config_path:
            return

        # Load config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return

        # Get category info
        store = config.get('store', 'mandarake')
        category_code = config.get('category', '')
        category_name = config.get('category_name', '')

        # Only show dialog for unknown categories
        if not category_name and category_code:
            # Create a fake event with the stored menu coordinates
            event = self._last_menu_event if self._last_menu_event else None
            if not event:
                # Fallback to center of screen if no event stored
                class FakeEvent:
                    x_root = self.main.winfo_rootx() + 200
                    y_root = self.main.winfo_rooty() + 200
                event = FakeEvent()

            # Show the dialog
            self.show_edit_category_dialog(config_path, config, category_code, store, event)
        else:
            messagebox.showinfo("Info", "This category is already named. Double-click to edit.")

    def show_edit_category_dialog(self, config_path, config, category_code, store, event):
        """
        Show dialog to edit/add category name.

        Args:
            config_path: Path to config file
            config: Config dictionary
            category_code: Category code to edit
            store: Store type ('mandarake' or 'suruga-ya')
            event: Mouse event for positioning
        """
        # Unknown code - allow user to add a name
        dialog = tk.Toplevel(self.main)
        dialog.title("Add Category Name")
        dialog.transient(self.main)
        dialog.grab_set()

        # Position dialog near mouse cursor
        x = event.x_root + 10
        y = event.y_root + 10
        dialog.geometry(f"400x150+{x}+{y}")

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
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                # Add to category codes file
                try:
                    if store == 'suruga-ya':
                        codes_file = Path('store_codes') / 'surugaya_codes.py'
                    else:
                        codes_file = Path('store_codes') / 'mandarake_codes.py'

                    if codes_file.exists():
                        # Read the file as lines
                        with open(codes_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        # Determine the main category prefix (first 2 digits for most codes)
                        main_prefix = category_code[:2] if len(category_code) >= 2 else category_code

                        # Find where to insert this entry
                        insert_index = None
                        last_matching_index = None

                        for i, line in enumerate(lines):
                            # Look for category entries: '    'CODE': {'en': 'Name', 'jp': 'Name'},
                            match = re.match(r"\s*'(\d+)':\s*\{", line)
                            if match:
                                code = match.group(1)
                                # Check if this code belongs to the same main category
                                if code.startswith(main_prefix):
                                    last_matching_index = i

                        # Insert after the last matching entry
                        if last_matching_index is not None:
                            insert_index = last_matching_index + 1
                        else:
                            # No matching entries found, try to find the main category comment
                            for i, line in enumerate(lines):
                                if f"'{main_prefix}':" in line and 'everything' in line.lower():
                                    insert_index = i + 1
                                    break

                        if insert_index is not None:
                            # Create new entry with proper indentation
                            new_entry = f"    '{category_code}': {{'en': '{name}', 'jp': '{name}'}},\n"

                            # Insert the new entry
                            lines.insert(insert_index, new_entry)

                            # Write back to file
                            with open(codes_file, 'w', encoding='utf-8') as f:
                                f.writelines(lines)

                            print(f"[CATEGORY] Added {category_code}: {name} to {codes_file.name} under main category {main_prefix}")
                        else:
                            # Fallback: add at the end of the dict (before closing brace)
                            for i in range(len(lines) - 1, -1, -1):
                                if lines[i].strip() == '}':
                                    new_entry = f"    '{category_code}': {{'en': '{name}', 'jp': '{name}'}},\n"
                                    lines.insert(i, new_entry)
                                    with open(codes_file, 'w', encoding='utf-8') as f:
                                        f.writelines(lines)
                                    print(f"[CATEGORY] Added {category_code}: {name} to {codes_file.name} (at end)")
                                    break
                except Exception as e:
                    print(f"[CATEGORY] Could not update category file: {e}")

                # Update tree using tree manager
                if hasattr(self.main, 'tree_manager'):
                    self.main.tree_manager.update_tree_item(config_path, config)

                dialog.destroy()
                messagebox.showinfo("Success", f"Category '{name}' saved for code {category_code}")

        ttk.Button(dialog, text="Save", command=save_name).pack(pady=10)

    def on_double_click(self, event):
        """
        Handle double-click on config tree to edit category.

        Args:
            event: Mouse event
        """
        # Identify which column was clicked
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item:
            return

        # Check if category column was clicked (column #3)
        # Columns: store, keyword, category, shop, hide_sold, results_per_page, max_pages, latest_additions, language, file
        if column != '#3':  # Category is the 3rd column
            return

        # Get config path
        config_path = self.config_paths.get(item)
        if not config_path:
            return

        # Load config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return

        # Get current category value and store type
        store = config.get('store', 'mandarake')
        category_code = config.get('category', '')
        category_name = config.get('category_name', '')

        # Only show dialog for unknown categories
        if not category_name and category_code:
            self.show_edit_category_dialog(config_path, config, category_code, store, event)

    def load_csv_from_config(self):
        """Load CSV file associated with selected config."""
        selection = self.tree.selection()
        if not selection:
            self.main.status_var.set("No config selected")
            return

        item = selection[0]
        config_path = self.config_paths.get(item)
        if not config_path:
            self.main.status_var.set("Config path not found")
            return

        try:
            # Load the config to get the CSV path
            with config_path.open('r', encoding='utf-8') as f:
                config = json.load(f)

            # Get the CSV path from config
            csv_path_str = config.get('csv')
            if not csv_path_str:
                self.main.status_var.set("No CSV path in config")
                return

            csv_path = Path(csv_path_str)
            if not csv_path.exists():
                self.main.status_var.set(f"CSV does not exist: {csv_path.name}")
                return

            # Load CSV using main window's worker method
            success = self.main._load_csv_worker(csv_path, autofill_from_config=config)

            if success:
                csv_data = self.main.ebay_tab.csv_compare_data if hasattr(self.main, 'ebay_tab') else []
                self.main.status_var.set(f"CSV loaded successfully: {len(csv_data)} items")
            else:
                self.main.status_var.set(f"Error loading CSV: {csv_path.name}")

        except Exception as e:
            self.main.status_var.set(f"Error loading CSV: {e}")
            print(f"[CONFIG MENU] Error loading CSV: {e}")

    def autofill_search_query_from_config(self, config):
        """
        Auto-fill eBay search query from config keyword.

        Args:
            config: Config dictionary containing keyword
        """
        if hasattr(self.main, 'ebay_tab') and self.main.ebay_tab.csv_comparison_manager:
            self.main.ebay_tab.csv_comparison_manager._autofill_search_query_from_config(config)
