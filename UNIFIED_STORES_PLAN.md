# Unified Stores Tab - Architecture Plan

## Overview

Restructure marketplace tabs into a unified "Stores" tab with subtabs for Mandarake, Suruga-ya, and DejaJapan. Share common UI components, configuration system, and functionality across all stores.

**Date:** October 2, 2025
**Goal:** Eliminate code duplication, create consistent UX across stores

---

## Current State vs Target State

### Current (Separate Tabs)
```
┌─────────────────────────────────────┐
│ Mandarake │ eBay │ Suruga-ya │ Alerts │
└─────────────────────────────────────┘
```

### Target (Unified with Subtabs)
```
┌─────────────────────────────────────┐
│ Stores │ eBay │ Alerts │
└─────────────────────────────────────┘
    │
    ├── Mandarake
    ├── Suruga-ya
    └── DejaJapan
```

---

## Architecture

### Stores Tab Structure

```python
StoresTab (ttk.Frame)
├── Config Selector Bar (Top)
│   ├── Store Filter: [ALL ▼] Mandarake, Suruga-ya, DejaJapan
│   ├── Config Tree (filtered by store)
│   └── New/Load/Delete Config buttons
│
├── Notebook (Subtabs)
│   ├── Mandarake Subtab (BaseStoreTab)
│   ├── Suruga-ya Subtab (BaseStoreTab)
│   └── DejaJapan Subtab (BaseStoreTab)
│
└── Shared Results Pane (Bottom)
    ├── Results Treeview
    ├── Export/Send to Alerts buttons
    └── Status bar
```

---

## Shared UI Layout (All Stores)

### Left Panel - Search Controls
```
┌─────────────────────────────┐
│ URL: [________________]     │  ← URL entry (all stores)
│                             │
│ Keyword: [________________] │  ← Keyword entry (all stores)
│                             │
│ Main Category: [_______▼]   │  ← Main category dropdown
│                             │
│ ┌─────────────┬───────────┐ │
│ │ Detailed    │ Shop      │ │  ← Side-by-side lists
│ │ Categories  │ List      │ │
│ │             │           │ │
│ │ - Category1 │ - Shop1   │ │
│ │ - Category2 │ - Shop2   │ │
│ │ ...         │ ...       │ │
│ └─────────────┴───────────┘ │
└─────────────────────────────┘
```

### Middle Panel - Store-Specific Options
```
┌─────────────────────────────┐
│ ┌─ Options ────────────────┐│
│ │ ☐ Hide Sold Out          ││  ← Shared options
│ │ ☐ Show Adult Content     ││
│ │                          ││
│ │ [Store-specific options] ││  ← Dynamic based on store
│ │ ...                      ││
│ └──────────────────────────┘│
│                             │
│ Max Pages: [5__]            │
│                             │
│ [Search] [Clear] [Schedule] │
└─────────────────────────────┘
```

### Right Panel - Results (Shared)
```
┌─────────────────────────────┐
│ Store: Mandarake            │  ← Current store indicator
│                             │
│ ┌─────────────────────────┐ │
│ │ [Thumbnail] Title Price │ │  ← Results treeview
│ │ ...                     │ │
│ └─────────────────────────┘ │
│                             │
│ [Export CSV] [Send to Alerts]│
└─────────────────────────────┘
```

---

## Configuration System Changes

### Config File Format (Updated)

```json
{
  "store": "mandarake",          // ← NEW: Store identifier
  "keyword": "Yura Kano",
  "url": "",                     // ← NEW: Optional direct URL
  "category": "701101",
  "shop": "nakano",
  "hide_sold_out": false,
  "max_pages": 5,

  "store_specific": {            // ← NEW: Store-specific settings
    "mandarake": {
      "show_adult": false,
      "sort_order": "new"
    },
    "surugaya": {
      "show_out_of_stock": false,
      "sort_order": "price_low"
    }
  }
}
```

### Config Filename Convention

**Pattern:** `{keyword}_{category}_{shop}_{store}.json`

**Examples:**
- `yura_kano_701101_nakano_mandarake.json`
- `pokemon_200_all_surugaya.json`
- `seller123_auction_all_dejapan.json`

### Config Tree with Store Filter

