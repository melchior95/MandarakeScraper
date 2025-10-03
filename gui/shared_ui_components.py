"""Reusable UI components for store tabs"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional, List, Tuple


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

        self.main_categories = main_categories
        self.detailed_categories = detailed_categories
        self.shops = shops

        # Main category dropdown
        ttk.Label(self, text="Main Category:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.main_category_var = tk.StringVar()
        self.main_category_combo = ttk.Combobox(
            self,
            textvariable=self.main_category_var,
            values=self._format_category_list(main_categories),
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

    def _format_category_list(self, categories: Dict) -> List[str]:
        """Format categories as 'code - name' for display"""
        return [f"{code} - {name}" for code, name in sorted(categories.items())]

    def _populate_categories(self, categories: Dict):
        for code, name in sorted(categories.items()):
            self.category_listbox.insert(tk.END, f"{code} - {name}")

    def _populate_shops(self, shops: Dict):
        for code, name in sorted(shops.items()):
            self.shop_listbox.insert(tk.END, f"{code} - {name}")

    def get_selected_category_code(self) -> str:
        """Get selected detailed category code"""
        cat_selection = self.category_listbox.curselection()
        if cat_selection:
            text = self.category_listbox.get(cat_selection[0])
            return text.split(' - ')[0]
        return ''

    def get_selected_shop_code(self) -> str:
        """Get selected shop code"""
        shop_selection = self.shop_listbox.curselection()
        if shop_selection:
            text = self.shop_listbox.get(shop_selection[0])
            return text.split(' - ')[0]
        return ''

    def get_values(self) -> Dict[str, str]:
        # Get selected main category
        main_cat = self.main_category_var.get()
        main_cat_code = main_cat.split(' - ')[0] if ' - ' in main_cat else main_cat

        return {
            'main_category': main_cat_code,
            'category': self.get_selected_category_code(),
            'shop': self.get_selected_shop_code()
        }

    def set_category(self, category_code: str):
        """Select category by code"""
        for i in range(self.category_listbox.size()):
            text = self.category_listbox.get(i)
            if text.startswith(category_code + ' - '):
                self.category_listbox.selection_clear(0, tk.END)
                self.category_listbox.selection_set(i)
                self.category_listbox.see(i)
                break

    def set_shop(self, shop_code: str):
        """Select shop by code"""
        for i in range(self.shop_listbox.size()):
            text = self.shop_listbox.get(i)
            if text.startswith(shop_code + ' - '):
                self.shop_listbox.selection_clear(0, tk.END)
                self.shop_listbox.selection_set(i)
                self.shop_listbox.see(i)
                break


class StoreOptionsPanel(ttk.LabelFrame):
    """Store-specific options panel (dynamic based on store)"""

    def __init__(self, parent):
        super().__init__(parent, text="Options", padding=5)
        self.options = {}

    def add_checkbox(self, key: str, label: str, default: bool = False) -> tk.BooleanVar:
        var = tk.BooleanVar(value=default)
        chk = ttk.Checkbutton(self, text=label, variable=var)
        chk.pack(anchor=tk.W, padx=5, pady=2)
        self.options[key] = var
        return var

    def add_spinbox(self, key: str, label: str, from_: int, to: int, default: int) -> tk.IntVar:
        frame = ttk.Frame(self)
        frame.pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        var = tk.IntVar(value=default)
        spin = ttk.Spinbox(frame, from_=from_, to=to, textvariable=var, width=10)
        spin.pack(side=tk.LEFT, padx=5)
        self.options[key] = var
        return var

    def add_combobox(self, key: str, label: str, values: List[str], default: str = '') -> tk.StringVar:
        frame = ttk.Frame(self)
        frame.pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(frame, textvariable=var, values=values, width=20, state='readonly')
        combo.pack(side=tk.LEFT, padx=5)
        self.options[key] = var
        return var

    def get_values(self) -> Dict:
        return {key: var.get() for key, var in self.options.items()}

    def set_values(self, values: Dict):
        for key, value in values.items():
            if key in self.options:
                self.options[key].set(value)
