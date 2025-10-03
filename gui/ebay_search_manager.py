#!/usr/bin/env python3
"""eBay Search Manager Module - Handles eBay search operations and results display."""

import threading
import webbrowser
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO

from gui import workers


class EbaySearchManager:
    """Manages eBay search operations and results display."""
    
    def __init__(self, tree_widget, progress_bar, status_var, gui_instance):
        """Initialize the eBay search manager.
        
        Args:
            tree_widget: The ttk.Treeview widget for eBay results
            progress_bar: Progress bar widget
            status_var: StringVar for status updates
            gui_instance: Main GUI instance for callbacks
        """
        self.tree = tree_widget
        self.progress_bar = progress_bar
        self.status_var = status_var
        self.gui = gui_instance
        
        # Results data
        self.results_data: List[Dict[str, Any]] = []
        self.images: Dict[str, ImageTk.PhotoImage] = {}
        
        # Setup tree columns
        self._setup_tree_columns()
        
        # Bind events
        self._bind_events()
    
    def _setup_tree_columns(self):
        """Setup eBay results tree columns and headings."""
        # Create custom style for eBay results treeview with thumbnails
        style = ttk.Style()
        style.configure('Browserless.Treeview', rowheight=70)
        
        self.tree['columns'] = ('title', 'price', 'shipping', 'mandarake_price', 
                               'profit_margin', 'sold_date', 'similarity', 'url')
        self.tree.configure(style='Browserless.Treeview')
        
        # Setup thumbnail column
        self.tree.heading('#0', text='Thumb')
        self.tree.column('#0', width=70, stretch=False)
        
        # Setup data columns
        headings = {
            'title': 'Title',
            'price': 'eBay Price',
            'shipping': 'Shipping',
            'mandarake_price': 'Mandarake ¥',
            'profit_margin': 'Profit %',
            'sold_date': 'Sold Date',
            'similarity': 'Similarity %',
            'url': 'eBay URL'
        }
        
        widths = {
            'title': 280,
            'price': 80,
            'shipping': 70,
            'mandarake_price': 90,
            'profit_margin': 80,
            'sold_date': 100,
            'similarity': 90,
            'url': 180
        }
        
        for col, heading in headings.items():
            self.tree.heading(col, text=heading)
            width = widths.get(col, 100)
            self.tree.column(col, width=width, stretch=False)
    
    def _bind_events(self):
        """Bind tree events."""
        # Double-click to open URL
        self.tree.bind('<Double-1>', self._open_url)
        # Prevent space from affecting tree selection
        self.tree.bind("<Button-1>", lambda e: self._deselect_if_empty(e))
    
    def _deselect_if_empty(self, event):
        """Deselect tree items if clicking on empty area."""
        item = self.tree.identify_row(event.y)
        if not item:
            self.tree.selection_remove(self.tree.selection())
    
    def _open_url(self, event):
        """Open selected eBay URL in browser."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.results_data):
                url = self.results_data[index]['url']
                if url and not any(x in url for x in ["No URL available", "Placeholder URL", "Invalid URL", "URL Error"]):
                    print(f"[EBAY SEARCH] Opening URL: {url}")
                    webbrowser.open(url)
                else:
                    messagebox.showwarning("Invalid URL", f"Cannot open URL: {url}")
        except (ValueError, IndexError) as e:
            print(f"[EBAY SEARCH] Error opening URL: {e}")
    
    def run_text_search(self, query: str, max_results: int, search_method: str = "scrapy"):
        """Run eBay text search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            search_method: "scrapy" or "api"
        """
        if not query.strip():
            messagebox.showerror("Error", "Please enter a search query")
            return
        
        # Start search in background thread
        self.progress_bar.start()
        self.status_var.set("Searching eBay...")
        
        # Start background thread
        thread = threading.Thread(
            target=self._run_text_search_worker,
            args=(query, max_results, search_method),
            daemon=True
        )
        thread.start()
    
    def _run_text_search_worker(self, query: str, max_results: int, search_method: str):
        """Worker method for eBay text search (runs in background thread)."""
        def update_callback(message):
            self.gui.after(0, lambda: self.status_var.set(message))
        
        def display_callback(results):
            self.gui.after(0, lambda: self.display_results(results))
            self.gui.after(0, self.progress_bar.stop)
        
        def show_message_callback(title, message):
            self.gui.after(0, lambda: messagebox.showinfo(title, message))
            self.gui.after(0, self.progress_bar.stop)
        
        workers.run_scrapy_text_search_worker(
            query, max_results,
            update_callback,
            display_callback,
            show_message_callback,
            search_method=search_method
        )
    
    def run_search_with_compare(self, query: str, max_results: int, 
                              max_comparisons: Optional[int], 
                              reference_image_path: Optional[Path]):
        """Run eBay search with image comparison.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            max_comparisons: Maximum comparisons or None for all
            reference_image_path: Path to reference image for comparison
        """
        if not query.strip():
            messagebox.showerror("Error", "Please enter a search query")
            return
        
        if not reference_image_path or not reference_image_path.exists():
            messagebox.showerror("Error", "Please select a reference image for comparison")
            return
        
        # Check if we have cached results
        has_cached_results = bool(self.results_data)
        
        if has_cached_results:
            # Use cached results - just run comparison
            print(f"[EBAY SEARCH] Using {len(self.results_data)} cached eBay results")
            self.progress_bar.start()
            self.status_var.set("Comparing cached results with reference image...")
            
            thread = threading.Thread(
                target=self._run_cached_compare_worker,
                args=(query, max_comparisons, reference_image_path),
                daemon=True
            )
            thread.start()
        else:
            # No cached results - run full search and compare
            print(f"[EBAY SEARCH] No cached results, running full eBay search")
            self.progress_bar.start()
            self.status_var.set("Searching eBay and comparing images...")
            
            thread = threading.Thread(
                target=self._run_search_with_compare_worker,
                args=(query, max_results, max_comparisons, reference_image_path),
                daemon=True
            )
            thread.start()
    
    def _run_search_with_compare_worker(self, query: str, max_results: int, 
                                     max_comparisons: Optional[int], 
                                     reference_image_path: Path):
        """Worker method for search with image comparison."""
        def update_callback(message):
            self.gui.after(0, lambda: self.status_var.set(message))
        
        def display_callback(results):
            self.gui.after(0, lambda: self.display_results(results))
            self.gui.after(0, self.progress_bar.stop)
        
        def show_message_callback(title, message):
            self.gui.after(0, lambda: messagebox.showerror(title, message))
            self.gui.after(0, self.progress_bar.stop)
        
        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)
        
        workers.run_scrapy_search_with_compare_worker(
            query, max_results, max_comparisons,
            reference_image_path,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback
        )
    
    def _run_cached_compare_worker(self, query: str, max_comparisons: Optional[int], 
                                 reference_image_path: Path):
        """Worker method to compare reference image with cached eBay results."""
        def update_callback(message):
            self.gui.after(0, lambda: self.status_var.set(message))
        
        def display_callback(results):
            self.gui.after(0, lambda: self.display_results(results))
            self.gui.after(0, self.progress_bar.stop)
        
        def show_message_callback(title, message):
            self.gui.after(0, lambda: messagebox.showerror(title, message))
            self.gui.after(0, self.progress_bar.stop)
        
        def create_debug_folder_callback(query):
            return self._create_debug_folder(query)
        
        workers.run_cached_compare_worker(
            query, max_comparisons,
            reference_image_path,
            self.results_data,
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback
        )
    
    def display_results(self, results: List[Dict[str, Any]]):
        """Display eBay search results in the tree view with thumbnails."""
        # Clear existing results and images
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.images.clear()
        
        # Store results for URL opening
        self.results_data = results
        
        # Add new results with thumbnails
        for i, result in enumerate(results, 1):
            values = (
                result['title'],  # Show full title, no truncation
                result['price'],
                result['shipping'],
                result.get('mandarake_price', ''),
                result.get('profit_margin', ''),
                result.get('sold_date', ''),
                result.get('similarity', ''),
                result['url']  # Show full URL, no truncation
            )
            
            # Try to load thumbnail
            image_url = result.get('image_url', '')
            photo = None
            
            if image_url:
                try:
                    response = requests.get(image_url, timeout=5)
                    response.raise_for_status()
                    pil_img = Image.open(BytesIO(response.content))
                    pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(pil_img)
                except Exception as e:
                    print(f"[EBAY SEARCH] Failed to load thumbnail {i}: {e}")
                    photo = None
            
            # Insert with or without image
            if photo:
                self.tree.insert('', 'end', iid=str(i), text='', values=values, image=photo)
                self.images[str(i)] = photo  # Keep reference to prevent garbage collection
            else:
                self.tree.insert('', 'end', iid=str(i), text=str(i), values=values)
        
        print(f"[EBAY SEARCH] Displayed {len(results)} results in tree view ({len(self.images)} with thumbnails)")
    
    def clear_results(self):
        """Clear all eBay search results."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data = []
        self.images.clear()
        self.status_var.set("Ready for eBay text search")
    
    def get_selected_result(self) -> Optional[Dict[str, Any]]:
        """Get the selected eBay result."""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.results_data):
                return self.results_data[index]
        except (ValueError, IndexError):
            pass
        
        return None
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all eBay results."""
        return self.results_data.copy()
    
    def has_cached_results(self) -> bool:
        """Check if there are cached results available."""
        return bool(self.results_data)
    
    def _create_debug_folder(self, query: str) -> Path:
        """Create debug folder for saving comparison images."""
        from datetime import datetime
        import re
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        debug_folder = Path(f"debug_comparison/{safe_query}_{timestamp}")
        debug_folder.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] Debug folder: {debug_folder}")
        return debug_folder
    
    def set_alert_thresholds(self, active: bool, min_similarity: float, min_profit: float):
        """Set alert thresholds for filtering results.
        
        Args:
            active: Whether alert thresholds are active
            min_similarity: Minimum similarity percentage (0-100)
            min_profit: Minimum profit percentage
        """
        self.alert_threshold_active = active
        self.alert_min_similarity = min_similarity
        self.alert_min_profit = min_profit
    
    def filter_results_by_thresholds(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results based on alert thresholds.
        
        Args:
            results: List of comparison results
            
        Returns:
            Filtered list of results
        """
        if not getattr(self, 'alert_threshold_active', False):
            return results
        
        min_sim = getattr(self, 'alert_min_similarity', 70.0)
        min_profit = getattr(self, 'alert_min_profit', 20.0)
        
        filtered = [
            r for r in results
            if r.get('similarity', 0) >= min_sim and r.get('profit_margin', 0) >= min_profit
        ]
        
        return filtered