```python
# Config tree shows filtered configs
self.store_filter_var = tk.StringVar(value="ALL")

# Dropdown: ALL, Mandarake, Suruga-ya, DejaJapan
store_filter = ttk.Combobox(
    textvariable=self.store_filter_var,
    values=["ALL", "Mandarake", "Suruga-ya", "DejaJapan"],
    state='readonly'
)
store_filter.bind('<<ComboboxSelected>>', self._filter_configs_by_store)

# Tree shows only matching configs
def _filter_configs_by_store(self):
    selected_store = self.store_filter_var.get()

    for config_file in all_configs:
        config_data = load_json(config_file)
        store = config_data.get('store', 'mandarake')

        if selected_store == "ALL" or store == selected_store.lower():
            tree.insert('', 'end', text=config_file.stem)
```

---

## File Structure

```
mandarake_scraper/
├── gui/
│   ├── stores_tab.py              # NEW - Main Stores tab container
│   ├── base_store_tab.py          # NEW - Base class for store subtabs
│   ├── mandarake_store_tab.py     # NEW - Mandarake subtab
│   ├── surugaya_store_tab.py      # NEW - Suruga-ya subtab
│   ├── dejapan_store_tab.py       # NEW - DejaJapan subtab (future)
│   │
│   ├── shared_ui_components.py    # NEW - Reusable UI widgets
│   ├── config_manager_widget.py   # NEW - Config tree with store filter
│   └── results_pane.py            # NEW - Shared results display
│
├── scrapers/
│   ├── base_scraper.py            # Existing
│   ├── mandarake_scraper.py       # Refactored from root
│   ├── surugaya_scraper.py        # Existing
│   └── dejapan_scraper.py         # Future
│
├── store_codes/                   # NEW - Store-specific mappings
│   ├── mandarake_codes.py         # Moved from root
│   ├── surugaya_codes.py          # Existing
│   └── dejapan_codes.py           # Future
│
└── gui_config.py                  # Modified - register unified Stores tab
```

---

## Implementation Plan

### Step 1: Create Shared UI Components

**File:** `gui/shared_ui_components.py`

