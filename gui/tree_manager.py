#!/usr/bin/env python3
"""Tree Manager Module - Handles configuration tree operations."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from tkinter import messagebox, ttk

from gui.configuration_manager import ConfigurationManager


class TreeManager:
    """Manages the configuration tree widget operations."""
    
    def __init__(self, tree_widget, config_manager: ConfigurationManager):
        """Initialize the tree manager.
        
        Args:
            tree_widget: The ttk.Treeview widget for configurations
            config_manager: ConfigurationManager instance
        """
        self.tree = tree_widget
        self.config_manager = config_manager
        self.config_paths: Dict[str, Path] = {}
        
        # Setup tree columns
        self._setup_tree_columns()
        
        # Setup drag-to-reorder functionality
        self._setup_column_drag()
        
        # Bind events
        self._bind_events()
    
    def _setup_tree_columns(self):
        """Setup tree columns and headings."""
        columns = ('store', 'keyword', 'category', 'shop', 'hide_sold',
                  'results_per_page', 'max_pages', 'latest_additions', 'language', 'file')
        
        self.tree['columns'] = columns
        
        headings = {
            'store': 'Store',
            'file': 'File',
            'keyword': 'Keyword',
            'category': 'Category',
            'shop': 'Shop',
            'hide_sold': 'Hide Sold',
            'results_per_page': 'Results/Page',
            'max_pages': 'Max Pages',
            'latest_additions': 'Latest',
            'language': 'Lang',
        }
        
        widths = {
            'store': 90,
            'file': 200,
            'keyword': 120,
            'category': 120,
            'shop': 120,
            'hide_sold': 80,
            'results_per_page': 80,
            'max_pages': 70,
            'latest_additions': 70,
            'language': 50,
        }
        
        for col, heading in headings.items():
            self.tree.heading(col, text=heading)
            width = widths.get(col, 100)
            self.tree.column(col, width=width, stretch=False)
    
    def _setup_column_drag(self):
        """Enable drag-to-reorder for treeview columns."""
        self.tree._drag_data = {'column': None, 'x': 0}
        
        def on_header_press(event):
            region = self.tree.identify_region(event.x, event.y)
            if region == 'heading':
                col = self.tree.identify_column(event.x)
                self.tree._drag_data['column'] = col
                self.tree._drag_data['x'] = event.x
        
        def on_header_motion(event):
            if self.tree._drag_data['column']:
                self.tree.configure(cursor='exchange')
        
        def on_header_release(event):
            if self.tree._drag_data['column']:
                src_col = self.tree._drag_data['column']
                region = self.tree.identify_region(event.x, event.y)
                if region == 'heading':
                    dst_col = self.tree.identify_column(event.x)
                    if src_col != dst_col:
                        self._reorder_columns(src_col, dst_col)
                self.tree.configure(cursor='')
                self.tree._drag_data['column'] = None
        
        self.tree.bind('<ButtonPress-1>', on_header_press, add='+')
        self.tree.bind('<B1-Motion>', on_header_motion, add='+')
        self.tree.bind('<ButtonRelease-1>', on_header_release, add='+')
    
    def _reorder_columns(self, src_col: str, dst_col: str):
        """Reorder treeview columns while preserving headings and widths."""
        cols = list(self.tree['columns'])
        
        # Convert column identifiers to indices
        src_idx = int(src_col.replace('#', '')) - 1
        dst_idx = int(dst_col.replace('#', '')) - 1
        
        # Save current headings and widths
        column_info = {}
        for col in cols:
            column_info[col] = {
                'heading': self.tree.heading(col)['text'],
                'width': self.tree.column(col)['width'],
                'minwidth': self.tree.column(col)['minwidth'],
                'stretch': self.tree.column(col)['stretch'],
                'anchor': self.tree.column(col)['anchor']
            }
        
        # Reorder the columns list
        col_to_move = cols.pop(src_idx)
        cols.insert(dst_idx, col_to_move)
        
        # Apply new column order
        self.tree['columns'] = cols
        self.tree['displaycolumns'] = cols
        
        # Restore headings and widths
        for col in cols:
            info = column_info[col]
            self.tree.heading(col, text=info['heading'])
            self.tree.column(col,
                           width=info['width'],
                           minwidth=info['minwidth'],
                           stretch=info['stretch'],
                           anchor=info['anchor'])
    
    def _bind_events(self):
        """Bind tree events."""
        # Prevent space from affecting tree selection
        # Allow deselect by clicking empty area
        self.tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e))
    
    def _deselect_if_empty(self, event):
        """Deselect tree items if clicking on empty area."""
        item = self.tree.identify_row(event.y)
        if not item:
            self.tree.selection_remove(self.tree.selection())
    
    def load_config_tree(self, store_filter: str = 'All'):
        """Load all configuration files into the tree."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.config_paths.clear()
        
        configs_dir = Path('configs')
        if not configs_dir.exists():
            return
        
        # Get all config files
        config_files = list(configs_dir.glob('*.json'))
        
        # Load custom order
        order_file = Path('.config_order.json')
        custom_order = []
        if order_file.exists():
            try:
                with order_file.open('r', encoding='utf-8') as f:
                    custom_order = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load config order file: {e}")
        
        # Sort: custom ordered items first, then new items by modification time
        config_file_names = {f.name: f for f in config_files}
        sorted_files = []
        
        # Add files in custom order
        for name in custom_order:
            if name in config_file_names:
                sorted_files.append(config_file_names[name])
                del config_file_names[name]
        
        # Add any new files (sorted by modification time, newest first)
        new_files = sorted(config_file_names.values(), key=lambda p: p.stat().st_mtime, reverse=True)
        sorted_files.extend(new_files)
        
        # Add files to tree
        for cfg_path in sorted_files:
            if self._add_config_to_tree(cfg_path, store_filter):
                continue  # Successfully added
        
        print(f"[TREE MANAGER] Loaded {len(self.config_paths)} configs (filter: {store_filter})")
    
    def _add_config_to_tree(self, cfg_path: Path, store_filter: str) -> bool:
        """Add a single config to the tree if it matches the filter."""
        try:
            with cfg_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return False
        
        # Skip if data is not a dictionary
        if not isinstance(data, dict):
            return False
        
        # Check store filter
        store = data.get('store', 'mandarake')
        if store_filter != 'All' and store.lower() != store_filter.lower():
            return False
        
        # Get display values
        values = self.config_manager.get_config_tree_values(data, cfg_path)
        
        # Add to tree
        item = self.tree.insert('', 'end', values=values)
        self.config_paths[item] = cfg_path
        
        return True
    
    def filter_by_store(self, store_filter: str):
        """Filter tree by store type."""
        # Get all items
        all_items = list(self.config_paths.keys())
        
        # Show/hide items based on filter
        for item in all_items:
            values = self.tree.item(item, 'values')
            if values:
                store = values[0]  # Store is the first column
                
                # Show item if it matches filter or filter is "All"
                if store_filter == 'All' or store == store_filter:
                    self.tree.reattach(item, '', 'end')
                else:
                    self.tree.detach(item)
        
        print(f"[TREE MANAGER] Filtered by store: {store_filter}")
    
    def update_tree_item(self, path: Path, config: Dict[str, Any]):
        """Update a specific tree item's values or add if new."""
        # Find existing item
        existing_item = None
        for item in self.tree.get_children():
            if self.config_paths.get(item) == path:
                existing_item = item
                break
        
        # Get values
        values = self.config_manager.get_config_tree_values(config, path)
        
        if existing_item:
            # Update existing item
            self.tree.item(existing_item, values=values)
        else:
            # Add new item
            new_item = self.tree.insert('', 'end', values=values)
            self.config_paths[new_item] = path
            # Select and show the new item
            self.tree.selection_set(new_item)
            self.tree.see(new_item)
            print(f"[TREE MANAGER] Added new config: {path.name}")
    
    def get_selected_config_path(self) -> Optional[Path]:
        """Get the path of the selected configuration."""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = selection[0]
        return self.config_paths.get(item)
    
    def get_selected_config_paths(self) -> List[Path]:
        """Get paths of all selected configurations."""
        selection = self.tree.selection()
        paths = []
        for item in selection:
            path = self.config_paths.get(item)
            if path:
                paths.append(path)
        return paths
    
    def select_config_by_path(self, path: Path):
        """Select a configuration by its path."""
        for item in self.tree.get_children():
            if self.config_paths.get(item) == path:
                self.tree.selection_set(item)
                self.tree.see(item)
                break
    
    def move_config_up(self):
        """Move selected config up in the list."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to move")
            return False
        
        item = selection[0]
        path = self.config_paths.get(item)
        if not path:
            return False
        
        # Get current order
        tree_children = self.tree.get_children()
        current_order = [self.config_paths.get(child).name for child in tree_children]
        
        try:
            current_index = current_order.index(path.name)
        except ValueError:
            return False
        
        if current_index <= 0:
            return False  # Already at top
        
        # Swap positions
        new_index = current_index - 1
        current_order[current_index], current_order[new_index] = current_order[new_index], current_order[current_index]
        
        # Save new order
        self._save_config_order(current_order)
        
        # Reload tree
        self.load_config_tree()
        
        # Re-select moved item
        self.select_config_by_path(path)
        
        return True
    
    def move_config_down(self):
        """Move selected config down in the list."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a config file to move")
            return False
        
        item = selection[0]
        path = self.config_paths.get(item)
        if not path:
            return False
        
        # Get current order
        tree_children = self.tree.get_children()
        current_order = [self.config_paths.get(child).name for child in tree_children]
        
        try:
            current_index = current_order.index(path.name)
        except ValueError:
            return False
        
        if current_index >= len(current_order) - 1:
            return False  # Already at bottom
        
        # Swap positions
        new_index = current_index + 1
        current_order[current_index], current_order[new_index] = current_order[new_index], current_order[current_index]
        
        # Save new order
        self._save_config_order(current_order)
        
        # Reload tree
        self.load_config_tree()
        
        # Re-select moved item
        self.select_config_by_path(path)
        
        return True
    
    def _save_config_order(self, order: List[str]):
        """Save configuration order to metadata file."""
        order_file = Path('.config_order.json')
        try:
            with order_file.open('w', encoding='utf-8') as f:
                json.dump(order, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save order: {e}")
    
    def delete_selected_configs(self) -> int:
        """Delete selected configurations.
        
        Returns:
            Number of configurations deleted
        """
        paths = self.get_selected_config_paths()
        if not paths:
            messagebox.showinfo("No Selection", "Please select config files to delete")
            return 0
        
        # Confirm deletion
        if len(paths) == 1:
            message = f"Are you sure you want to delete:\n{paths[0].name}?"
        else:
            file_list = '\n'.join(p.name for p in paths)
            message = f"Are you sure you want to delete {len(paths)} configs?\n\n{file_list}"
        
        if not messagebox.askyesno("Confirm Delete", message):
            return 0
        
        # Delete files
        deleted_count = 0
        errors = []
        for path in paths:
            if self.config_manager.delete_config(path):
                deleted_count += 1
            else:
                errors.append(f"{path.name}: Failed to delete")
        
        # Reload tree
        self.load_config_tree()
        
        # Show errors if any
        if errors:
            messagebox.showerror("Errors", "Failed to delete:\n" + '\n'.join(errors))
        
        return deleted_count
    
    def get_all_config_paths(self) -> List[Path]:
        """Get all configuration paths in current order."""
        tree_children = self.tree.get_children()
        return [self.config_paths.get(child) for child in tree_children if self.config_paths.get(child)]
