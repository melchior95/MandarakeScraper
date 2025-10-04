"""
Mandarake/Stores Tab

This tab provides:
1. Multi-store search interface (Mandarake, Suruga-ya)
2. Keyword and category selection
3. Shop filtering
4. Configuration management
5. Search URL preview
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Dict, List
from pathlib import Path

from gui.constants import (
    MAIN_CATEGORY_OPTIONS,
    RECENT_OPTIONS
)


class MandarakeTab(ttk.Frame):
    """Mandarake/Stores tab for multi-store product search configuration."""

    def __init__(self, parent, main_window):
        """
        Initialize Mandarake/Stores tab.

        Args:
            parent: Parent widget (notebook)
            main_window: Reference to main window for shared resources
        """
        super().__init__(parent)
        self.main = main_window

        # Store UI references
        self.vertical_paned = None
        self.listbox_paned = None
        self.detail_listbox = None
        self.shop_listbox = None
        self.keyword_entry = None
        self.keyword_menu = None
        self.main_category_combo = None
        self.exclude_word_label = None
        self.exclude_word_entry = None
        self.condition_label = None
        self.condition_combo = None
        self.recent_combo = None

        # Create variables on main window so they're accessible from main window methods
        # Store selector and URL
        self.main.current_store = tk.StringVar(value="Mandarake")
        self.main.mandarake_url_var = tk.StringVar()

        # Search configuration
        self.main.keyword_var = tk.StringVar()
        self.main.exclude_word_var = tk.StringVar()
        self.main.main_category_var = tk.StringVar()

        # URL options - load defaults from settings
        self.main.hide_sold_var = tk.BooleanVar(value=False)
        default_results_per_page = str(self.main.settings.get_setting('scrapers.mandarake.results_per_page', 48))
        default_max_pages = str(self.main.settings.get_setting('scrapers.mandarake.max_pages', 2))
        self.main.results_per_page_var = tk.StringVar(value=default_results_per_page)
        self.main.max_pages_var = tk.StringVar(value=default_max_pages)
        self.main.recent_hours_var = tk.StringVar(value=RECENT_OPTIONS[0][0])

        # Language and filters - load defaults from settings
        default_language = self.main.settings.get_setting('general.language', 'en')
        self.main.language_var = tk.StringVar(value=default_language)
        self.main.condition_var = tk.StringVar(value="all")
        self.main.adult_filter_var = tk.StringVar(value="All")

        # Track user sash position
        self._user_sash_ratio = None

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the Mandarake/Stores tab UI."""
        pad = {'padx': 5, 'pady': 5}

        # Create vertical PanedWindow to split top section from bottom sections
        self.vertical_paned = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        self.vertical_paned.pack(fill=tk.BOTH, expand=True)

        # Top pane: Form fields and listboxes (resizable)
        top_pane = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(top_pane, minsize=200)

        # Bottom container: Options + Configs (not resizable internally)
        bottom_container = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(bottom_container, minsize=200)

        # Bind to track user changes to vertical paned position
        self.vertical_paned.bind('<ButtonRelease-1>', self._on_vertical_sash_moved)

        # === TOP PANE: Search Configuration ===
        self._build_search_fields(top_pane, pad)
        self._build_category_shop_listboxes(top_pane, pad)

        # === MIDDLE PANE: Options ===
        self._build_options_section(bottom_container, pad)

        # === BOTTOM PANE: Config/Schedule Management ===
        self._build_config_schedule_section(bottom_container, pad)

        # Initialize with Mandarake store (default)
        self._on_store_changed()

    def _build_search_fields(self, parent, pad):
        """Build search input fields (store selector, URL, keyword, main category)."""
        # Store selector
        ttk.Label(parent, text="Store:").grid(row=0, column=0, sticky=tk.W, **pad)
        store_combo = ttk.Combobox(
            parent,
            textvariable=self.main.current_store,
            values=["Mandarake", "Suruga-ya"],
            state="readonly",
            width=20
        )
        store_combo.grid(row=0, column=1, sticky=tk.W, **pad)
        store_combo.bind("<<ComboboxSelected>>", self._on_store_changed)

        # Store URL input
        ttk.Label(parent, text="Store URL:").grid(row=1, column=0, sticky=tk.W, **pad)
        url_entry = ttk.Entry(parent, textvariable=self.main.mandarake_url_var, width=60)
        url_entry.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), **pad)
        ttk.Button(parent, text="Load URL", command=self._load_from_url).grid(row=1, column=4, sticky=tk.W, **pad)

        # Keyword entry
        ttk.Label(parent, text="Keyword:").grid(row=2, column=0, sticky=tk.W, **pad)
        self.main.keyword_entry = ttk.Entry(parent, textvariable=self.main.keyword_var, width=42)
        self.main.keyword_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W, **pad)
        self.main.keyword_var.trace_add("write", self._update_preview)
        self.main.keyword_entry.bind("<FocusOut>", self._commit_keyword_changes)
        self.main.keyword_entry.bind("<Return>", self._save_config_on_enter)

        # Right-click context menu for keyword entry
        self.main.keyword_menu = tk.Menu(self.main.keyword_entry, tearoff=0)
        self.main.keyword_menu.add_command(label="Add Selected Text to Publisher List", command=self.main._add_to_publisher_list)
        self.main.keyword_entry.bind("<Button-3>", self._show_keyword_menu)

        # Exclude keywords field (for Suruga-ya)
        self.main.exclude_word_label = ttk.Label(parent, text="Exclude words:")
        self.main.exclude_word_label.grid(row=2, column=3, sticky=tk.W, padx=(20, 5), pady=5)
        self.main.exclude_word_entry = ttk.Entry(parent, textvariable=self.main.exclude_word_var, width=30)
        self.main.exclude_word_entry.grid(row=2, column=4, columnspan=2, sticky=tk.W, **pad)
        self.main.exclude_word_var.trace_add("write", self.main._auto_save_config)
        # Hide by default (shown when Suruga-ya is selected)
        self.main.exclude_word_label.grid_remove()
        self.main.exclude_word_entry.grid_remove()

        # Main category selector
        ttk.Label(parent, text="Main category:").grid(row=3, column=0, sticky=tk.W, **pad)
        self.main.main_category_combo = ttk.Combobox(
            parent,
            textvariable=self.main.main_category_var,
            state="readonly",
            width=42,
            values=[f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS],
        )
        self.main.main_category_combo.grid(row=3, column=1, columnspan=3, sticky=tk.W, **pad)
        self.main.main_category_combo.bind("<<ComboboxSelected>>", self._on_main_category_selected)

        # Configure grid weights
        parent.columnconfigure(6, weight=1)

    def _build_category_shop_listboxes(self, parent, pad):
        """Build category and shop listboxes with labels."""
        # Create labels row for both listboxes
        labels_frame = ttk.Frame(parent)
        labels_frame.grid(row=4, column=0, columnspan=7, sticky=(tk.W, tk.E), **pad)
        ttk.Label(labels_frame, text="Detailed categories:").pack(side=tk.LEFT)
        ttk.Label(labels_frame, text="Shop:", anchor='e').pack(side=tk.RIGHT, padx=(0, 50))

        # Create PanedWindow for resizable listboxes
        self.listbox_paned = tk.PanedWindow(parent, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.listbox_paned.grid(row=5, column=0, columnspan=7, sticky=(tk.W, tk.E, tk.N, tk.S), **pad)

        # Left pane: Detailed categories
        detail_frame = ttk.Frame(self.listbox_paned)
        self.main.detail_listbox = tk.Listbox(
            detail_frame,
            selectmode=tk.SINGLE,
            height=10,
            exportselection=False,
        )
        self.main.detail_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.main.detail_listbox.yview)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.main.detail_listbox.configure(yscrollcommand=detail_scroll.set)
        self.main.detail_listbox.bind("<<ListboxSelect>>", lambda _: self._update_preview())
        self._populate_detail_categories()
        self.listbox_paned.add(detail_frame, minsize=200)

        # Right pane: Shop listbox
        shop_frame = ttk.Frame(self.listbox_paned)
        self.main.shop_listbox = tk.Listbox(
            shop_frame,
            selectmode=tk.SINGLE,
            height=10,
            exportselection=False,
        )
        self.main.shop_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shop_scroll = ttk.Scrollbar(shop_frame, orient=tk.VERTICAL, command=self.main.shop_listbox.yview)
        shop_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.main.shop_listbox.configure(yscrollcommand=shop_scroll.set)
        self.main.shop_listbox.bind("<<ListboxSelect>>", self._on_shop_selected)
        self._populate_shop_list()
        self.listbox_paned.add(shop_frame, minsize=150)

        # Bind to track user changes
        self.listbox_paned.bind('<ButtonRelease-1>', self._on_listbox_sash_moved)

        # Configure top pane grid weights
        parent.rowconfigure(5, weight=1)  # Listbox row expands

    def _build_options_section(self, parent, pad):
        """Build options section (URL options, language, filters)."""
        # Middle pane: Options (fixed, no sash below it)
        middle_pane = ttk.Frame(parent)
        middle_pane.pack(fill=tk.X, padx=5, pady=5)

        # --- URL Options (affect Mandarake search) - All in one row ---
        ttk.Checkbutton(middle_pane, text="Hide sold", variable=self.main.hide_sold_var,
                        command=self._update_preview).grid(row=0, column=0, sticky=tk.W, **pad)

        ttk.Label(middle_pane, text="Results/page:").grid(row=0, column=1, sticky=tk.W, padx=(15, 5), pady=5)
        results_per_page_combo = ttk.Combobox(
            middle_pane,
            textvariable=self.main.results_per_page_var,
            state="readonly",
            width=6,
            values=["48", "120", "240"]
        )
        results_per_page_combo.grid(row=0, column=2, sticky=tk.W, **pad)
        self.main.results_per_page_var.trace_add("write", self._update_preview)

        ttk.Label(middle_pane, text="Max pages:").grid(row=0, column=3, sticky=tk.W, padx=(15, 5), pady=5)
        ttk.Entry(middle_pane, textvariable=self.main.max_pages_var, width=8).grid(row=0, column=4, sticky=tk.W, **pad)
        self.main.max_pages_var.trace_add("write", self.main._auto_save_config)

        ttk.Label(middle_pane, text="Latest:").grid(row=0, column=5, sticky=tk.W, padx=(15, 5), pady=5)
        self.main.recent_combo = ttk.Combobox(
            middle_pane,
            textvariable=self.main.recent_hours_var,
            state="readonly",
            width=15,
            values=[label for label, _ in RECENT_OPTIONS],
        )
        self.main.recent_combo.grid(row=0, column=6, sticky=tk.W, **pad)
        self.main.recent_hours_var.trace_add("write", self._update_preview)
        self.main.recent_hours_var.trace_add("write", self._on_recent_hours_changed)

        # Initialize CSV variables if not already done (for backward compatibility with CSV comparison tab)
        if not hasattr(self.main, 'csv_newly_listed_only'):
            self.main.csv_newly_listed_only = tk.BooleanVar(value=False)
        if not hasattr(self.main, 'csv_in_stock_only'):
            self.main.csv_in_stock_only = tk.BooleanVar(value=True)
        if not hasattr(self.main, 'csv_add_secondary_keyword'):
            self.main.csv_add_secondary_keyword = tk.BooleanVar(value=False)

        # --- Language (rarely used) - Same row ---
        ttk.Label(middle_pane, text="Language:").grid(row=1, column=0, sticky=tk.W, **pad)
        lang_combo = ttk.Combobox(middle_pane, textvariable=self.main.language_var, values=["en", "ja"], width=6, state="readonly")
        lang_combo.grid(row=1, column=1, sticky=tk.W, **pad)
        self.main.language_var.trace_add("write", self._update_preview)

        # --- Condition filter (for Suruga-ya) ---
        self.main.condition_label = ttk.Label(middle_pane, text="Condition:")
        self.main.condition_label.grid(row=1, column=2, sticky=tk.W, padx=(15, 5), pady=5)
        self.main.condition_combo = ttk.Combobox(
            middle_pane,
            textvariable=self.main.condition_var,
            values=["All", "New Only", "Used Only"],
            state="readonly",
            width=12
        )
        self.main.condition_combo.grid(row=1, column=3, sticky=tk.W, **pad)
        self.main.condition_var.trace_add("write", self.main._auto_save_config)
        # Hide by default (shown when Suruga-ya is selected)
        self.main.condition_label.grid_remove()
        self.main.condition_combo.grid_remove()

        # --- Adult content filter ---
        ttk.Label(middle_pane, text="Content:").grid(row=1, column=4, sticky=tk.W, padx=(15, 5), pady=5)
        adult_combo = ttk.Combobox(
            middle_pane,
            textvariable=self.main.adult_filter_var,
            values=["All", "Adult Only"],
            state="readonly",
            width=12
        )
        adult_combo.grid(row=1, column=5, sticky=tk.W, **pad)
        self.main.adult_filter_var.trace_add("write", self.main._auto_save_config)

    def _build_config_schedule_section(self, parent, pad):
        """Build config/schedule management section."""
        from gui.tree_manager import TreeManager
        from gui.schedule_frame import ScheduleFrame

        # Bottom pane: Configs/Schedules and buttons (fills remaining space)
        bottom_pane = ttk.Frame(parent)
        bottom_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Configs/Schedules tabbed interface
        config_schedule_notebook = ttk.Notebook(bottom_pane)
        config_schedule_notebook.grid(row=0, column=0, columnspan=7, sticky=tk.NSEW, **pad)

        # Configs tab
        tree_frame = ttk.Frame(config_schedule_notebook)
        config_schedule_notebook.add(tree_frame, text="Configs")

        # Store filter row
        filter_frame = ttk.Frame(tree_frame)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Store Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.main.config_store_filter = tk.StringVar(value='All')
        store_filter_combo = ttk.Combobox(filter_frame, textvariable=self.main.config_store_filter,
                                          values=['All', 'Mandarake', 'Suruga-Ya'], state='readonly', width=12)
        store_filter_combo.pack(side=tk.LEFT)
        store_filter_combo.bind('<<ComboboxSelected>>', lambda e: self.main._filter_config_tree())

        columns = ('store', 'file', 'keyword', 'category', 'shop', 'hide_sold', 'results_per_page', 'max_pages', 'latest_additions', 'language')
        self.main.config_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=6)
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
            self.main.config_tree.heading(col, text=heading)
            width = widths.get(col, 100)
            self.main.config_tree.column(col, width=width, stretch=False)

        # Add vertical scrollbar
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.main.config_tree.yview)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.main.config_tree.xview)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.main.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.main.config_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        # Initialize tree manager after tree widget is created
        self.main.tree_manager = TreeManager(self.main.config_tree, self.main.config_manager)
        # Share tree manager path mapping for legacy helpers
        self.main.config_paths = self.main.tree_manager.config_paths

        # Single click to load config
        self.main.config_tree.bind('<<TreeviewSelect>>', self.main._on_config_selected)
        # Prevent space from affecting tree selection when it has focus
        # Allow deselect by clicking empty area
        self.main.config_tree.bind("<Button-1>", lambda e: self.main._deselect_if_empty(e, self.main.config_tree))

        # Add right-click context menu for config tree
        self.main.config_tree_menu = tk.Menu(self.main.config_tree, tearoff=0)
        self.main.config_tree_menu.add_command(label="Load CSV", command=self.main._load_csv_from_config)
        self.main.config_tree_menu.add_command(label="Edit Category", command=self.main._edit_category_from_menu)
        self.main.config_tree.bind("<Button-3>", self.main._show_config_tree_menu)

        # Double-click to edit category
        self.main.config_tree.bind("<Double-Button-1>", self.main._on_config_tree_double_click)

        # Enable column drag-to-reorder
        self.main._setup_column_drag(self.main.config_tree)

        # Schedules tab
        self.main.schedule_frame = ScheduleFrame(config_schedule_notebook, self.main.schedule_executor)
        config_schedule_notebook.add(self.main.schedule_frame, text="Schedules")

        # Bind tab change to show/hide appropriate buttons
        config_schedule_notebook.bind("<<NotebookTabChanged>>", self.main._on_config_schedule_tab_changed)
        self.main.config_schedule_notebook = config_schedule_notebook

        # Config management buttons (row 1)
        self.main.config_buttons_frame = ttk.Frame(bottom_pane)
        self.main.config_buttons_frame.grid(row=1, column=0, columnspan=5, sticky=tk.W, **pad)
        ttk.Button(self.main.config_buttons_frame, text="New Config", command=self.main._new_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.main.config_buttons_frame, text="Delete Selected", command=self.main._delete_selected_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.main.config_buttons_frame, text="Move Up", command=lambda: self.main._move_config(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.main.config_buttons_frame, text="Move Down", command=lambda: self.main._move_config(1)).pack(side=tk.LEFT, padx=5)

        # Action buttons for Mandarake scraper (row 2)
        self.main.action_buttons_frame = ttk.Frame(bottom_pane)
        self.main.action_buttons_frame.grid(row=2, column=0, columnspan=5, sticky=tk.W, **pad)
        ttk.Button(self.main.action_buttons_frame, text="Search Store", command=self.main.run_now).pack(side=tk.LEFT, padx=5)
        self.main.cancel_button = ttk.Button(self.main.action_buttons_frame, text="Cancel Search", command=self.main.cancel_search, state='disabled')
        self.main.cancel_button.pack(side=tk.LEFT, padx=5)

        # Configure bottom pane grid
        bottom_pane.rowconfigure(0, weight=1)  # Tree row expands
        for i in range(7):
            bottom_pane.columnconfigure(i, weight=1)

        # Load config tree
        self.main._load_config_tree()

    # ==================== Store/Category Management ====================

    def _on_store_changed(self, event=None):
        """Handle store selection change - reload categories and shops."""
        store = self.main.current_store.get()

        if store == "Mandarake":
            # Reload Mandarake categories and shops
            self._populate_detail_categories()
            self._populate_shop_list()
            # Update main category dropdown
            self.main.main_category_combo['values'] = [f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS]
            # Auto-select "Everything" category
            self.main.main_category_var.set("Everything (00)")
            # Set results per page to 240 (Mandarake default)
            self.main.results_per_page_var.set('240')
            # Trigger category selection to populate detailed categories
            self._on_main_category_selected()

            # Hide Suruga-ya specific fields
            self.main.exclude_word_label.grid_remove()
            self.main.exclude_word_entry.grid_remove()
            self.main.condition_label.grid_remove()
            self.main.condition_combo.grid_remove()

        elif store == "Suruga-ya":
            # Load Suruga-ya categories and shops
            from store_codes.surugaya_codes import SURUGAYA_MAIN_CATEGORIES
            # Update main category dropdown with Suruga-ya categories
            category_values = [f"{name} ({code})" for code, name in sorted(SURUGAYA_MAIN_CATEGORIES.items())]
            self.main.main_category_combo['values'] = category_values
            # Auto-select first category (Games)
            if category_values:
                self.main.main_category_var.set(category_values[0])
            # Load Suruga-ya shops
            self._populate_surugaya_shops()
            # Set results per page to 50 (Suruga-ya fixed)
            self.main.results_per_page_var.set('50')
            # Trigger category selection to populate detailed categories
            self._on_main_category_selected()

            # Show Suruga-ya specific fields
            self.main.exclude_word_label.grid()
            self.main.exclude_word_entry.grid()
            self.main.condition_label.grid()
            self.main.condition_combo.grid()

    def _populate_detail_categories(self, main_code=None):
        """Populate detail categories listbox based on selected store and main category."""
        from mandarake_codes import MANDARAKE_ALL_CATEGORIES

        self.main.detail_listbox.delete(0, tk.END)
        self.main.detail_code_map = []

        def should_include(code: str) -> bool:
            if not main_code:
                return True
            # If main_code is "00" (Everything), show all categories
            if main_code == "00":
                return True
            return code.startswith(main_code)

        for code, info in sorted(MANDARAKE_ALL_CATEGORIES.items()):
            if should_include(code):
                label = f"{code} - {info['en']}"
                self.main.detail_listbox.insert(tk.END, label)
                self.main.detail_code_map.append(code)

    def _populate_shop_list(self):
        """Populate shop listbox with all available stores."""
        from gui.constants import STORE_OPTIONS

        self.main.shop_listbox.delete(0, tk.END)
        self.main.shop_code_map = []

        # Add "All Stores" option first
        self.main.shop_listbox.insert(tk.END, "All Stores")
        self.main.shop_code_map.append("all")

        # Add all individual stores
        for code, name in STORE_OPTIONS:
            label = f"{name} ({code})"
            self.main.shop_listbox.insert(tk.END, label)
            self.main.shop_code_map.append(code)

        # Default selection: All Stores
        self.main.shop_listbox.selection_set(0)

    def _populate_surugaya_categories(self, main_code=None):
        """Populate Suruga-ya categories."""
        from store_codes.surugaya_codes import SURUGAYA_DETAILED_CATEGORIES

        self.main.detail_listbox.delete(0, tk.END)
        self.main.detail_code_map = []

        if not main_code:
            return

        # Get categories for this main category
        categories = SURUGAYA_DETAILED_CATEGORIES.get(main_code, {})
        for code, name in sorted(categories.items()):
            label = f"{code} - {name}"
            self.main.detail_listbox.insert(tk.END, label)
            self.main.detail_code_map.append(code)

    def _populate_surugaya_shops(self):
        """Populate Suruga-ya shops."""
        from store_codes.surugaya_codes import SURUGAYA_SHOPS

        self.main.shop_listbox.delete(0, tk.END)
        self.main.shop_code_map = []

        # Add "All Stores" option first
        self.main.shop_listbox.insert(tk.END, "All Stores")
        self.main.shop_code_map.append("all")

        # Add all individual stores
        for code, name in sorted(SURUGAYA_SHOPS.items()):
            label = f"{name} ({code})"
            self.main.shop_listbox.insert(tk.END, label)
            self.main.shop_code_map.append(code)

        # Default selection: All Stores
        self.main.shop_listbox.selection_set(0)

    def _on_main_category_selected(self, event=None):
        """Handle main category selection."""
        from gui import utils

        # Don't auto-select during config loading - let _select_categories handle it
        if getattr(self.main, '_loading_config', False):
            return

        code = utils.extract_code(self.main.main_category_var.get())

        # Check which store is selected
        store = self.main.current_store.get()

        if store == "Suruga-ya":
            # Use Suruga-ya hierarchical categories
            self._populate_surugaya_categories(code)
        else:
            # Use Mandarake categories
            self._populate_detail_categories(code)

        # Auto-select the first detail category (the main category itself)
        if self.main.detail_listbox.size() > 0:
            self.main.detail_listbox.selection_clear(0, tk.END)
            self.main.detail_listbox.selection_set(0)

        self._update_preview()

    def _on_shop_selected(self, event=None):
        """Handle shop selection from listbox."""
        selection = self.main.shop_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        shop_code = self.main.shop_code_map[index]

        self._update_preview()

    # ==================== URL and Preview ====================

    def _load_from_url(self):
        """Load configuration from Mandarake/Suruga-ya URL."""
        from tkinter import messagebox
        from urllib.parse import urlparse, parse_qs

        url = self.main.mandarake_url_var.get().strip()
        if not url:
            messagebox.showinfo("No URL", "Please enter a store URL")
            return

        try:
            # Detect store type from URL
            if 'suruga-ya.jp' in url:
                # Parse Suruga-ya URL
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
                self.main.current_store.set("Suruga-ya")
                self._on_store_changed()  # Load Suruga-ya categories

            elif 'mandarake.co.jp' in url:
                # Parse Mandarake URL
                from mandarake_scraper import parse_mandarake_url
                config = parse_mandarake_url(url)
                config['search_url'] = url  # Store the original URL
                config['store'] = 'mandarake'

                # Update store selector
                self.main.current_store.set("Mandarake")
                self._on_store_changed()  # Load Mandarake categories
            else:
                messagebox.showerror("Error", "URL must be from Mandarake or Suruga-ya")
                return

            self.main._populate_from_config(config)
            self.main.status_var.set(f"Loaded URL parameters from {config['store']}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to parse URL: {e}")

    def _update_preview(self, *args):
        """Update search URL preview based on current configuration."""
        # Delegate to main window for now
        if hasattr(self.main, '_update_preview'):
            self.main._update_preview(*args)

    def _commit_keyword_changes(self, event=None):
        """Trim trailing spaces from keyword and rename file if needed (called on blur)."""
        from gui import utils

        if not hasattr(self.main, 'last_saved_path') or not self.main.last_saved_path:
            return

        # Don't rename during initial load
        if not getattr(self.main, '_settings_loaded', False):
            return

        # Don't rename while loading a config
        if getattr(self.main, '_loading_config', False):
            return

        try:
            # Trim trailing spaces from keyword
            current_keyword = self.main.keyword_var.get()
            trimmed_keyword = current_keyword.rstrip()

            # Only update if there were trailing spaces
            if current_keyword != trimmed_keyword:
                self.main.keyword_var.set(trimmed_keyword)

            # Now check if filename should be updated
            config = self.main._collect_config()
            if config:
                suggested_filename = utils.suggest_config_filename(config)
                current_filename = self.main.last_saved_path.name

                # If the suggested filename is different, rename the file
                if suggested_filename != current_filename:
                    new_path = self.main.last_saved_path.parent / suggested_filename

                    # Only rename if new path doesn't exist or is the same file
                    if not new_path.exists() or new_path == self.main.last_saved_path:
                        old_path = self.main.last_saved_path

                        # Find the tree item with the old path and update its mapping
                        for item in self.main.config_tree.get_children():
                            if self.main.config_paths.get(item) == old_path:
                                self.main.config_paths[item] = new_path
                                break

                        # Delete old file if renaming
                        if new_path != self.main.last_saved_path and self.main.last_saved_path.exists():
                            self.main.last_saved_path.unlink()

                        # Update the path
                        self.main.last_saved_path = new_path
                        print(f"[COMMIT] Renamed config to: {suggested_filename}")

                        # Save and update tree
                        self.main._save_config_to_path(config, self.main.last_saved_path, update_tree=True)
        except Exception as e:
            print(f"[COMMIT] Error: {e}")

    def _save_config_on_enter(self, event=None):
        """Auto-save config with new filename when Enter is pressed in keyword field."""
        return self.main._save_config_on_enter(event)

    def _show_keyword_menu(self, event):
        """Show context menu on keyword entry."""
        try:
            # Always show menu - user can select text before right-clicking
            self.main.keyword_menu.post(event.x_root, event.y_root)
        except tk.TclError as e:
            logging.debug(f"Failed to show keyword menu: {e}")

    def _add_to_publisher_list(self):
        """Add selected text from keyword entry to publisher list."""
        from tkinter import messagebox

        try:
            if self.main.keyword_entry.selection_present():
                selected_text = self.main.keyword_entry.selection_get().strip()
                if selected_text and len(selected_text) > 1:
                    self.main.publisher_list.add(selected_text)
                    self.main._save_publisher_list()
                    messagebox.showinfo("Publisher Added", f"'{selected_text}' has been added to the publisher list.")
                    print(f"[PUBLISHERS] Added: {selected_text}")
        except Exception as e:
            print(f"[PUBLISHERS] Error adding publisher: {e}")

    def _set_keyword_field(self, text):
        """Helper function to reliably set the keyword field."""
        # Method 1: Use StringVar
        self.main.keyword_var.set(text)

        # Method 2: Direct widget manipulation (more reliable)
        self.main.keyword_entry.delete(0, tk.END)
        self.main.keyword_entry.insert(0, text)

        # Force update
        self.main.keyword_entry.update_idletasks()

    def _on_recent_hours_changed(self, *args):
        """Handle recent hours filter change."""
        # Delegate to main window for now
        if hasattr(self.main, '_on_recent_hours_changed'):
            self.main._on_recent_hours_changed(*args)

    # ==================== Helper Methods ====================

    def _on_vertical_sash_moved(self, event=None):
        """Track when user manually moves the vertical sash."""
        if not hasattr(self, 'vertical_paned'):
            return

        # Skip if we're currently restoring sash position
        if hasattr(self.main, 'window_manager') and getattr(self.main.window_manager, '_restoring_sash', False):
            return

        try:
            total_height = self.vertical_paned.winfo_height()
            if total_height > 400:
                sash_pos = self.vertical_paned.sash_coord(0)[1]  # Y coordinate
                # Set on window_manager, not main
                self.main.window_manager._user_vertical_sash_ratio = sash_pos / total_height
        except Exception:
            pass

    def _on_listbox_sash_moved(self, event=None):
        """Track when user manually moves the horizontal listbox sash."""
        if not hasattr(self, 'listbox_paned'):
            return

        # Skip if we're currently restoring sash position
        if hasattr(self.main, 'window_manager') and getattr(self.main.window_manager, '_restoring_sash', False):
            return

        try:
            total_width = self.listbox_paned.winfo_width()
            if total_width > 500:
                sash_pos = self.listbox_paned.sash_coord(0)[0]
                ratio = sash_pos / total_width
                # Set on window_manager, not main
                self.main.window_manager._user_sash_ratio = ratio
                print(f"[LISTBOX SASH MOVED] New ratio: {ratio:.2f} (sash={sash_pos}px, width={total_width}px)")
        except Exception as e:
            print(f"[LISTBOX SASH MOVED] Error: {e}")

    def _resolve_shop(self):
        """Get the selected shop code from the listbox."""
        selection = self.main.shop_listbox.curselection()
        if not selection:
            return "all"  # Default to all stores if nothing selected

        index = selection[0]
        shop_code = self.main.shop_code_map[index]

        return shop_code if shop_code else "all"

    def _extract_code(self, label: str | None):
        """Extract code from label string."""
        from gui import utils
        return utils.extract_code(label)

    def _match_main_code(self, code: str | None):
        """Match category code to main category."""
        from gui import utils
        return utils.match_main_code(code)

    def _select_categories(self, categories):
        """Select categories in the detail listbox."""
        from gui import utils
        from gui.constants import MAIN_CATEGORY_OPTIONS

        self.main.detail_listbox.selection_clear(0, tk.END)
        if not categories:
            self.main.main_category_var.set('')
            self._populate_detail_categories()
            return

        # Select main category
        first_code = categories[0]
        main_code = utils.match_main_code(first_code)
        if main_code:
            # Find the exact matching value from the combobox list
            # This ensures the value matches the dropdown format exactly
            for code, name in MAIN_CATEGORY_OPTIONS:
                if code == main_code:
                    label = f"{name} ({code})"
                    self.main.main_category_var.set(label)
                    break
        else:
            self.main.main_category_var.set('')

        # Populate detail categories based on main category
        self._populate_detail_categories(utils.extract_code(self.main.main_category_var.get()))

        # Select detail categories and scroll to first selected
        first_selected_idx = None
        unknown_categories = []

        for idx, code in enumerate(self.main.detail_code_map):
            if code in categories:
                self.main.detail_listbox.selection_set(idx)
                if first_selected_idx is None:
                    first_selected_idx = idx

        # Handle unknown categories (not in current listbox)
        for cat_code in categories:
            if cat_code not in self.main.detail_code_map:
                unknown_categories.append(cat_code)

        # Add unknown categories to listbox temporarily
        if unknown_categories:
            for cat_code in unknown_categories:
                # Add to detail_code_map and listbox
                self.main.detail_code_map.append(cat_code)
                display_text = f"Unknown Category ({cat_code})"
                self.main.detail_listbox.insert(tk.END, display_text)
                # Select the newly added item
                new_idx = len(self.main.detail_code_map) - 1
                self.main.detail_listbox.selection_set(new_idx)
                if first_selected_idx is None:
                    first_selected_idx = new_idx

        # Scroll to make the first selected category visible
        if first_selected_idx is not None:
            self.main.detail_listbox.see(first_selected_idx)

    def load_results_table(self, csv_path: Path | None):
        """Load and display Mandarake search results from CSV file.

        Args:
            csv_path: Path to CSV results file
        """
        import csv
        import tkinter as tk
        from tkinter import messagebox
        from pathlib import Path
        from PIL import Image, ImageTk

        print(f"[GUI DEBUG] Loading results table from: {csv_path}")
        if not hasattr(self.main, 'result_tree'):
            return
        for item in self.main.result_tree.get_children():
            self.main.result_tree.delete(item)
        self.main.result_links.clear()
        self.main.result_images.clear()
        self.main.result_data.clear()
        if not csv_path or not csv_path.exists():
            print(f"[GUI DEBUG] CSV not found: {csv_path}")
            self.main.status_var.set(f'CSV not found: {csv_path}')
            return
        show_images = getattr(self.main, 'show_images_var', None)
        show_images = show_images.get() if show_images else False
        print(f"[GUI DEBUG] Show images setting: {show_images}")
        try:
            with csv_path.open('r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row.get('title', '')
                    price = row.get('price_text') or row.get('price') or ''
                    shop = row.get('shop') or row.get('shop_text') or ''
                    stock = row.get('in_stock') or row.get('stock_status') or ''
                    if isinstance(stock, str) and stock.lower() in {'true', 'false'}:
                        stock = 'Yes' if stock.lower() == 'true' else 'No'
                    category = row.get('category', '')
                    link = row.get('product_url') or row.get('url') or ''
                    local_image_path = row.get('local_image') or ''
                    web_image_url = row.get('image_url') or ''
                    item_kwargs = {'values': (title, price, shop, stock, category, link)}
                    photo = None

                    if show_images:
                        # Try local image first, then fallback to web image
                        if local_image_path:
                            print(f"[GUI DEBUG] Attempting to load local image: {local_image_path}")
                            try:
                                pil_img = Image.open(local_image_path)
                                pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)  # Slightly smaller for better fit
                                photo = ImageTk.PhotoImage(pil_img)
                                item_kwargs['image'] = photo
                                print(f"[GUI DEBUG] Successfully loaded local thumbnail: {local_image_path}")
                            except Exception as e:
                                print(f"[GUI DEBUG] Failed to load local image {local_image_path}: {e}")
                                photo = None

                        # If no local image or local image failed, try web image
                        if not photo and web_image_url:
                            print(f"[GUI DEBUG] Attempting to download web image: {web_image_url}")
                            try:
                                import requests
                                response = requests.get(web_image_url, timeout=10)
                                response.raise_for_status()
                                from io import BytesIO
                                pil_img = Image.open(BytesIO(response.content))
                                pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)  # Slightly smaller for better fit
                                photo = ImageTk.PhotoImage(pil_img)
                                item_kwargs['image'] = photo
                                print(f"[GUI DEBUG] Successfully downloaded web thumbnail: {web_image_url}")
                            except Exception as e:
                                print(f"[GUI DEBUG] Failed to download web image {web_image_url}: {e}")
                                photo = None

                        if not photo:
                            print(f"[GUI DEBUG] No image available for row: {title}")
                    else:
                        print(f"[GUI DEBUG] Show images disabled")
                    item_id = self.main.result_tree.insert('', tk.END, **item_kwargs)
                    self.main.result_data[item_id] = row
                    if photo:
                        self.main.result_images[item_id] = photo
                    self.main.result_links[item_id] = link
            self.main.status_var.set(f'Loaded results from {csv_path}')
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to load results: {exc}')

    def update_preview(self, *args):
        """Update the search URL preview based on current form fields.

        Builds Mandarake or Suruga-ya URLs from current field values and displays
        in the preview label at bottom of window.

        Args:
            *args: Variable args from tkinter trace callbacks
        """
        from urllib.parse import quote

        # Also trigger auto-save when preview updates
        self.main._auto_save_config()

        # If loading config with a provided URL, don't regenerate - keep the provided URL
        if getattr(self.main, '_loading_config', False) and hasattr(self.main, '_provided_url') and self.main._provided_url:
            return  # Keep the provided URL that was already set

        # Clear provided URL when user makes changes to UI fields
        # This allows regenerating the URL from current field values
        if hasattr(self.main, '_provided_url') and self.main._provided_url:
            self.main._provided_url = None  # Clear so URL gets regenerated

        store = self.main.current_store.get()
        keyword = self.main.keyword_var.get().strip()

        params: list[tuple[str, str]] = []
        notes: list[str] = []

        if store == "Suruga-ya":
            # Build Suruga-ya URL
            if keyword:
                params.append(("search_word", quote(keyword)))
            params.append(("searchbox", "1"))

            # Main category (category1)
            main_category_text = self.main.main_category_var.get()
            if main_category_text:
                from gui import utils
                main_code = utils.extract_code(main_category_text)
                if main_code:
                    params.append(("category1", main_code))

            # Detailed category (category2)
            categories = self.main._get_selected_categories()
            if categories:
                params.append(("category2", categories[0]))

            # Exclude words
            if hasattr(self.main, 'exclude_word_var'):
                exclude = self.main.exclude_word_var.get().strip()
                if exclude:
                    params.append(("exclude_word", quote(exclude)))
                    notes.append(f"exclude: {exclude}")

            # Condition filter
            if hasattr(self.main, 'condition_var'):
                condition = self.main.condition_var.get()
                if condition == "New Only":
                    params.append(("sale_classified", "1"))
                    notes.append("new only")
                elif condition == "Used Only":
                    params.append(("sale_classified", "2"))
                    notes.append("used only")

            # Adult filter for Suruga-ya
            if hasattr(self.main, 'adult_filter_var') and self.main.adult_filter_var.get() == "Adult Only":
                params.append(("adult_s", "1"))
                notes.append("adult only")

            # Shop filter
            shop_value = self._resolve_shop()
            if shop_value and shop_value != 'all':
                params.append(("tenpo_code", shop_value))

            # Build URL
            query = '&'.join(f"{key}={value}" for key, value in params)
            url = "https://www.suruga-ya.jp/search"
            if query:
                url = f"{url}?{query}"

        else:
            # Build Mandarake URL
            if keyword:
                params.append(("keyword", quote(keyword)))

            # Add category even without keyword
            categories = self.main._get_selected_categories()
            if categories:
                params.append(("categoryCode", categories[0]))
                if len(categories) > 1:
                    notes.append(f"+{len(categories) - 1} more categories")

            shop_value = self._resolve_shop()
            if shop_value:
                params.append(("shop", quote(shop_value)))

            if self.main.hide_sold_var.get():
                params.append(("soldOut", '1'))

            if self.main.language_var.get() == 'en':
                params.append(("lang", "en"))

            recent_hours = self.main._get_recent_hours_value()
            if recent_hours:
                params.append(("upToMinutes", str(recent_hours * 60)))
                notes.append(f"last {recent_hours}h")

            # Adult content filter for Mandarake
            if hasattr(self.main, 'adult_filter_var') and self.main.adult_filter_var.get() == "Adult Only":
                params.append(("r18", "1"))
                notes.append("adult only")

            # Build URL
            query = '&'.join(f"{key}={value}" for key, value in params)
            url = "https://order.mandarake.co.jp/order/listPage/list"
            if query:
                url = f"{url}?{query}"

        note_str = f" ({'; '.join(notes)})" if notes else ''
        self.main.url_var.set(f"{url}{note_str}")