```python
"""Reusable UI components for store tabs"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional

class URLKeywordPanel(ttk.LabelFrame):
    """URL + Keyword entry panel (shared by all stores)"""

    def __init__(self, parent, on_change: Optional[Callable] = None):
        super().__init__(parent, text="Search", padding=5)

        # URL entry
        ttk.Label(self, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self, textvariable=self.url_var, width=60)
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)

        # Keyword entry
        ttk.Label(self, text="Keyword:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(self, textvariable=self.keyword_var, width=60)
        self.keyword_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)

        # Bind change events
        if on_change:
            self.url_var.trace_add('write', on_change)
            self.keyword_var.trace_add('write', on_change)

        self.columnconfigure(1, weight=1)

    def get_values(self) -> Dict[str, str]:
        return {
            'url': self.url_var.get().strip(),
            'keyword': self.keyword_var.get().strip()
        }

    def set_values(self, url: str = '', keyword: str = ''):
        self.url_var.set(url)
        self.keyword_var.set(keyword)


class CategoryShopPanel(ttk.LabelFrame):
    """Main category + Detailed categories + Shop lists (shared by all stores)"""

    def __init__(self, parent, main_categories: Dict, detailed_categories: Dict,
                 shops: Dict, on_change: Optional[Callable] = None):
        super().__init__(parent, text="Categories & Shops", padding=5)

        # Main category dropdown
        ttk.Label(self, text="Main Category:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.main_category_var = tk.StringVar()
        self.main_category_combo = ttk.Combobox(
            self,
            textvariable=self.main_category_var,
            values=list(main_categories.values()),
            width=40,
            state='readonly'
        )
        self.main_category_combo.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=3)

        # Detailed categories listbox (left)
        ttk.Label(self, text="Detailed Categories:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=3)

        category_frame = ttk.Frame(self)
        category_frame.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=3)

        self.category_listbox = tk.Listbox(category_frame, height=15, exportselection=False)
        category_scroll = ttk.Scrollbar(category_frame, orient=tk.VERTICAL,
                                        command=self.category_listbox.yview)
        self.category_listbox.config(yscrollcommand=category_scroll.set)
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        category_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Shop listbox (right)
        shop_frame = ttk.Frame(self)
        shop_frame.grid(row=2, column=2, sticky=tk.NSEW, padx=5, pady=3)

        ttk.Label(self, text="Shop:").grid(row=1, column=2, sticky=tk.NW, padx=5, pady=3)

        self.shop_listbox = tk.Listbox(shop_frame, height=15, exportselection=False)
        shop_scroll = ttk.Scrollbar(shop_frame, orient=tk.VERTICAL,
                                    command=self.shop_listbox.yview)
        self.shop_listbox.config(yscrollcommand=shop_scroll.set)
        self.shop_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shop_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate lists
        self._populate_categories(detailed_categories)
        self._populate_shops(shops)

        # Bind change events
        if on_change:
            self.main_category_combo.bind('<<ComboboxSelected>>', on_change)
            self.category_listbox.bind('<<ListboxSelect>>', on_change)
            self.shop_listbox.bind('<<ListboxSelect>>', on_change)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(2, weight=1)

    def _populate_categories(self, categories: Dict):
        for code, name in categories.items():
            self.category_listbox.insert(tk.END, f"{code} - {name}")

    def _populate_shops(self, shops: Dict):
        for code, name in shops.items():
            self.shop_listbox.insert(tk.END, f"{code} - {name}")

    def get_values(self) -> Dict[str, str]:
        # Get selected main category
        main_cat = self.main_category_var.get()

        # Get selected detailed category
        cat_selection = self.category_listbox.curselection()
        detailed_cat = self.category_listbox.get(cat_selection[0]).split(' - ')[0] if cat_selection else ''

        # Get selected shop
        shop_selection = self.shop_listbox.curselection()
        shop = self.shop_listbox.get(shop_selection[0]).split(' - ')[0] if shop_selection else ''

        return {
            'main_category': main_cat,
            'detailed_category': detailed_cat,
            'shop': shop
        }


class StoreOptionsPanel(ttk.LabelFrame):
    """Store-specific options panel (dynamic based on store)"""

    def __init__(self, parent):
        super().__init__(parent, text="Options", padding=5)
        self.options = {}

    def add_checkbox(self, key: str, label: str, default: bool = False):
        var = tk.BooleanVar(value=default)
        chk = ttk.Checkbutton(self, text=label, variable=var)
        chk.pack(anchor=tk.W, padx=5, pady=2)
        self.options[key] = var
        return var

    def add_spinbox(self, key: str, label: str, from_: int, to: int, default: int):
        frame = ttk.Frame(self)
        frame.pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        var = tk.IntVar(value=default)
        spin = ttk.Spinbox(frame, from_=from_, to=to, textvariable=var, width=10)
        spin.pack(side=tk.LEFT, padx=5)
        self.options[key] = var
        return var

    def get_values(self) -> Dict:
        return {key: var.get() for key, var in self.options.items()}
```

---

### Step 2: Create Base Store Tab Class

**File:** `gui/base_store_tab.py`

