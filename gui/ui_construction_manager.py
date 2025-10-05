#!/usr/bin/env python3
"""UI Construction Manager for modular GUI component creation."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Optional
import logging

from gui.constants import (
    STORE_OPTIONS,
    MAIN_CATEGORY_OPTIONS,
    RECENT_OPTIONS,
    CATEGORY_KEYWORDS,
)


class UIConstructionManager:
    """Manages the construction and layout of UI components."""

    def __init__(self, main_window):
        """
        Initialize UI Construction Manager.
        
        Args:
            main_window: The main GUI window instance
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
    def create_menu_bar(self) -> tk.Menu:
        """
        Create the application menu bar.
        
        Returns:
            The created menu bar
        """
        menubar = tk.Menu(self.main_window)
        self.main_window.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        # Recent files submenu
        recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Configs", menu=recent_menu)
        self.main_window._update_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.main_window.on_closing)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="View Settings Summary", command=self.main_window._show_settings_summary)
        settings_menu.add_command(label="Reset to Defaults", command=self.main_window._reset_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Export Settings", command=self.main_window._export_settings)
        settings_menu.add_command(label="Import Settings", command=self.main_window._import_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Image Search Guide", command=self.main_window._show_image_search_help)
        help_menu.add_command(label="About", command=self.main_window._show_about)

        return menubar

    def create_status_bar(self) -> ttk.Label:
        """
        Create the status bar at the bottom of the window.
        
        Returns:
            The status bar label widget
        """
        status_label = ttk.Label(self.main_window, textvariable=self.main_window.status_var, 
                                relief=tk.SUNKEN, anchor='w')
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        return status_label

    def create_url_label(self) -> tk.Label:
        """
        Create the clickable URL label above the status bar.
        
        Returns:
            The URL label widget
        """
        url_label = tk.Label(self.main_window, textvariable=self.main_window.url_var, 
                           relief=tk.GROOVE, anchor='w', wraplength=720, justify=tk.LEFT, 
                           cursor="hand2", fg="blue")
        url_label.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        url_label.bind("<Button-1>", self.main_window._open_search_url)
        return url_label

    def create_main_notebook(self) -> ttk.Notebook:
        """
        Create the main notebook for tabs.
        
        Returns:
            The main notebook widget
        """
        notebook = ttk.Notebook(self.main_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        return notebook

    def create_stores_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        """
        Create the Stores tab (Mandarake/Suruga-ya).
        
        Args:
            notebook: The main notebook to add the tab to
            
        Returns:
            The stores tab frame
        """
        basic_frame = ttk.Frame(notebook)
        
        # Get marketplace toggles
        marketplace_toggles = self.main_window.settings.get_marketplace_toggles()
        
        if marketplace_toggles.get('mandarake', True):
            notebook.add(basic_frame, text="Stores")
            
        return basic_frame

    def create_ebay_search_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        """
        Create the eBay Search & CSV tab.
        
        Args:
            notebook: The main notebook to add the tab to
            
        Returns:
            The eBay search tab frame
        """
        browserless_frame = ttk.Frame(notebook)
        
        # Get marketplace toggles
        marketplace_toggles = self.main_window.settings.get_marketplace_toggles()
        
        if marketplace_toggles.get('ebay', True):
            notebook.add(browserless_frame, text="eBay Search & CSV")
            
        return browserless_frame

    def create_advanced_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        """
        Create the Advanced tab.
        
        Args:
            notebook: The main notebook to add the tab to
            
        Returns:
            The advanced tab frame
        """
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced")
        return advanced_frame

    def create_stores_tab_content(self, parent_frame: ttk.Frame) -> Dict[str, Any]:
        """
        Create the content for the Stores tab.
        
        Args:
            parent_frame: The parent frame for the stores tab
            
        Returns:
            Dictionary containing all created widgets
        """
        widgets = {}
        pad = {"padx": 3, "pady": 4}

        # Create vertical PanedWindow to split top section from bottom sections
        vertical_paned = tk.PanedWindow(parent_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        vertical_paned.pack(fill=tk.BOTH, expand=True)
        widgets['vertical_paned'] = vertical_paned

        # Top pane: Form fields and listboxes (resizable)
        top_pane = ttk.Frame(vertical_paned)
        vertical_paned.add(top_pane, minsize=200)
        widgets['top_pane'] = top_pane

        # Bottom container: Options + Configs (not resizable internally)
        bottom_container = ttk.Frame(vertical_paned)
        vertical_paned.add(bottom_container, minsize=200)
        widgets['bottom_container'] = bottom_container

        # Store selector
        ttk.Label(top_pane, text="Store:").grid(row=0, column=0, sticky=tk.W, **pad)
        current_store = tk.StringVar(value="Mandarake")
        store_combo = ttk.Combobox(
            top_pane,
            textvariable=current_store,
            values=["Mandarake", "Suruga-ya"],
            state="readonly",
            width=20
        )
        store_combo.grid(row=0, column=1, sticky=tk.W, **pad)
        store_combo.bind("<<ComboboxSelected>>", self.main_window._on_store_changed)
        widgets['current_store'] = current_store
        widgets['store_combo'] = store_combo

        # Mandarake URL input
        mandarake_url_var = tk.StringVar()
        ttk.Label(top_pane, text="Store URL:").grid(row=1, column=0, sticky=tk.W, **pad)
        url_entry = ttk.Entry(top_pane, textvariable=mandarake_url_var, width=60)
        url_entry.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), **pad)
        ttk.Button(top_pane, text="Load URL", command=self.main_window._load_from_url).grid(row=1, column=4, sticky=tk.W, **pad)
        widgets['mandarake_url_var'] = mandarake_url_var
        widgets['url_entry'] = url_entry

        # Keyword field
        keyword_var = tk.StringVar()
        ttk.Label(top_pane, text="Keyword:").grid(row=2, column=0, sticky=tk.W, **pad)
        keyword_entry = ttk.Entry(top_pane, textvariable=keyword_var, width=42)
        keyword_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W, **pad)
        keyword_var.trace_add("write", self.main_window._update_preview)
        keyword_entry.bind("<FocusOut>", self.main_window._commit_keyword_changes)
        keyword_entry.bind("<Return>", self.main_window._save_config_on_enter)
        widgets['keyword_var'] = keyword_var
        widgets['keyword_entry'] = keyword_entry

        # Add right-click context menu to keyword entry
        keyword_menu = tk.Menu(self.main_window.keyword_entry, tearoff=0)
        keyword_menu.add_command(label="Add Selected Text to Publisher List", command=self.main_window._add_to_publisher_list)
        keyword_entry.bind("<Button-3>", self.main_window._show_keyword_menu)
        widgets['keyword_menu'] = keyword_menu

        # Exclude keywords field (for Suruga-ya advanced search)
        exclude_word_var = tk.StringVar()
        ttk.Label(top_pane, text="Exclude words:").grid(row=2, column=3, sticky=tk.W, padx=(20, 5), pady=5)
        exclude_entry = ttk.Entry(top_pane, textvariable=exclude_word_var, width=30)
        exclude_entry.grid(row=2, column=4, columnspan=2, sticky=tk.W, **pad)
        exclude_word_var.trace_add("write", self.main_window._auto_save_config)
        widgets['exclude_word_var'] = exclude_word_var
        widgets['exclude_entry'] = exclude_entry

        # Main category dropdown
        main_category_var = tk.StringVar()
        ttk.Label(top_pane, text="Main category:").grid(row=3, column=0, sticky=tk.W, **pad)
        main_category_combo = ttk.Combobox(
            top_pane,
            textvariable=main_category_var,
            state="readonly",
            width=42,
            values=[f"{name} ({code})" for code, name in MAIN_CATEGORY_OPTIONS],
        )
        main_category_combo.grid(row=3, column=1, columnspan=3, sticky=tk.W, **pad)
        main_category_combo.bind("<<ComboboxSelected>>", self.main_window._on_main_category_selected)
        widgets['main_category_var'] = main_category_var
        widgets['main_category_combo'] = main_category_combo

        # Create labels row for both listboxes
        labels_frame = ttk.Frame(top_pane)
        labels_frame.grid(row=4, column=0, columnspan=7, sticky=(tk.W, tk.E), **pad)
        ttk.Label(labels_frame, text="Detailed categories:").pack(side=tk.LEFT)
        ttk.Label(labels_frame, text="Shop:", anchor='e').pack(side=tk.RIGHT, padx=(0, 50))
        widgets['labels_frame'] = labels_frame

        # Create PanedWindow for resizable listboxes
        listbox_paned = tk.PanedWindow(top_pane, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        listbox_paned.grid(row=5, column=0, columnspan=7, sticky=(tk.W, tk.E, tk.N, tk.S), **pad)
        widgets['listbox_paned'] = listbox_paned

        # Left pane: Detailed categories
        detail_frame = ttk.Frame(listbox_paned)
        detail_listbox = tk.Listbox(
            detail_frame,
            selectmode=tk.SINGLE,
            height=10,
            exportselection=False,
        )
        detail_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=detail_listbox.yview)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        detail_listbox.configure(yscrollcommand=detail_scroll.set)
        detail_listbox.bind("<<ListboxSelect>>", lambda _: self.main_window._update_preview())
        listbox_paned.add(detail_frame, minsize=200)
        widgets['detail_listbox'] = detail_listbox
        widgets['detail_scroll'] = detail_scroll

        # Right pane: Shop listbox
        shop_frame = ttk.Frame(listbox_paned)
        shop_listbox = tk.Listbox(
            shop_frame,
            selectmode=tk.SINGLE,
            height=10,
            exportselection=False,
        )
        shop_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shop_scroll = ttk.Scrollbar(shop_frame, orient=tk.VERTICAL, command=shop_listbox.yview)
        shop_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        shop_listbox.configure(yscrollcommand=shop_scroll.set)
        shop_listbox.bind("<<ListboxSelect>>", self.main_window._on_shop_selected)
        listbox_paned.add(shop_frame, minsize=150)
        widgets['shop_listbox'] = shop_listbox
        widgets['shop_scroll'] = shop_scroll

        # Configure top pane grid weights
        top_pane.rowconfigure(5, weight=1)
        top_pane.columnconfigure(6, weight=1)

        # Create middle pane for options
        middle_pane = self._create_options_pane(bottom_container)
        widgets['middle_pane'] = middle_pane

        # Create bottom pane for configs and buttons
        bottom_pane = self._create_configs_pane(bottom_container)
        widgets['bottom_pane'] = bottom_pane

        return widgets

    def _create_options_pane(self, parent: ttk.Frame) -> ttk.Frame:
        """
        Create the options pane with URL options and settings.
        
        Args:
            parent: The parent frame
            
        Returns:
            The options pane frame
        """
        middle_pane = ttk.Frame(parent)
        middle_pane.pack(fill=tk.X, padx=5, pady=5)

        pad = {"padx": 3, "pady": 4}

        # URL Options (affect Mandarake search) - All in one row
        hide_sold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(middle_pane, text="Hide sold", variable=hide_sold_var,
                        command=self.main_window._update_preview).grid(row=0, column=0, sticky=tk.W, **pad)

        results_per_page_var = tk.StringVar(value="48")
        ttk.Label(middle_pane, text="Results/page:").grid(row=0, column=1, sticky=tk.W, padx=(15, 5), pady=5)
        results_per_page_combo = ttk.Combobox(
            middle_pane,
            textvariable=results_per_page_var,
            state="readonly",
            width=6,
            values=["48", "120", "240"]
        )
        results_per_page_combo.grid(row=0, column=2, sticky=tk.W, **pad)
        results_per_page_var.trace_add("write", self.main_window._update_preview)

        max_pages_var = tk.StringVar()
        ttk.Label(middle_pane, text="Max pages:").grid(row=0, column=3, sticky=tk.W, padx=(15, 5), pady=5)
        ttk.Entry(middle_pane, textvariable=max_pages_var, width=8).grid(row=0, column=4, sticky=tk.W, **pad)
        max_pages_var.trace_add("write", self.main_window._auto_save_config)

        recent_hours_var = tk.StringVar(value=RECENT_OPTIONS[0][0])
        ttk.Label(middle_pane, text="Latest:").grid(row=0, column=5, sticky=tk.W, padx=(15, 5), pady=5)
        recent_combo = ttk.Combobox(
            middle_pane,
            textvariable=recent_hours_var,
            state="readonly",
            width=15,
            values=[label for label, _ in RECENT_OPTIONS],
        )
        recent_combo.grid(row=0, column=6, sticky=tk.W, **pad)
        recent_hours_var.trace_add("write", self.main_window._update_preview)
        recent_hours_var.trace_add("write", self.main_window._on_recent_hours_changed)

        # Language (rarely used) - Same row
        language_var = tk.StringVar(value="en")
        ttk.Label(middle_pane, text="Language:").grid(row=1, column=0, sticky=tk.W, **pad)
        lang_combo = ttk.Combobox(middle_pane, textvariable=language_var, values=["en", "ja"], width=6, state="readonly")
        lang_combo.grid(row=1, column=1, sticky=tk.W, **pad)
        language_var.trace_add("write", self.main_window._update_preview)

        # Condition filter (for Suruga-ya)
        condition_var = tk.StringVar(value="all")
        ttk.Label(middle_pane, text="Condition:").grid(row=1, column=2, sticky=tk.W, padx=(15, 5), pady=5)
        condition_combo = ttk.Combobox(
            middle_pane,
            textvariable=condition_var,
            values=["All", "New Only", "Used Only"],
            state="readonly",
            width=12
        )
        condition_combo.grid(row=1, column=3, sticky=tk.W, **pad)
        condition_var.trace_add("write", self.main_window._auto_save_config)

        # Adult content filter
        adult_filter_var = tk.StringVar(value="All")
        ttk.Label(middle_pane, text="Content:").grid(row=1, column=4, sticky=tk.W, padx=(15, 5), pady=5)
        adult_combo = ttk.Combobox(
            middle_pane,
            textvariable=adult_filter_var,
            values=["All", "Adult Only"],
            state="readonly",
            width=12
        )
        adult_combo.grid(row=1, column=5, sticky=tk.W, **pad)
        adult_filter_var.trace_add("write", self.main_window._auto_save_config)

        # Store variables in main window
        self.main_window.hide_sold_var = hide_sold_var
        self.main_window.results_per_page_var = results_per_page_var
        self.main_window.max_pages_var = max_pages_var
        self.main_window.recent_hours_var = recent_hours_var
        self.main_window.language_var = language_var
        self.main_window.condition_var = condition_var
        self.main_window.adult_filter_var = adult_filter_var

        return middle_pane

    def _create_configs_pane(self, parent: ttk.Frame) -> ttk.Frame:
        """
        Create the configs pane with tree view and buttons.
        
        Args:
            parent: The parent frame
            
        Returns:
            The configs pane frame
        """
        bottom_pane = ttk.Frame(parent)
        bottom_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Configs/Schedules tabbed interface
        config_schedule_notebook = ttk.Notebook(bottom_pane)
        config_schedule_notebook.grid(row=0, column=0, columnspan=7, sticky=tk.NSEW, padx=3, pady=4)

        # Configs tab
        tree_frame = ttk.Frame(config_schedule_notebook)
        config_schedule_notebook.add(tree_frame, text="Configs")

        # Create config tree
        config_tree = self._create_config_tree(tree_frame)
        self.main_window.config_tree = config_tree

        # Schedules tab
        from gui.schedule_frame import ScheduleFrame
        schedule_frame = ScheduleFrame(config_schedule_notebook, self.main_window.schedule_executor)
        config_schedule_notebook.add(schedule_frame, text="Schedules")
        self.main_window.schedule_frame = schedule_frame

        # Bind tab change event
        config_schedule_notebook.bind("<<NotebookTabChanged>>", self.main_window._on_config_schedule_tab_changed)
        self.main_window.config_schedule_notebook = config_schedule_notebook

        # Config management buttons
        self._create_config_buttons(bottom_pane)

        # Action buttons for Mandarake scraper
        self._create_action_buttons(bottom_pane)

        # Configure bottom pane grid
        bottom_pane.rowconfigure(0, weight=1)
        for i in range(7):
            bottom_pane.columnconfigure(i, weight=1)

        return bottom_pane

    def _create_config_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        """
        Create the configuration tree view.
        
        Args:
            parent: The parent frame
            
        Returns:
            The config tree widget
        """
        # Store filter row
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Store Filter:").pack(side=tk.LEFT, padx=(0, 5))
        config_store_filter = tk.StringVar(value='All')
        store_filter_combo = ttk.Combobox(filter_frame, textvariable=config_store_filter,
                                          values=['All', 'Mandarake', 'Suruga-Ya'], state='readonly', width=12)
        store_filter_combo.pack(side=tk.LEFT)
        store_filter_combo.bind('<<ComboboxSelected>>', lambda e: self.main_window._filter_config_tree())
        self.main_window.config_store_filter = config_store_filter

        # Create tree
        columns = ('store', 'keyword', 'category', 'shop', 'hide_sold', 'results_per_page', 'max_pages', 'latest_additions', 'language', 'file')
        config_tree = ttk.Treeview(parent, columns=columns, show='headings', height=6)
        
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
            config_tree.heading(col, text=heading)
            width = widths.get(col, 100)
            config_tree.column(col, width=width, stretch=False)

        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=config_tree.yview)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=config_tree.xview)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        # Bind events
        config_tree.bind('<<TreeviewSelect>>', self.main_window._on_config_selected)
        config_tree.bind("<Button-1>", lambda e: self.main_window._deselect_if_empty(e, config_tree))

        # Add right-click context menu
        config_tree_menu = tk.Menu(config_tree, tearoff=0)
        config_tree_menu.add_command(label="Load CSV", command=self.main_window._load_csv_from_config)
        config_tree.bind("<Button-3>", self.main_window._show_config_tree_menu)
        self.main_window.config_tree_menu = config_tree_menu

        # Double-click to edit category
        config_tree.bind("<Double-Button-1>", self.main_window._on_config_tree_double_click)

        # Enable column drag-to-reorder
        self.main_window._setup_column_drag(config_tree)

        return config_tree

    def _create_config_buttons(self, parent: ttk.Frame) -> ttk.Frame:
        """
        Create configuration management buttons.
        
        Args:
            parent: The parent frame
            
        Returns:
            The buttons frame
        """
        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=1, column=0, columnspan=5, sticky=tk.W, padx=3, pady=4)
        
        ttk.Button(buttons_frame, text="New Config", command=self.main_window._new_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Delete Selected", command=self.main_window._delete_selected_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Move Up", command=lambda: self.main_window._move_config(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Move Down", command=lambda: self.main_window._move_config(1)).pack(side=tk.LEFT, padx=5)
        
        self.main_window.config_buttons_frame = buttons_frame
        return buttons_frame

    def _create_action_buttons(self, parent: ttk.Frame) -> ttk.Frame:
        """
        Create action buttons for scraper operations.
        
        Args:
            parent: The parent frame
            
        Returns:
            The action buttons frame
        """
        action_buttons_frame = ttk.Frame(parent)
        action_buttons_frame.grid(row=2, column=0, columnspan=5, sticky=tk.W, padx=3, pady=4)
        
        ttk.Button(action_buttons_frame, text="Search Store", command=self.main_window.run_now).pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(action_buttons_frame, text="Cancel Search", command=self.main_window.cancel_search, state='disabled')
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        self.main_window.action_buttons_frame = action_buttons_frame
        self.main_window.cancel_button = cancel_button
        return action_buttons_frame

    def create_advanced_tab_content(self, parent: ttk.Frame) -> Dict[str, Any]:
        """
        Create the content for the Advanced tab.
        
        Args:
            parent: The parent frame for the advanced tab
            
        Returns:
            Dictionary containing all created widgets
        """
        widgets = {}
        pad = {"padx": 5, "pady": 4}
        current_row = 0

        # Scraper Options Section
        ttk.Label(parent, text="Scraper Options", font=('TkDefaultFont', 9, 'bold')).grid(
            row=current_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(0, 5))
        current_row += 1

        fast_var = tk.BooleanVar(value=False)
        resume_var = tk.BooleanVar(value=True)
        debug_var = tk.BooleanVar(value=False)
        mimic_var = tk.BooleanVar(value=True)  # Enable by default for Unicode support

        ttk.Checkbutton(parent, text="Fast mode (skip eBay)", variable=fast_var).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(parent, text="Resume interrupted runs", variable=resume_var).grid(
            row=current_row, column=1, sticky=tk.W, **pad)
        current_row += 1

        ttk.Checkbutton(parent, text="Debug logging", variable=debug_var).grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        ttk.Checkbutton(parent, text="Use browser mimic (recommended for Japanese text)",
                       variable=mimic_var).grid(
            row=current_row, column=1, columnspan=2, sticky=tk.W, **pad)
        mimic_var.trace_add('write', self.main_window._on_mimic_changed)
        current_row += 1

        # Max CSV items control
        ttk.Label(parent, text="Max CSV items (0 = unlimited):").grid(
            row=current_row, column=0, sticky=tk.W, **pad)
        max_csv_items_var = tk.StringVar(value=str(self.main_window.settings.get_setting('scraper.max_csv_items', 0)))
        max_csv_entry = ttk.Entry(parent, textvariable=max_csv_items_var, width=10)
        max_csv_entry.grid(row=current_row, column=1, sticky=tk.W, **pad)
        max_csv_items_var.trace_add('write', self.main_window._on_max_csv_items_changed)
        current_row += 1

        # Store variables
        widgets['fast_var'] = fast_var
        widgets['resume_var'] = resume_var
        widgets['debug_var'] = debug_var
        widgets['mimic_var'] = mimic_var
        widgets['max_csv_items_var'] = max_csv_items_var

        # Add more sections as needed...
        # (eBay Search Method, Marketplace Toggles, Scheduling, Output Settings, etc.)

        return widgets
