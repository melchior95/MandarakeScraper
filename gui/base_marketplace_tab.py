"""
Base Marketplace Tab

Abstract base class for all marketplace tabs (Mandarake, Suruga-ya, DejaJapan, etc.)
Provides common UI framework and functionality.
"""

import queue
import threading
import tkinter as tk
from abc import ABC, abstractmethod
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from PIL import Image, ImageTk


class BaseMarketplaceTab(ttk.Frame, ABC):
    """
    Abstract base class for marketplace tabs

    Provides:
    - Common UI layout (search controls, results tree, filters)
    - Thumbnail loading and caching
    - CSV export functionality
    - Alert system integration
    - Thread management for background operations

    Subclasses must implement:
    - _create_marketplace_specific_controls()
    - _search_worker()
    - _build_search_params()
    """

    def __init__(self, parent, settings_manager, alert_manager, marketplace_name: str):
        """
        Initialize base marketplace tab

        Args:
            parent: Parent notebook widget
            settings_manager: SettingsManager instance
            alert_manager: AlertManager instance
            marketplace_name: Display name (e.g., "Suruga-ya", "DejaJapan")
        """
        super().__init__(parent)
        self.parent = parent
        self.settings = settings_manager
        self.alert_manager = alert_manager
        self.marketplace_name = marketplace_name

        # State management
        self.results_data = []  # All results
        self.images = {}  # Image cache for thumbnails
        self.worker_thread = None
        self.is_searching = False

        # Communication queue for thread-safe UI updates
        self.queue = queue.Queue()

        # Create UI
        self._create_ui()

        # Start queue processor
        self._process_queue()

    def _create_ui(self):
        """Create the complete UI layout"""
        # Configure grid layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Results area gets weight

        # Padding style
        pad = {'padx': 5, 'pady': 5}

        # Title
        title_label = ttk.Label(
            self,
            text=f"{self.marketplace_name} Search",
            font=('TkDefaultFont', 10, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W, **pad)

        # Search controls (implemented by subclass)
        search_frame = ttk.LabelFrame(self, text="Search", padding=10)
        search_frame.grid(row=1, column=0, sticky=tk.EW, **pad)
        search_frame.columnconfigure(1, weight=1)

        self._create_search_controls(search_frame)

        # Progress bar
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.grid(row=2, column=0, sticky=tk.EW, **pad)
        self.progress.grid_remove()  # Hidden by default

        # Results treeview
        results_frame = ttk.LabelFrame(self, text="Results", padding=5)
        results_frame.grid(row=3, column=0, sticky=tk.NSEW, **pad)
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        self._create_results_tree(results_frame)

        # Action buttons
        actions_frame = ttk.Frame(self)
        actions_frame.grid(row=4, column=0, sticky=tk.EW, **pad)

        self._create_action_buttons(actions_frame)

        # Status bar
        self.status_var = tk.StringVar(value=f"Ready to search {self.marketplace_name}")
        status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor='w'
        )
        status_label.grid(row=5, column=0, sticky=tk.EW)

    def _create_search_controls(self, parent):
        """
        Create search control widgets

        Subclasses override to add marketplace-specific controls
        """
        pad = {'padx': 5, 'pady': 3}

        # Keyword (common to all marketplaces)
        ttk.Label(parent, text="Keyword:").grid(row=0, column=0, sticky=tk.W, **pad)
        self.keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(parent, textvariable=self.keyword_var, width=40)
        keyword_entry.grid(row=0, column=1, sticky=tk.EW, **pad)
        keyword_entry.bind('<Return>', lambda e: self.search())

        # Max results
        ttk.Label(parent, text="Max results:").grid(row=0, column=2, sticky=tk.W, **pad)
        self.max_results_var = tk.StringVar(value="50")
        max_results_combo = ttk.Combobox(
            parent,
            textvariable=self.max_results_var,
            values=['10', '20', '50', '100', '200'],
            width=8,
            state='readonly'
        )
        max_results_combo.grid(row=0, column=3, sticky=tk.W, **pad)

        # Search and Clear buttons
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, **pad)

        ttk.Button(
            button_frame,
            text="Search",
            command=self.search
        ).grid(row=0, column=0, **pad)

        ttk.Button(
            button_frame,
            text="Clear Results",
            command=self.clear_results
        ).grid(row=0, column=1, **pad)

        # Marketplace-specific controls
        self._create_marketplace_specific_controls(parent, start_row=2)

    @abstractmethod
    def _create_marketplace_specific_controls(self, parent, start_row: int):
        """
        Create marketplace-specific controls (override in subclass)

        Args:
            parent: Parent frame
            start_row: Row to start adding controls
        """
        pass

    def _create_results_tree(self, parent):
        """Create results treeview with columns"""
        # Define columns (subclass can customize)
        columns = self._get_tree_columns()

        # Create treeview with thumbnail column
        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show='tree headings',
            height=12
        )

        # Configure thumbnail column
        self.tree.heading('#0', text='Image')
        self.tree.column('#0', width=80, stretch=False)

        # Configure data columns
        column_widths = self._get_column_widths()
        for col in columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            width = column_widths.get(col, 150)
            self.tree.column(col, width=width, stretch=False)

        # Scrollbars
        v_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scroll.grid(row=0, column=1, sticky=tk.NS)
        h_scroll.grid(row=1, column=0, sticky=tk.EW)

        # Double-click to open URL
        self.tree.bind('<Double-1>', self._on_item_double_click)

        # Set row height for thumbnails
        style = ttk.Style()
        style.configure('Treeview', rowheight=70)

    def _get_tree_columns(self) -> tuple:
        """Get column names for results tree (override in subclass)"""
        return ('title', 'price', 'condition', 'stock_status')

    def _get_column_widths(self) -> Dict[str, int]:
        """Get column widths (override in subclass)"""
        return {
            'title': 300,
            'price': 80,
            'condition': 80,
            'stock_status': 100
        }

    def _create_action_buttons(self, parent):
        """Create action buttons"""
        pad = {'padx': 5, 'pady': 3}

        ttk.Button(
            parent,
            text="Export to CSV",
            command=self.export_csv
        ).grid(row=0, column=0, **pad)

        ttk.Button(
            parent,
            text="Send to Alerts",
            command=self.send_to_alerts
        ).grid(row=0, column=1, **pad)

        ttk.Button(
            parent,
            text="Open Selected URL",
            command=self._open_selected_url
        ).grid(row=0, column=2, **pad)

    # ========================================================================
    # Search Methods
    # ========================================================================

    def search(self):
        """Start search (runs in background thread)"""
        if self.is_searching:
            messagebox.showwarning("Search in Progress", "Please wait for current search to complete")
            return

        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showwarning("Missing Keyword", "Please enter a search keyword")
            return

        # Clear previous results
        self.clear_results()

        # Show progress
        self.progress.grid()
        self.progress.start()
        self.is_searching = True
        self.status_var.set(f"Searching {self.marketplace_name}...")

        # Start background thread
        self.worker_thread = threading.Thread(target=self._search_worker, daemon=True)
        self.worker_thread.start()

    @abstractmethod
    def _search_worker(self):
        """
        Background worker for search (override in subclass)

        Should:
        1. Perform search using scraper
        2. Post results to queue: self.queue.put(('results', results_list))
        3. Post status updates: self.queue.put(('status', message))
        4. Post completion: self.queue.put(('complete', None))
        """
        pass

    # ========================================================================
    # Results Display
    # ========================================================================

    def _display_results(self, results: List[Dict]):
        """
        Display results in treeview

        Args:
            results: List of result dictionaries
        """
        self.results_data = results

        for i, item in enumerate(results):
            # Prepare values for tree columns
            values = self._format_tree_values(item)

            # Load thumbnail
            photo = None
            image_url = item.get('thumbnail_url') or item.get('image_url')
            if image_url:
                try:
                    photo = self._load_thumbnail(image_url, size=(60, 60))
                    self.images[str(i)] = photo
                except Exception as e:
                    print(f"[{self.marketplace_name}] Failed to load thumbnail: {e}")

            # Insert into tree
            if photo:
                self.tree.insert('', 'end', iid=str(i), text='', values=values, image=photo)
            else:
                self.tree.insert('', 'end', iid=str(i), text=str(i+1), values=values)

        print(f"[{self.marketplace_name}] Displayed {len(results)} results")

    @abstractmethod
    def _format_tree_values(self, item: Dict) -> tuple:
        """
        Format item data for tree display (override in subclass)

        Args:
            item: Result dictionary

        Returns:
            Tuple of values matching tree columns
        """
        pass

    def _load_thumbnail(self, url: str, size: tuple = (60, 60)) -> ImageTk.PhotoImage:
        """
        Load and resize thumbnail from URL

        Args:
            url: Image URL
            size: Target size (width, height)

        Returns:
            PhotoImage object
        """
        import requests
        from io import BytesIO

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))
        image.thumbnail(size, Image.Resampling.LANCZOS)

        return ImageTk.PhotoImage(image)

    def clear_results(self):
        """Clear all results"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data = []
        self.images.clear()

    # ========================================================================
    # Queue Processing (Thread-Safe UI Updates)
    # ========================================================================

    def _process_queue(self):
        """Process queue messages (runs in main thread)"""
        try:
            while True:
                msg_type, payload = self.queue.get_nowait()

                if msg_type == 'results':
                    self._display_results(payload)
                elif msg_type == 'status':
                    self.status_var.set(payload)
                elif msg_type == 'complete':
                    self._search_complete()
                elif msg_type == 'error':
                    messagebox.showerror("Search Error", payload)
                    self._search_complete()

        except queue.Empty:
            pass

        # Schedule next check
        self.after(100, self._process_queue)

    def _search_complete(self):
        """Called when search completes"""
        self.progress.stop()
        self.progress.grid_remove()
        self.is_searching = False

    # ========================================================================
    # Actions
    # ========================================================================

    def export_csv(self):
        """Export results to CSV"""
        if not self.results_data:
            messagebox.showinfo("No Data", "No results to export")
            return

        filepath = filedialog.asksaveasfilename(
            title="Export to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.marketplace_name.lower()}_results.csv"
        )

        if not filepath:
            return

        try:
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                if self.results_data:
                    writer = csv.DictWriter(f, fieldnames=self.results_data[0].keys())
                    writer.writeheader()
                    writer.writerows(self.results_data)

            messagebox.showinfo("Export Complete", f"Exported {len(self.results_data)} items to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export: {e}")

    def send_to_alerts(self):
        """Send selected results to Alert tab"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select items to send to alerts")
            return

        count = 0
        for item_id in selection:
            try:
                index = int(item_id)
                if 0 <= index < len(self.results_data):
                    item = self.results_data[index]
                    # Convert to alert format
                    alert_item = self._convert_to_alert_format(item)
                    # Add to alert manager (assuming it has an add method)
                    if hasattr(self.alert_manager, 'add_item'):
                        self.alert_manager.add_item(alert_item)
                        count += 1
            except (ValueError, IndexError):
                continue

        if count > 0:
            messagebox.showinfo("Added to Alerts", f"Added {count} items to alerts")

    def _convert_to_alert_format(self, item: Dict) -> Dict:
        """Convert result item to alert format (override if needed)"""
        return {
            'title': item.get('title', ''),
            'price': item.get('price', 0),
            'url': item.get('url', ''),
            'image_url': item.get('image_url', ''),
            'marketplace': self.marketplace_name,
            'status': 'Pending'
        }

    def _open_selected_url(self):
        """Open selected item URL in browser"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            index = int(selection[0])
            if 0 <= index < len(self.results_data):
                url = self.results_data[index].get('url')
                if url:
                    import webbrowser
                    webbrowser.open(url)
        except (ValueError, IndexError):
            pass

    def _on_item_double_click(self, event):
        """Handle double-click on tree item"""
        self._open_selected_url()