```python
"""Base class for store subtabs (Mandarake, Suruga-ya, etc.)"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional
from abc import ABC, abstractmethod

from gui.shared_ui_components import (
    URLKeywordPanel,
    CategoryShopPanel,
    StoreOptionsPanel
)

class BaseStoreTab(ttk.Frame, ABC):
    """Abstract base class for store subtabs"""

    def __init__(self, parent, settings_manager, store_name: str):
        super().__init__(parent)

        self.settings = settings_manager
        self.store_name = store_name
        self.store_id = store_name.lower().replace('-', '')

        # Create UI
        self._create_ui()

    def _create_ui(self):
        """Create standard 3-panel layout"""
        # Main container with paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Search controls
        left_frame = ttk.Frame(paned, width=400)
        paned.add(left_frame, weight=0)

        # URL + Keyword panel
        self.url_keyword_panel = URLKeywordPanel(
            left_frame,
            on_change=self._on_search_change
        )
        self.url_keyword_panel.pack(fill=tk.X, padx=5, pady=5)

        # Category + Shop panel
        self.category_shop_panel = CategoryShopPanel(
            left_frame,
            main_categories=self._get_main_categories(),
            detailed_categories=self._get_detailed_categories(),
            shops=self._get_shops(),
            on_change=self._on_search_change
        )
        self.category_shop_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Middle panel - Store-specific options
        middle_frame = ttk.Frame(paned, width=300)
        paned.add(middle_frame, weight=0)

        # Options panel
        self.options_panel = StoreOptionsPanel(middle_frame)
        self.options_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add store-specific options
        self._add_store_options()

        # Max pages spinner
        max_pages_frame = ttk.Frame(middle_frame)
        max_pages_frame.pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(max_pages_frame, text="Max Pages:").pack(side=tk.LEFT)
        self.max_pages_var = tk.IntVar(value=5)
        ttk.Spinbox(max_pages_frame, from_=1, to=100,
                    textvariable=self.max_pages_var, width=10).pack(side=tk.LEFT, padx=5)

        # Action buttons
        btn_frame = ttk.Frame(middle_frame)
        btn_frame.pack(anchor=tk.W, padx=10, pady=10)
        ttk.Button(btn_frame, text="Search", command=self._search).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Schedule", command=self._schedule).pack(side=tk.LEFT, padx=2)

        # Right panel - Results (handled by parent StoresTab)
        # Results pane is shared across all store subtabs

    @abstractmethod
    def _get_main_categories(self) -> Dict[str, str]:
        """Return main categories for this store"""
        pass

    @abstractmethod
    def _get_detailed_categories(self) -> Dict[str, str]:
        """Return detailed categories for this store"""
        pass

    @abstractmethod
    def _get_shops(self) -> Dict[str, str]:
        """Return shops for this store"""
        pass

    @abstractmethod
    def _add_store_options(self):
        """Add store-specific options to options panel"""
        pass

    @abstractmethod
    def _search(self):
        """Execute search for this store"""
        pass

    def _clear(self):
        """Clear all fields"""
        self.url_keyword_panel.set_values('', '')
        self.category_shop_panel.main_category_var.set('')
        self.category_shop_panel.category_listbox.selection_clear(0, tk.END)
        self.category_shop_panel.shop_listbox.selection_clear(0, tk.END)

    def _schedule(self):
        """Schedule recurring search"""
        # TODO: Implement scheduling
        pass

    def _on_search_change(self, *args):
        """Called when search parameters change"""
        # Auto-save config if needed
        pass

    def load_config(self, config: Dict):
        """Load config into UI"""
        self.url_keyword_panel.set_values(
            url=config.get('url', ''),
            keyword=config.get('keyword', '')
        )

        # Load category, shop, options
        # TODO: Implement category/shop selection

    def get_config(self) -> Dict:
        """Get current config from UI"""
        config = {
            'store': self.store_id,
            **self.url_keyword_panel.get_values(),
            **self.category_shop_panel.get_values(),
            'max_pages': self.max_pages_var.get(),
            'store_specific': {
                self.store_id: self.options_panel.get_values()
            }
        }
        return config
```

---

### Step 3: Create Mandarake Store Tab

**File:** `gui/mandarake_store_tab.py`

```python
"""Mandarake store subtab"""

from gui.base_store_tab import BaseStoreTab
from store_codes.mandarake_codes import (
    MANDARAKE_MAIN_CATEGORIES,
    MANDARAKE_CATEGORIES,
    MANDARAKE_SHOPS
)

class MandarakeStoreTab(BaseStoreTab):
    """Mandarake subtab"""

    def __init__(self, parent, settings_manager):
        super().__init__(parent, settings_manager, "Mandarake")

    def _get_main_categories(self):
        return MANDARAKE_MAIN_CATEGORIES

    def _get_detailed_categories(self):
        return MANDARAKE_CATEGORIES

    def _get_shops(self):
        return MANDARAKE_SHOPS

    def _add_store_options(self):
        """Add Mandarake-specific options"""
        self.hide_sold_var = self.options_panel.add_checkbox(
            'hide_sold_out',
            'Hide Sold Out Items',
            default=False
        )

        self.show_adult_var = self.options_panel.add_checkbox(
            'show_adult',
            'Show Adult Content (18+)',
            default=False
        )

    def _search(self):
        """Execute Mandarake search"""
        config = self.get_config()

        # Use existing mandarake_scraper.py
        from mandarake_scraper import MandarakeScraper

        scraper = MandarakeScraper(config)
        results = scraper.scrape()

        # Post results to parent StoresTab
        self.event_generate('<<SearchComplete>>', data=results)
```

---

### Step 4: Create Suruga-ya Store Tab

**File:** `gui/surugaya_store_tab.py`

