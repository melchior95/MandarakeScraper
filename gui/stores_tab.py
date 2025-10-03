"""Main Stores tab with subtabs and shared config/results"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
from typing import Dict, List

from gui.mandarake_store_tab import MandarakeStoreTab
from gui.surugaya_store_tab import SurugayaStoreTab


class StoresTab(ttk.Frame):
    """Unified Stores tab with subtabs for each marketplace"""

    def __init__(self, parent, settings_manager, alert_manager):
        super().__init__(parent)

        self.settings = settings_manager
        self.alert_manager = alert_manager
        self.current_results = []
        self.current_store = ''

        self._create_ui()

    def _create_ui(self):
        """Create unified stores UI"""
        # Top section - Config management
        config_frame = ttk.LabelFrame(self, text="Configurations", padding=5)
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        # Store filter and buttons
        filter_btn_frame = ttk.Frame(config_frame)
        filter_btn_frame.pack(fill=tk.X, padx=5, pady=5)

        # Store filter
        ttk.Label(filter_btn_frame, text="Store Filter:").pack(side=tk.LEFT, padx=5)
        self.store_filter_var = tk.StringVar(value="ALL")
        store_filter = ttk.Combobox(
            filter_btn_frame,
            textvariable=self.store_filter_var,
            values=["ALL", "Mandarake", "Suruga-ya"],
            width=20,
            state='readonly'
        )
        store_filter.pack(side=tk.LEFT, padx=5)
        store_filter.bind('<<ComboboxSelected>>', self._filter_configs)

        # Config buttons
        ttk.Button(filter_btn_frame, text="New Config",
                   command=self._new_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_btn_frame, text="Load Selected",
                   command=self._load_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_btn_frame, text="Delete Config",
                   command=self._delete_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_btn_frame, text="Refresh List",
                   command=self._load_config_tree).pack(side=tk.LEFT, padx=2)

        # Config tree
        tree_frame = ttk.Frame(config_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.config_tree = ttk.Treeview(
            tree_frame,
            columns=('store', 'keyword', 'category'),
            show='tree headings',
            height=5
        )

        self.config_tree.heading('#0', text='Config Name')
        self.config_tree.heading('store', text='Store')
        self.config_tree.heading('keyword', text='Keyword')
        self.config_tree.heading('category', text='Category')

        self.config_tree.column('#0', width=200)
        self.config_tree.column('store', width=100)
        self.config_tree.column('keyword', width=150)
        self.config_tree.column('category', width=100)

        config_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                      command=self.config_tree.yview)
        self.config_tree.config(yscrollcommand=config_scroll.set)

        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to load config
        self.config_tree.bind('<Double-1>', lambda e: self._load_config())

        # Middle section - Store subtabs
        self.store_notebook = ttk.Notebook(self)
        self.store_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create store subtabs
        self.mandarake_tab = MandarakeStoreTab(
            self.store_notebook,
            self.settings,
            self._on_search_complete
        )
        self.store_notebook.add(self.mandarake_tab, text="Mandarake")

        self.surugaya_tab = SurugayaStoreTab(
            self.store_notebook,
            self.settings,
            self._on_search_complete
        )
        self.store_notebook.add(self.surugaya_tab, text="Suruga-ya")

        # Bottom section - Shared results pane
        results_frame = ttk.LabelFrame(self, text="Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Results treeview
        tree_container = ttk.Frame(results_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.results_tree = ttk.Treeview(
            tree_container,
            columns=('store', 'title', 'price', 'condition', 'stock'),
            show='tree headings',
            height=10
        )

        # Configure columns
        self.results_tree.column('#0', width=100)  # Thumbnail
        self.results_tree.column('store', width=80)
        self.results_tree.column('title', width=350)
        self.results_tree.column('price', width=80)
        self.results_tree.column('condition', width=80)
        self.results_tree.column('stock', width=100)

        self.results_tree.heading('#0', text='Image')
        self.results_tree.heading('store', text='Store')
        self.results_tree.heading('title', text='Title')
        self.results_tree.heading('price', text='Price')
        self.results_tree.heading('condition', text='Condition')
        self.results_tree.heading('stock', text='Stock')

        results_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL,
                                       command=self.results_tree.yview)
        self.results_tree.config(yscrollcommand=results_scroll.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to open URL
        self.results_tree.bind('<Double-1>', self._open_selected_url)

        # Action buttons
        action_frame = ttk.Frame(results_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(action_frame, text="Export CSV",
                   command=self._export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Send to Alerts",
                   command=self._send_to_alerts).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Open Selected URL",
                   command=self._open_selected_url).pack(side=tk.LEFT, padx=2)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(results_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=5)

        # Load configs
        self._load_config_tree()

    def _load_config_tree(self):
        """Load configs into tree (filtered by store)"""
        self.config_tree.delete(*self.config_tree.get_children())

        config_dir = Path('configs')
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
            return

        selected_store = self.store_filter_var.get().lower()

        for config_file in sorted(config_dir.glob('*.json')):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # Get store from config (default to mandarake for old configs)
                store = config_data.get('store', 'mandarake')

                # Filter by store
                if selected_store == "all" or store == selected_store:
                    keyword = config_data.get('keyword', '')
                    category = config_data.get('category', '')

                    self.config_tree.insert(
                        '', 'end',
                        text=config_file.stem,
                        values=(store.title(), keyword, category),
                        tags=(str(config_file),)
                    )
            except Exception as e:
                print(f"Error loading config {config_file}: {e}")

    def _filter_configs(self, event=None):
        """Filter config tree by selected store"""
        self._load_config_tree()

    def _new_config(self):
        """Create new config from current active tab"""
        # Get active store tab
        current_tab_index = self.store_notebook.index(self.store_notebook.select())

        if current_tab_index == 0:
            active_tab = self.mandarake_tab
        elif current_tab_index == 1:
            active_tab = self.surugaya_tab
        else:
            return

        # Get config from active tab
        config = active_tab.get_config()

        # Generate filename
        keyword = config.get('keyword', 'search')
        category = config.get('category', '00')
        shop = config.get('shop', 'all')
        store = config.get('store', 'unknown')

        # Clean filename
        import re
        keyword_clean = re.sub(r'[^\w\s-]', '', keyword).strip().replace(' ', '_')[:50]
        filename = f"{keyword_clean}_{category}_{shop}_{store}.json"

        # Ask user for filename
        filepath = filedialog.asksaveasfilename(
            initialdir='configs',
            initialfile=filename,
            defaultextension='.json',
            filetypes=[('JSON files', '*.json')]
        )

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Success", f"Config saved: {Path(filepath).name}")
            self._load_config_tree()

    def _load_config(self):
        """Load selected config into appropriate store tab"""
        selection = self.config_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a config to load")
            return

        # Get config file path from tags
        config_file_str = self.config_tree.item(selection[0], 'tags')[0]
        config_file = Path(config_file_str)

        if not config_file.exists():
            messagebox.showerror("Error", f"Config file not found: {config_file}")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # Determine which store tab to load into
            store = config_data.get('store', 'mandarake')

            if store == 'mandarake':
                self.store_notebook.select(self.mandarake_tab)
                self.mandarake_tab.load_config(config_data)
                self.status_var.set(f"Loaded Mandarake config: {config_file.stem}")

            elif store == 'surugaya':
                self.store_notebook.select(self.surugaya_tab)
                self.surugaya_tab.load_config(config_data)
                self.status_var.set(f"Loaded Suruga-ya config: {config_file.stem}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def _delete_config(self):
        """Delete selected config"""
        selection = self.config_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a config to delete")
            return

        config_file_str = self.config_tree.item(selection[0], 'tags')[0]
        config_file = Path(config_file_str)

        if messagebox.askyesno("Confirm Delete", f"Delete config '{config_file.stem}'?"):
            try:
                config_file.unlink()
                self._load_config_tree()
                self.status_var.set(f"Deleted config: {config_file.stem}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete config: {e}")

    def _on_search_complete(self, results: List[Dict], store_id: str):
        """Handle search completion from any store tab"""
        self.current_results = results
        self.current_store = store_id

        # Display results in shared results tree
        self.results_tree.delete(*self.results_tree.get_children())

        for item in results:
            marketplace = item.get('marketplace', store_id).title()
            title = item.get('title', '')
            price = item.get('price', 0)
            condition = item.get('condition', '')
            stock = item.get('stock_status', '')

            price_str = f"¥{price:.0f}" if price > 0 else "N/A"

            self.results_tree.insert(
                '', 'end',
                text='',  # TODO: Add thumbnail
                values=(marketplace, title, price_str, condition, stock),
                tags=(item.get('url', ''),)
            )

        self.status_var.set(f"Found {len(results)} items from {store_id.title()}")

    def _open_selected_url(self, event=None):
        """Open selected item's URL in browser"""
        selection = self.results_tree.selection()
        if not selection:
            return

        url = self.results_tree.item(selection[0], 'tags')[0]
        if url:
            import webbrowser
            webbrowser.open(url)

    def _export_csv(self):
        """Export results to CSV"""
        if not self.current_results:
            messagebox.showwarning("No Results", "No results to export")
            return

        # Ask for filename
        filepath = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')],
            initialfile=f"{self.current_store}_results.csv"
        )

        if filepath:
            import csv

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                if self.current_results:
                    fieldnames = list(self.current_results[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.current_results)

            messagebox.showinfo("Success", f"Exported {len(self.current_results)} items to {Path(filepath).name}")
            self.status_var.set(f"Exported to: {Path(filepath).name}")

    def _send_to_alerts(self):
        """Send selected results to Alerts tab"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select items to send to Alerts")
            return

        # Get selected items
        selected_items = []
        for item_id in selection:
            # Find matching item in current_results
            url = self.results_tree.item(item_id, 'tags')[0]
            for result in self.current_results:
                if result.get('url') == url:
                    selected_items.append(result)
                    break

        if selected_items:
            # Convert to alert format and add to alert manager
            for item in selected_items:
                alert_item = {
                    'title': item.get('title', ''),
                    'price': item.get('price', 0),
                    'url': item.get('url', ''),
                    'image_url': item.get('image_url', ''),
                    'marketplace': item.get('marketplace', self.current_store).title(),
                    'condition': item.get('condition', ''),
                    'stock_status': item.get('stock_status', ''),
                    'status': 'Pending',
                    'extra': item.get('extra', {})
                }

                # Add to alert manager
                self.alert_manager.add_alert(alert_item)

            messagebox.showinfo("Success", f"Sent {len(selected_items)} items to Alerts")
            self.status_var.set(f"Sent {len(selected_items)} items to Alerts tab")