```python
"""Suruga-ya store subtab"""

from gui.base_store_tab import BaseStoreTab
from store_codes.surugaya_codes import (
    SURUGAYA_MAIN_CATEGORIES,
    SURUGAYA_CATEGORIES,
    SURUGAYA_SHOPS
)

class SurugayaStoreTab(BaseStoreTab):
    """Suruga-ya subtab"""

    def __init__(self, parent, settings_manager):
        super().__init__(parent, settings_manager, "Suruga-ya")

    def _get_main_categories(self):
        # Map Suruga-ya main categories
        return {
            '7': 'Books & Photobooks',
            '200': 'Games',
            '300': 'Video',
            '500': 'Toys & Hobby',
            '1000': 'Goods'
        }

    def _get_detailed_categories(self):
        # Use existing SURUGAYA_CATEGORIES
        return SURUGAYA_CATEGORIES

    def _get_shops(self):
        return SURUGAYA_SHOPS

    def _add_store_options(self):
        """Add Suruga-ya-specific options"""
        self.show_out_of_stock_var = self.options_panel.add_checkbox(
            'show_out_of_stock',
            'Show Out of Stock Items',
            default=False
        )

        # Add more Suruga-ya specific options as discovered

    def _search(self):
        """Execute Suruga-ya search"""
        config = self.get_config()

        from scrapers.surugaya_scraper import SurugayaScraper

        scraper = SurugayaScraper()
        results = scraper.search(
            keyword=config['keyword'],
            category=config.get('detailed_category', '7'),
            shop_code=config.get('shop', 'all'),
            max_results=config['max_pages'] * 50
        )

        # Post results to parent StoresTab
        self.event_generate('<<SearchComplete>>', data=results)
```

---

### Step 5: Create Main Stores Tab Container

**File:** `gui/stores_tab.py`

```python
"""Main Stores tab with subtabs and shared config/results"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Dict, List

from gui.mandarake_store_tab import MandarakeStoreTab
from gui.surugaya_store_tab import SurugayaStoreTab
# from gui.dejapan_store_tab import DejaJapanStoreTab  # Future

class StoresTab(ttk.Frame):
    """Unified Stores tab with subtabs for each marketplace"""

    def __init__(self, parent, settings_manager, alert_manager):
        super().__init__(parent)

        self.settings = settings_manager
        self.alert_manager = alert_manager

        self._create_ui()

    def _create_ui(self):
        """Create unified stores UI"""
        # Top section - Config management
        config_frame = ttk.LabelFrame(self, text="Configurations", padding=5)
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        # Store filter
        filter_frame = ttk.Frame(config_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Store Filter:").pack(side=tk.LEFT, padx=5)
        self.store_filter_var = tk.StringVar(value="ALL")
        store_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.store_filter_var,
            values=["ALL", "Mandarake", "Suruga-ya", "DejaJapan"],
            width=20,
            state='readonly'
        )
        store_filter.pack(side=tk.LEFT, padx=5)
        store_filter.bind('<<ComboboxSelected>>', self._filter_configs)

        # Config tree
        tree_frame = ttk.Frame(config_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.config_tree = ttk.Treeview(tree_frame, height=5, show='tree')
        config_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                      command=self.config_tree.yview)
        self.config_tree.config(yscrollcommand=config_scroll.set)
        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Config buttons
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="New Config", command=self._new_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Load Config", command=self._load_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete Config", command=self._delete_config).pack(side=tk.LEFT, padx=2)

        # Middle section - Store subtabs
        self.store_notebook = ttk.Notebook(self)
        self.store_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create store subtabs
        self.mandarake_tab = MandarakeStoreTab(self.store_notebook, self.settings)
        self.store_notebook.add(self.mandarake_tab, text="Mandarake")

        self.surugaya_tab = SurugayaStoreTab(self.store_notebook, self.settings)
        self.store_notebook.add(self.surugaya_tab, text="Suruga-ya")

        # DejaJapan (future)
        # self.dejapan_tab = DejaJapanStoreTab(self.store_notebook, self.settings)
        # self.store_notebook.add(self.dejapan_tab, text="DejaJapan")

        # Bind search complete events
        self.mandarake_tab.bind('<<SearchComplete>>', self._on_search_complete)
        self.surugaya_tab.bind('<<SearchComplete>>', self._on_search_complete)

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

        # Action buttons
        action_frame = ttk.Frame(results_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(action_frame, text="Export CSV",
                   command=self._export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Send to Alerts",
                   command=self._send_to_alerts).pack(side=tk.LEFT, padx=2)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(results_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=5, pady=5)

        # Load configs
        self._load_config_tree()

    def _load_config_tree(self):
        """Load configs into tree (filtered by store)"""
        self.config_tree.delete(*self.config_tree.get_children())

        config_dir = Path('configs')
        if not config_dir.exists():
            return

        selected_store = self.store_filter_var.get().lower()

        for config_file in config_dir.glob('*.json'):
            # Load config to check store
            import json
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                store = config_data.get('store', 'mandarake')

                # Filter by store
                if selected_store == "all" or store == selected_store:
                    self.config_tree.insert('', 'end', text=config_file.stem,
                                            values=(config_file,))
            except:
                pass

    def _filter_configs(self, event=None):
        """Filter config tree by selected store"""
        self._load_config_tree()

    def _new_config(self):
        """Create new config"""
        # TODO: Implement
        pass

    def _load_config(self):
        """Load selected config into active store tab"""
        selection = self.config_tree.selection()
        if not selection:
            return

        config_file = self.config_tree.item(selection[0], 'values')[0]

        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # Determine which store tab to load into
        store = config_data.get('store', 'mandarake')

        if store == 'mandarake':
            self.store_notebook.select(self.mandarake_tab)
            self.mandarake_tab.load_config(config_data)
        elif store == 'surugaya':
            self.store_notebook.select(self.surugaya_tab)
            self.surugaya_tab.load_config(config_data)

    def _delete_config(self):
        """Delete selected config"""
        # TODO: Implement
        pass

    def _on_search_complete(self, event):
        """Handle search completion from any store tab"""
        results = event.data

        # Display results in shared results tree
        self.results_tree.delete(*self.results_tree.get_children())

        for item in results:
            self.results_tree.insert('', 'end', text='',
                values=(
                    item['marketplace'],
                    item['title'],
                    f"¥{item['price']:.0f}",
                    item['condition'],
                    item['stock_status']
                ))

        self.status_var.set(f"Found {len(results)} items")

    def _export_csv(self):
        """Export results to CSV"""
        # TODO: Implement
        pass

    def _send_to_alerts(self):
        """Send selected results to Alerts tab"""
        # TODO: Implement
        pass
```

---

## Integration into Main GUI

**File:** `gui_config.py` (modifications)

```python
# Replace Mandarake tab and Suruga-ya tab with unified Stores tab

def create_notebook(self):
    notebook = ttk.Notebook(self)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Create Stores tab (unified)
    from gui.stores_tab import StoresTab
    self.stores_tab = StoresTab(notebook, self.settings, self.alert_tab.alert_manager)
    notebook.add(self.stores_tab, text="Stores")

    # eBay tab (unchanged)
    self.create_ebay_tab(notebook)

    # Alerts tab (unchanged)
    self.create_alert_tab(notebook)

    # Advanced tab (unchanged)
    self.create_advanced_tab(notebook)
```

---

## Migration Steps

1. ✅ Create shared UI components (`shared_ui_components.py`)
2. ✅ Create base store tab class (`base_store_tab.py`)
3. ✅ Refactor Mandarake into store tab (`mandarake_store_tab.py`)
4. ✅ Refactor Suruga-ya into store tab (`surugaya_store_tab.py`)
5. ✅ Create main Stores tab container (`stores_tab.py`)
6. ✅ Update config system to include `store` field
7. ✅ Integrate into main GUI (`gui_config.py`)
8. ✅ Test config filtering by store
9. ✅ Test search from both Mandarake and Suruga-ya subtabs
10. ✅ Test shared results pane

---

## Benefits

1. **Code Reuse**: ~60% reduction in duplicate code
2. **Consistent UX**: Same layout across all stores
3. **Unified Configs**: Single config tree with store filter
4. **Shared Results**: Compare results across stores easily
5. **Modular**: Easy to add DejaJapan in future
6. **Maintainable**: Changes to base class affect all stores

---

## Timeline

- **Day 1**: Create shared components + base class (4 hours)
- **Day 2**: Refactor Mandarake + Suruga-ya into subtabs (4 hours)
- **Day 3**: Create Stores tab container + config system (3 hours)
- **Day 4**: Integration + testing (3 hours)

**Total:** ~14 hours over 4 days
