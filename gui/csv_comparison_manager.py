"""CSV Comparison Manager - Handles CSV loading, filtering, and comparison operations."""

import csv
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Callable, Any
import re
import tkinter as tk
from tkinter import messagebox, filedialog
import webbrowser
from PIL import Image, ImageTk
import requests
from io import BytesIO

from gui.constants import CATEGORY_KEYWORDS


class CSVComparisonManager:
    """Manages CSV comparison operations including loading, filtering, and eBay comparisons."""
    
    def __init__(self, gui_instance):
        """Initialize CSV Comparison Manager.
        
        Args:
            gui_instance: The main GUI instance for callbacks and widget access
        """
        self.gui = gui_instance
        self.csv_compare_data: List[Dict] = []
        self.csv_compare_path: Optional[Path] = None
        self.csv_filtered_items: List[Dict] = []
        self.csv_new_items: Set[str] = set()
        self.csv_images: Dict[str, ImageTk.PhotoImage] = {}
        
    def load_csv_worker(self, csv_path: Path, autofill_from_config: Optional[Dict] = None) -> bool:
        """Load CSV data into comparison tree.
        
        Args:
            csv_path: Path to CSV file
            autofill_from_config: Optional config dict to autofill eBay query from config keyword
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.csv_compare_path = csv_path
            if hasattr(self.gui, 'csv_compare_label'):
                self.gui.csv_compare_label.config(text=f"Loaded: {csv_path.name}", foreground="black")
            print(f"[CSV WORKER] Loading CSV: {csv_path}")

            # Load CSV data
            self.csv_compare_data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.csv_compare_data.append(row)

            # Set in-stock filter from config if provided
            if autofill_from_config and hasattr(self.gui, 'csv_in_stock_only'):
                show_in_stock_only = autofill_from_config.get('csv_show_in_stock_only', False)
                self.gui.csv_in_stock_only.set(show_in_stock_only)
                print(f"[CSV WORKER] Set in-stock filter to: {show_in_stock_only}")

            # Display with filter applied
            self.filter_csv_items()

            # Auto-fill eBay search query
            if autofill_from_config:
                self._autofill_search_query_from_config(autofill_from_config)
            else:
                self._autofill_search_query_from_csv()

            print(f"[CSV WORKER] Loaded {len(self.csv_compare_data)} items")
            return True

        except Exception as e:
            print(f"[CSV WORKER ERROR] {e}")
            return False

    def filter_csv_items(self) -> None:
        """Filter and display CSV items based on in-stock filter - fast load, thumbnails loaded on demand."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        # Clear existing items and images
        for item in self.gui.csv_items_tree.get_children():
            self.gui.csv_items_tree.delete(item)
        self.csv_images.clear()

        if not self.csv_compare_data:
            return

        # Apply filters
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)  # 24 hours for newly listed filter

        in_stock_only = getattr(self.gui, 'csv_in_stock_only', tk.BooleanVar()).get()
        newly_listed_only = getattr(self.gui, 'csv_newly_listed_only', tk.BooleanVar()).get()
        filtered_items = []

        for row in self.csv_compare_data:
            # In-stock filter
            stock = row.get('in_stock', '').lower()
            if in_stock_only and stock not in ('true', 'yes', '1'):
                continue

            # Newly listed filter (24 hours)
            if newly_listed_only:
                first_seen_str = row.get('first_seen', '')
                if first_seen_str:
                    try:
                        first_seen = datetime.fromisoformat(first_seen_str)
                        if first_seen < cutoff_time:
                            continue  # Skip items older than 24 hours
                    except:
                        continue  # Skip items with invalid dates
                else:
                    continue  # Skip items without first_seen date

            filtered_items.append(row)

        # Display filtered items WITHOUT thumbnails first (fast load)
        recent_hours = self._get_recent_hours_value()
        new_indicator_cutoff = current_time - timedelta(hours=recent_hours) if recent_hours else current_time - timedelta(hours=12)

        # Store NEW status for each item for thumbnail border rendering
        self.csv_new_items.clear()

        for i, row in enumerate(filtered_items):
            # Calculate NEW indicator dynamically
            first_seen_str = row.get('first_seen', '')
            if first_seen_str:
                try:
                    first_seen = datetime.fromisoformat(first_seen_str)
                    if first_seen >= new_indicator_cutoff:
                        self.csv_new_items.add(str(i))  # Mark as new
                except:
                    pass

            # Use English translated title if available, otherwise use original title
            title = row.get('title_en', row.get('title', ''))

            # Format price properly - handle both floats (Suruga-ya) and formatted strings (Mandarake)
            price_raw = row.get('price_text', row.get('price', ''))
            if isinstance(price_raw, (int, float)):
                # Format as currency: ¥160,999
                price = f"¥{price_raw:,.0f}"
            elif isinstance(price_raw, str) and price_raw.replace('.', '').replace(',', '').isdigit():
                # String but looks like a number (e.g., "160999.0")
                try:
                    price = f"¥{float(price_raw):,.0f}"
                except:
                    price = price_raw  # Fallback to original
            else:
                # Already formatted (e.g., "¥1,234")
                price = price_raw

            shop = row.get('shop', row.get('shop_text', ''))
            stock_display = 'Yes' if row.get('in_stock', '').lower() in ('true', 'yes', '1') else 'No'
            category = row.get('category', '')
            url = row.get('url', '')

            # Insert WITHOUT image for fast loading (use 0-based index as iid for proper mapping)
            self.gui.csv_items_tree.insert('', 'end', iid=str(i), text=str(i+1),
                                          values=(title, price, shop, stock_display, category, url))

        print(f"[CSV COMPARE] Displayed {len(filtered_items)} items (newly listed: {newly_listed_only}, in-stock: {in_stock_only})")

        # Store filtered items for thumbnail toggling
        self.csv_filtered_items = filtered_items

        # Load thumbnails in background thread if enabled
        if getattr(self.gui, 'csv_show_thumbnails', tk.BooleanVar()).get():
            self._start_thread(self._load_csv_thumbnails_worker, filtered_items)
        else:
            print(f"[CSV THUMBNAILS] Thumbnails disabled, skipping load")

    def load_csv_for_comparison(self) -> None:
        """Load CSV file for batch comparison."""
        file_path = filedialog.askopenfilename(
            title="Select CSV file for comparison",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="results"
        )

        if file_path:
            success = self.load_csv_worker(Path(file_path))
            if not success:
                messagebox.showerror("Error", f"Failed to load CSV: {file_path}")

    def _load_csv_thumbnails_worker(self, filtered_items: List[Dict]) -> None:
        """Background worker to load CSV thumbnails without blocking UI."""
        def update_image_callback(item_id: str, pil_img: Image.Image) -> None:
            def update_image():
                try:
                    # item_id is the tree item's iid (0-based index as string)
                    if item_id in self.gui.csv_items_tree.get_children():
                        # Create PhotoImage in main thread from PIL Image
                        from PIL import ImageTk
                        photo = ImageTk.PhotoImage(pil_img)
                        self.gui.csv_items_tree.item(item_id, image=photo, text='')
                        self.csv_images[item_id] = photo  # Store to prevent garbage collection
                except Exception as e:
                    print(f"[CSV THUMBNAILS] Error updating image for {item_id}: {e}")
            self.gui.after(0, update_image)

        def save_to_csv_callback(local_image_path: str, row_index: int) -> None:
            """Callback to save downloaded image path to CSV file."""
            def save_csv():
                try:
                    if not self.csv_compare_path:
                        return

                    # Update the in-memory data
                    if row_index < len(self.csv_compare_data):
                        self.csv_compare_data[row_index]['local_image'] = local_image_path

                    # Write back to CSV file
                    import csv
                    with open(self.csv_compare_path, 'w', newline='', encoding='utf-8') as f:
                        if self.csv_compare_data:
                            fieldnames = list(self.csv_compare_data[0].keys())
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(self.csv_compare_data)
                    print(f"[CSV SAVE] Updated CSV with local_image for row {row_index}")
                except Exception as e:
                    print(f"[CSV SAVE] Error saving image path to CSV: {e}")
            self.gui.after(0, save_csv)

        # Get current thumbnail column width
        thumb_width = self.gui.csv_items_tree.column('#0', 'width')

        # Import workers module for thumbnail loading
        from gui import workers
        workers.load_csv_thumbnails_worker(
            filtered_items,
            self.csv_new_items,
            update_image_callback,
            thumb_width,
            csv_path=self.csv_compare_path,
            save_to_csv_callback=save_to_csv_callback
        )

    def toggle_csv_thumbnails(self) -> None:
        """Toggle visibility of thumbnails in CSV treeview."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        show_thumbnails = getattr(self.gui, 'csv_show_thumbnails', tk.BooleanVar()).get()

        if show_thumbnails:
            # Show thumbnails - set column width and rowheight
            self.gui.csv_items_tree.column('#0', width=70, stretch=False)
            style = ttk.Style()
            style.configure('CSV.Treeview', rowheight=70)

            # Reload thumbnails if we have CSV items loaded
            if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items:
                print(f"[CSV THUMBNAILS] Loading thumbnails for {len(self.csv_filtered_items)} items...")
                self._start_thread(self._load_csv_thumbnails_worker, self.csv_filtered_items)
        else:
            # Hide thumbnails - set column width to 0
            self.gui.csv_items_tree.column('#0', width=0, stretch=False)
            style = ttk.Style()
            style.configure('CSV.Treeview', rowheight=25)

        print(f"[CSV THUMBNAILS] Thumbnails {'shown' if show_thumbnails else 'hidden'}")

    def on_csv_item_selected(self, event) -> None:
        """Auto-fill search query when CSV item is selected."""
        if not hasattr(self.gui, 'csv_items_tree') or not hasattr(self.gui, 'browserless_query_var'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                row = items_list[index]

                # Extract core word from title and category keyword
                title = row.get('title', '')
                category = row.get('category', '')
                keyword = row.get('keyword', '')  # Use extracted keyword if available

                # Use keyword if available, otherwise extract from title
                if keyword:
                    core_words = keyword
                else:
                    core_words = ' '.join(title.split()[:3]) if title else ''

                # Get category keyword from mapping
                category_keyword = CATEGORY_KEYWORDS.get(category, '')

                # Build search query: keyword + category keyword
                search_query = f"{core_words} {category_keyword}".strip()

                # Add secondary keyword if toggle is on
                if hasattr(self.gui, 'csv_add_secondary_keyword') and self.gui.csv_add_secondary_keyword.get():
                    if title and keyword:
                        secondary = self._extract_secondary_keyword(title, keyword)
                        if secondary:
                            search_query = f"{search_query} {secondary}".strip()
                            print(f"[CSV COMPARE] Added secondary keyword: {secondary}")

                if search_query:
                    self.gui.browserless_query_var.set(search_query)
                    print(f"[CSV COMPARE] Auto-filled search: {search_query}")

        except (ValueError, IndexError) as e:
            print(f"[CSV COMPARE] Error selecting item: {e}")

    def on_csv_filter_changed(self) -> None:
        """Handle CSV filter changes - filter items (settings saved on close)."""
        self.filter_csv_items()

    def on_csv_column_resize(self, event) -> None:
        """Handle column resize event to reload thumbnails with new size."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        # Only handle if we're resizing the thumbnail column (#0)
        # Use a timer to avoid reloading on every pixel change
        if hasattr(self, '_resize_timer'):
            self.gui.after_cancel(self._resize_timer)

        def reload_thumbnails():
            # Check if thumbnail column was resized and thumbnails are enabled
            if (getattr(self.gui, 'csv_show_thumbnails', tk.BooleanVar()).get() and 
                hasattr(self, 'csv_filtered_items') and self.csv_filtered_items):
                current_width = self.gui.csv_items_tree.column('#0', 'width')
                # Only reload if width changed significantly (more than 5px)
                if not hasattr(self, '_last_thumb_width') or abs(current_width - self._last_thumb_width) > 5:
                    self._last_thumb_width = current_width
                    print(f"[CSV THUMBNAILS] Column resized to {current_width}px, reloading thumbnails...")
                    self._start_thread(self._load_csv_thumbnails_worker, self.csv_filtered_items)

        # Debounce: wait 300ms after user stops dragging
        self._resize_timer = self.gui.after(300, reload_thumbnails)

    def on_csv_item_double_click(self, event) -> None:
        """Handle double-click on CSV item to open URL in browser."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        # Get the item that was double-clicked
        region = self.gui.csv_items_tree.identify('region', event.x, event.y)
        item_id = self.gui.csv_items_tree.identify_row(event.y)

        if not item_id:
            return

        # Get the URL from the item's values (last column)
        item_values = self.gui.csv_items_tree.item(item_id, 'values')
        if len(item_values) >= 6:  # Make sure URL column exists
            url = item_values[5]  # URL is the 6th column (index 5)
            if url:
                # Open URL in default browser in a separate thread to avoid blocking
                def open_url():
                    webbrowser.open(url)
                    print(f"[CSV] Opened URL: {url}")

                thread = threading.Thread(target=open_url, daemon=True)
                thread.start()

    def compare_selected_csv_item(self) -> None:
        """Compare selected CSV item with eBay."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to compare")
            return

        # Get selected item data
        item_id = selection[0]
        try:
            # Need to find the actual item from filtered display
            # The iid in tree might not match csv_compare_data index due to filtering
            values = self.gui.csv_items_tree.item(item_id)['values']
            if not values:
                messagebox.showerror("Error", "Could not get item data")
                return

            # Find matching item in csv_compare_data by title
            title_prefix = values[0]  # Truncated title from display
            item = None
            for row in self.csv_compare_data:
                if row.get('title', '').startswith(title_prefix.replace('...', '')):
                    item = row
                    break

            if not item:
                messagebox.showerror("Error", "Could not find selected item")
                return

            # Extract search query from eBay query field
            if not hasattr(self.gui, 'browserless_query_var'):
                messagebox.showerror("Error", "eBay search query field not available")
                return

            search_query = self.gui.browserless_query_var.get().strip()
            if not search_query:
                messagebox.showwarning("No Query", "Please enter a search query")
                return

            # Run comparison in background
            if hasattr(self.gui, 'csv_compare_progress'):
                self.gui.csv_compare_progress.start()
            self._start_thread(lambda: self._compare_csv_items_worker([item], search_query))

        except Exception as e:
            messagebox.showerror("Error", f"Invalid selection: {e}")

    def compare_all_csv_items(self, skip_confirmation: bool = False) -> None:
        """Compare all visible CSV items with eBay.

        Args:
            skip_confirmation: If True, skip confirmation dialogs (for scheduled tasks)
        """
        if not self.csv_compare_data:
            if not skip_confirmation:
                messagebox.showinfo("No Data", "Please load a CSV file first")
            return

        # Use already filtered items from the display
        # This respects both in-stock and newly listed filters
        items_to_compare = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') else self.csv_compare_data

        if not items_to_compare:
            if not skip_confirmation:
                messagebox.showinfo("No Items", "No items to compare (check filter settings)")
            return

        # Extract search query from the eBay query field (already populated by CSV load)
        if not hasattr(self.gui, 'browserless_query_var'):
            messagebox.showerror("Error", "eBay search query field not available")
            return

        search_query = self.gui.browserless_query_var.get().strip()
        if not search_query:
            messagebox.showwarning("No Query", "Please load a CSV or enter a search query")
            return

        # Check if 2nd keyword is enabled
        add_secondary = (hasattr(self.gui, 'csv_add_secondary_keyword') and 
                        self.gui.csv_add_secondary_keyword.get())

        # Choose comparison method based on 2nd keyword setting
        if add_secondary:
            # With 2nd keyword: Each item needs individual eBay search (different keywords)
            if skip_confirmation:
                response = True
            else:
                response = messagebox.askyesno(
                    "Individual Batch Comparison",
                    f"Compare {len(items_to_compare)} items with individual eBay searches?\n\n"
                    f"2nd keyword is enabled, so each item will have a separate search.\n"
                    f"This will take longer."
                )
            if response:
                if hasattr(self.gui, 'csv_compare_progress'):
                    self.gui.csv_compare_progress.start()
                self._start_thread(lambda: self._compare_csv_items_individually_worker(items_to_compare, search_query))
        else:
            # Without 2nd keyword: Use single cached eBay search for all items
            if skip_confirmation:
                response = True
            else:
                response = messagebox.askyesno(
                    "Batch Comparison",
                    f"Compare {len(items_to_compare)} items with cached eBay search?\n\n"
                    f"All items use the same keyword, so we'll reuse eBay results."
                )
            if response:
                if hasattr(self.gui, 'csv_compare_progress'):
                    self.gui.csv_compare_progress.start()
                self._start_thread(lambda: self._compare_csv_items_worker(items_to_compare, search_query))

    def _compare_csv_items_worker(self, items: List[Dict], search_query: str) -> None:
        """Worker to compare CSV items with eBay - OPTIMIZED with caching (runs in background thread).

        Args:
            items: List of items to compare
            search_query: Pre-built search query (keyword + category keyword)
        """
        if not hasattr(self.gui, 'browserless_max_results'):
            print("[CSV COMPARISON] eBay max results setting not available")
            return

        max_results = int(self.gui.browserless_max_results.get())

        def update_callback(message: str) -> None:
            if hasattr(self.gui, 'browserless_status'):
                self.gui.after(0, lambda: self.gui.browserless_status.set(message))

        def display_callback(comparison_results: List[Dict]) -> None:
            # Store results and apply filter
            if hasattr(self.gui, 'all_comparison_results'):
                self.gui.all_comparison_results = comparison_results
                self.gui.after(0, self.gui.apply_results_filter)
                
                # Auto-send to alerts if threshold is active
                if (hasattr(self.gui, 'alert_threshold_active') and 
                    self.gui.alert_threshold_active.get()):
                    min_sim = self.gui.alert_min_similarity.get()
                    min_profit = self.gui.alert_min_profit.get()
                    self.gui.after(0, lambda: self.gui._send_to_alerts_with_thresholds(
                        comparison_results, min_sim, min_profit))
            
            if hasattr(self.gui, 'csv_compare_progress'):
                self.gui.after(0, self.gui.csv_compare_progress.stop)

        def show_message_callback(title: str, message: str, msg_type: str = 'info') -> None:
            def show_msg():
                if msg_type == 'error':
                    messagebox.showerror(title, message)
                else:
                    messagebox.showinfo(title, message)
            self.gui.after(0, show_msg)
            if hasattr(self.gui, 'csv_compare_progress'):
                self.gui.after(0, self.gui.csv_compare_progress.stop)

        # Import workers module for comparison
        from gui import workers
        workers.compare_csv_items_worker(
            items,
            max_results,
            getattr(self.gui, 'browserless_results_data', []),
            search_query,
            getattr(self.gui, 'usd_jpy_rate', 150.0),
            update_callback,
            display_callback,
            show_message_callback
        )

    def _compare_csv_items_individually_worker(self, items: List[Dict], base_search_query: str) -> None:
        """Worker to compare CSV items individually - each item gets its own eBay search.

        Args:
            items: List of items to compare
            base_search_query: Base search query (keyword + category keyword)
        """
        if not hasattr(self.gui, 'browserless_max_results'):
            print("[CSV COMPARISON] eBay max results setting not available")
            return

        max_results = int(self.gui.browserless_max_results.get())
        add_secondary = (hasattr(self.gui, 'csv_add_secondary_keyword') and 
                        self.gui.csv_add_secondary_keyword.get())

        def update_callback(message: str) -> None:
            if hasattr(self.gui, 'browserless_status'):
                self.gui.after(0, lambda: self.gui.browserless_status.set(message))

        def display_callback(comparison_results: List[Dict]) -> None:
            # Store results and apply filter
            if hasattr(self.gui, 'all_comparison_results'):
                self.gui.all_comparison_results = comparison_results
                self.gui.after(0, self.gui.apply_results_filter)
                
                # Auto-send to alerts if threshold is active
                if (hasattr(self.gui, 'alert_threshold_active') and 
                    self.gui.alert_threshold_active.get()):
                    min_sim = self.gui.alert_min_similarity.get()
                    min_profit = self.gui.alert_min_profit.get()
                    self.gui.after(0, lambda: self.gui._send_to_alerts_with_thresholds(
                        comparison_results, min_sim, min_profit))
            
            if hasattr(self.gui, 'csv_compare_progress'):
                self.gui.after(0, self.gui.csv_compare_progress.stop)

        def show_message_callback(title: str, message: str) -> None:
            def show_msg():
                messagebox.showerror(title, message)
            self.gui.after(0, show_msg)
            if hasattr(self.gui, 'csv_compare_progress'):
                self.gui.after(0, self.gui.csv_compare_progress.stop)

        def create_debug_folder_callback(query: str) -> str:
            return self.gui._create_debug_folder(query) if hasattr(self.gui, '_create_debug_folder') else 'debug'

        # Import workers module for individual comparison
        from gui import workers
        workers.compare_csv_items_individually_worker(
            items,
            max_results,
            add_secondary,
            getattr(self.gui, 'usd_jpy_rate', 150.0),
            update_callback,
            display_callback,
            show_message_callback,
            create_debug_folder_callback,
            self._extract_secondary_keyword
        )

    def _extract_secondary_keyword(self, title: str, primary_keyword: str) -> str:
        """Extract secondary keyword from title by removing primary keyword and common terms."""
        import re

        # Make a working copy
        secondary = title

        # Remove primary keyword (case insensitive), handling name in different orders
        # e.g., "Yura Kano" and "Kano Yura"
        secondary = re.sub(re.escape(primary_keyword), '', secondary, flags=re.IGNORECASE).strip()

        # Also remove reversed name order (split and reverse)
        name_parts = primary_keyword.split()
        if len(name_parts) == 2:
            reversed_name = f"{name_parts[1]} {name_parts[0]}"
            secondary = re.sub(re.escape(reversed_name), '', secondary, flags=re.IGNORECASE).strip()
            # Also remove individual parts if they appear alone
            for part in name_parts:
                if len(part) > 2:  # Don't remove very short words
                    secondary = re.sub(r'\b' + re.escape(part) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

        # Use dynamic publisher list instead of hardcoded
        if hasattr(self.gui, 'publisher_list'):
            for pub in self.gui.publisher_list:
                secondary = re.sub(r'\b' + re.escape(pub) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

        # Remove generic suffixes
        generic_terms = ['Photograph Collection', 'Photo Essay', 'Photo Collection',
                        'Photobook', 'autographed', 'Photograph', 'Collection']
        for term in generic_terms:
            secondary = re.sub(r'\b' + re.escape(term) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

        # Remove years (e.g., "2022", "2023")
        secondary = re.sub(r'\b(19|20)\d{2}\b', '', secondary).strip()

        # Remove "Desktop" before "Calendar" to get just "Calendar"
        secondary = re.sub(r'\bDesktop\s+Calendar\b', 'Calendar', secondary, flags=re.IGNORECASE).strip()

        # Clean up extra spaces
        secondary = re.sub(r'\s+', ' ', secondary).strip()

        # If nothing left, return empty
        if not secondary or len(secondary) < 2:
            return ""

        return secondary

    def _autofill_search_query_from_csv(self) -> None:
        """Auto-fill eBay search query from first CSV item's keyword and optionally add secondary keyword."""
        if not hasattr(self.gui, 'browserless_query_var'):
            return

        try:
            if not self.csv_filtered_items:
                return

            # Get first filtered item
            first_item = self.csv_filtered_items[0]
            keyword = first_item.get('keyword', '')
            category = first_item.get('category', '')

            # If no keyword field, try to extract from title
            if not keyword:
                title = first_item.get('title', '')
                keyword = ' '.join(title.split()[:3]) if title else ''

            if not keyword:
                return

            # Get category keyword from mapping
            category_keyword = CATEGORY_KEYWORDS.get(category, '')

            # Build search query: keyword + category keyword
            search_query = f"{keyword} {category_keyword}".strip()

            # Check if secondary keyword should be added
            if (hasattr(self.gui, 'csv_add_secondary_keyword') and 
                self.gui.csv_add_secondary_keyword.get()):
                title = first_item.get('title', '')
                if title:
                    secondary = self._extract_secondary_keyword(title, keyword)
                    if secondary:
                        search_query = f"{search_query} {secondary}".strip()
                        print(f"[CSV AUTOFILL] Added secondary keyword: {secondary}")

            # Set the final query
            self.gui.browserless_query_var.set(search_query)
            print(f"[CSV AUTOFILL] Set eBay query: {search_query}")

        except Exception as e:
            print(f"[CSV AUTOFILL] Error: {e}")

    def _autofill_search_query_from_config(self, config: Dict) -> None:
        """Auto-fill eBay search query from config keyword and optionally add secondary keyword."""
        if not hasattr(self.gui, 'browserless_query_var'):
            return

        try:
            # Get keyword from config
            keyword = config.get('keyword', '').strip()
            if not keyword:
                return

            # Check if secondary keyword should be added
            add_secondary = (hasattr(self.gui, 'csv_add_secondary_keyword') and 
                            self.gui.csv_add_secondary_keyword.get())

            if add_secondary and self.csv_filtered_items:
                # Get first filtered item and extract secondary keyword
                first_item = self.csv_filtered_items[0]
                title = first_item.get('title', '')
                if title:
                    secondary = self._extract_secondary_keyword(title, keyword)
                    if secondary:
                        query = f"{keyword} {secondary}"
                        self.gui.browserless_query_var.set(query)
                        print(f"[CSV AUTOFILL] Set eBay query with secondary: {query}")
                        return

            # No secondary keyword, just use primary keyword
            self.gui.browserless_query_var.set(keyword)
            print(f"[CSV AUTOFILL] Set eBay query: {keyword}")

        except Exception as e:
            print(f"[CSV AUTOFILL] Error: {e}")

    def _save_updated_csv(self) -> None:
        """Save the updated CSV with new local_image paths."""
        try:
            # Get fieldnames from first row
            if not self.csv_compare_data or not self.csv_compare_path:
                return

            fieldnames = list(self.csv_compare_data[0].keys())

            # Write to CSV
            with open(self.csv_compare_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.csv_compare_data)

            print(f"[CSV IMAGES] Updated CSV file: {self.csv_compare_path}")

        except Exception as e:
            print(f"[CSV IMAGES] Error saving CSV: {e}")
            raise

    def _download_missing_csv_images(self) -> None:
        """Download missing images from web and save them locally."""
        if not self.csv_compare_data or not self.csv_compare_path:
            messagebox.showwarning("No CSV", "Please load a CSV file first.")
            return

        # Count items missing local images
        missing_count = 0
        for row in self.csv_compare_data:
            local_image = row.get('local_image', '')
            image_url = row.get('image_url', '')
            if image_url and (not local_image or not Path(local_image).exists()):
                missing_count += 1

        if missing_count == 0:
            messagebox.showinfo("Complete", "All items already have local images!")
            return

        response = messagebox.askyesno(
            "Download Images",
            f"Download {missing_count} missing images from web and save them locally?\n\nThis will update the CSV file."
        )

        if not response:
            return

        # Start download in background
        if hasattr(self.gui, 'browserless_status'):
            self.gui.browserless_status.set(f"Downloading {missing_count} missing images...")
        self._start_thread(self._download_missing_images_worker)

    def _download_missing_images_worker(self) -> None:
        """Background worker to download missing images."""
        if not hasattr(self.gui, 'download_dir_var'):
            print("[CSV IMAGES] Download directory not available")
            return

        download_dir = self.gui.download_dir_var.get().strip()

        def update_callback(message: str) -> None:
            if hasattr(self.gui, 'browserless_status'):
                self.gui.after(0, lambda: self.gui.browserless_status.set(message))

        def save_callback() -> None:
            self._save_updated_csv()

        def reload_callback() -> None:
            self.gui.after(0, self.filter_csv_items)

        # Import workers module for image downloading
        from gui import workers
        workers.download_missing_images_worker(
            self.csv_compare_data,
            download_dir,
            update_callback,
            save_callback,
            reload_callback
        )

    def _delete_csv_items(self) -> None:
        """Delete selected CSV items (supports multi-select)."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select items to delete")
            return

        # Confirm deletion
        count = len(selection)
        item_word = "item" if count == 1 else "items"
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete {count} {item_word}?\n\nThis will also delete associated images from disk."):
            return

        try:
            # Get the titles and image paths of selected items
            items_to_delete = []
            images_to_delete = []
            for item_id in selection:
                values = self.gui.csv_items_tree.item(item_id)['values']
                if values:
                    title = values[0]  # Title is first column
                    items_to_delete.append(title)

                    # Find the corresponding row in csv_compare_data to get image path
                    for row in self.csv_compare_data:
                        if row.get('title', '') == title:
                            local_image = row.get('local_image', '')
                            if local_image:
                                images_to_delete.append(local_image)
                            break

            # Remove from csv_compare_data by matching titles
            original_count = len(self.csv_compare_data)
            self.csv_compare_data = [
                row for row in self.csv_compare_data
                if row.get('title', '') not in items_to_delete
            ]
            deleted_count = original_count - len(self.csv_compare_data)

            # Delete associated image files
            images_deleted = 0
            for image_path in images_to_delete:
                try:
                    img_file = Path(image_path)
                    if img_file.exists():
                        img_file.unlink()
                        images_deleted += 1
                        print(f"[CSV DELETE] Deleted image: {image_path}")
                except Exception as e:
                    print(f"[CSV DELETE] Failed to delete image {image_path}: {e}")

            # Refresh the display
            self.filter_csv_items()

            # Update status
            if hasattr(self.gui, 'status_var'):
                status_msg = f"Deleted {deleted_count} {item_word}"
                if images_deleted > 0:
                    status_msg += f" and {images_deleted} image{'s' if images_deleted != 1 else ''}"
                self.gui.status_var.set(status_msg)
            print(f"[CSV DELETE] Removed {deleted_count} items and {images_deleted} images from disk")

            # Save updated CSV if a file is loaded
            if self.csv_compare_path:
                self._save_updated_csv()

        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to delete items: {str(e)}")
            print(f"[CSV DELETE] Error: {e}")

    def _show_csv_tree_menu(self, event) -> None:
        """Show context menu on CSV tree."""
        if not hasattr(self.gui, 'csv_items_tree') or not hasattr(self.gui, 'csv_tree_menu'):
            return

        # Select the item under the cursor
        item = self.gui.csv_items_tree.identify_row(event.y)
        if item:
            self.gui.csv_items_tree.selection_set(item)
            self.gui.csv_tree_menu.post(event.x_root, event.y_root)

    def _add_full_title_to_search(self) -> None:
        """Replace eBay search query with full title from selected CSV item."""
        if not hasattr(self.gui, 'csv_items_tree') or not hasattr(self.gui, 'browserless_query_var'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item from the CSV tree")
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                row = items_list[index]

                # Get the full title
                title = row.get('title', '')
                if title:
                    # Update the eBay search query field
                    self.gui.browserless_query_var.set(title)
                    print(f"[CSV MENU] Set eBay search query to full title: {title}")
        except Exception as e:
            print(f"[CSV MENU] Error setting full title: {e}")

    def _add_secondary_keyword_from_csv(self) -> None:
        """Add selected CSV item's secondary keyword to the eBay search query field."""
        if not hasattr(self.gui, 'csv_items_tree') or not hasattr(self.gui, 'browserless_query_var'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item from the CSV tree")
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)

            # Use filtered items if available, otherwise use full list
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data

            if 0 <= index < len(items_list):
                row = items_list[index]

                # Get the title and primary keyword
                title = row.get('title', '')
                primary_keyword = row.get('keyword', '')

                # Extract secondary keyword using the extraction algorithm
                if title and primary_keyword:
                    secondary = self._extract_secondary_keyword(title, primary_keyword)
                elif title:
                    # No primary keyword, use first few words of title
                    secondary = ' '.join(title.split()[:3])
                else:
                    secondary = ''

                if secondary:
                    # Get current eBay search query value
                    current_query = self.gui.browserless_query_var.get().strip()

                    # Append secondary keyword to eBay search query
                    if current_query:
                        new_query = f"{current_query} {secondary}"
                    else:
                        new_query = secondary

                    # Update the eBay search query field
                    self.gui.browserless_query_var.set(new_query)
                    print(f"[CSV MENU] Added secondary keyword to eBay query: {secondary}")
        except Exception as e:
            print(f"[CSV MENU] Error adding secondary keyword: {e}")

    def _search_csv_by_image_api(self) -> None:
        """Search selected CSV item by image using eBay API."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                item_data = items_list[index]
                local_image_path = item_data.get('local_image', '')
                if not local_image_path or not Path(local_image_path).exists():
                    messagebox.showerror("Error", "Local image not found for this item.")
                    return

                from mandarake_scraper import EbayAPI
                # Note: eBay API credentials removed from GUI - using web scraping instead
                ebay_api = EbayAPI("", "")

                if hasattr(self.gui, 'browserless_status'):
                    self.gui.browserless_status.set("Searching by image on eBay (API)...")
                url = ebay_api.search_by_image_api(local_image_path)
                if url:
                    webbrowser.open(url)
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set("Search by image (API) complete.")
                else:
                    messagebox.showerror("Error", "Could not find results using eBay API.")
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set("Search by image (API) failed.")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")

    def _search_csv_by_image_web(self) -> None:
        """Search selected CSV item by image using web method."""
        if not hasattr(self.gui, 'csv_items_tree'):
            return

        selection = self.gui.csv_items_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            # item_id is now 0-based index directly
            index = int(item_id)
            # Use filtered items if available
            items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
            if 0 <= index < len(items_list):
                item_data = items_list[index]
                local_image_path = item_data.get('local_image', '')
                if not local_image_path or not Path(local_image_path).exists():
                    messagebox.showerror("Error", "Local image not found for this item.")
                    return

                if hasattr(self.gui, 'browserless_status'):
                    self.gui.browserless_status.set("Searching by image on eBay (Web)...")
                self._start_thread(self._run_csv_web_image_search, local_image_path)
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")

    def _run_csv_web_image_search(self, image_path: str) -> None:
        """Run web image search for CSV item."""
        from ebay_image_search import run_ebay_image_search
        url = run_ebay_image_search(image_path)
        if "Error" not in url:
            webbrowser.open(url)
            if hasattr(self.gui, 'run_queue'):
                self.gui.run_queue.put(("browserless_status", "Search by image (Web) complete."))
        else:
            if hasattr(self.gui, 'run_queue'):
                self.gui.run_queue.put(("error", "Could not find results using web search."))

    def _get_recent_hours_value(self) -> Optional[int]:
        """Get recent hours value from GUI."""
        if not hasattr(self.gui, 'recent_hours_var'):
            return None

        label = self.gui.recent_hours_var.get()
        if label:
            from gui.constants import RECENT_OPTIONS
            for display, hours in RECENT_OPTIONS:
                if display == label:
                    return hours
        return None

    def display_csv_comparison_results(self, results: List[Dict]) -> None:
        """Display CSV comparison results in the browserless tree.

        Args:
            results: List of comparison results with ebay_title, mandarake fields
        """
        # Convert format to match browserless display
        display_results = []
        for r in results:
            display_results.append({
                'title': r['ebay_title'],
                'price': r['ebay_price'],
                'shipping': r['shipping'],
                'mandarake_price': r.get('mandarake_price', ''),
                'profit_margin': r['profit_display'],
                'sold_date': r.get('sold_date', ''),  # Keep actual sold date
                'similarity': r['similarity_display'],
                'url': r['ebay_link'],
                'mandarake_url': r.get('mandarake_link', ''),
                'image_url': r['thumbnail'],
                'mandarake_image_url': r.get('mandarake_thumbnail', '')
            })

        # Delegate to EbaySearchManager for display
        if (hasattr(self.gui, 'ebay_tab') and
            hasattr(self.gui.ebay_tab, 'ebay_search_manager') and
            self.gui.ebay_tab.ebay_search_manager):
            self.gui.ebay_tab.ebay_search_manager.display_browserless_results(display_results)

    def save_comparison_results_to_csv(self, comparison_results: List[Dict]) -> None:
        """Save eBay comparison results back to the CSV file.

        Args:
            comparison_results: List of dicts with comparison data including
                              'mandarake_item', 'similarity', 'best_match', etc.
        """
        if not self.csv_compare_path or not self.csv_compare_data:
            print("[COMPARISON SAVE] No CSV loaded, skipping save")
            return

        try:
            from datetime import datetime

            # Create a mapping of URLs to comparison results
            url_to_results = {}
            for result in comparison_results:
                mandarake_item = result.get('mandarake_item', {})
                url = mandarake_item.get('url', mandarake_item.get('product_url', ''))
                if url:
                    best_match = result.get('best_match', {})
                    url_to_results[url] = {
                        'ebay_compared': datetime.now().isoformat(),
                        'ebay_match_found': 'Yes' if best_match else 'No',
                        'ebay_best_match_title': best_match.get('title', '') if best_match else '',
                        'ebay_similarity': f"{result.get('similarity', 0):.1f}" if best_match else '',
                        'ebay_price': f"${best_match.get('price', 0):.2f}" if best_match else '',
                        'ebay_profit_margin': f"{result.get('profit_margin', 0):.1f}%" if best_match else ''
                    }

            # Update csv_compare_data with comparison results
            updated_count = 0
            for row in self.csv_compare_data:
                url = row.get('url', row.get('product_url', ''))
                if url in url_to_results:
                    row.update(url_to_results[url])
                    updated_count += 1

            # Save updated CSV
            if updated_count > 0:
                self._save_updated_csv()
                print(f"[COMPARISON SAVE] Saved comparison results for {updated_count} items to CSV")
            else:
                print("[COMPARISON SAVE] No items matched for saving")

        except Exception as e:
            print(f"[COMPARISON SAVE] Error saving comparison results: {e}")
            import traceback
            traceback.print_exc()

    def clear_comparison_results(self) -> None:
        """Clear all eBay comparison results from the loaded CSV."""
        if not self.csv_compare_data or not self.csv_compare_path:
            messagebox.showwarning("No CSV", "Please load a CSV file first")
            return

        # Count items with comparison results
        compared_count = sum(1 for item in self.csv_compare_data if item.get('ebay_compared'))

        if compared_count == 0:
            # Log to status instead of popup
            if hasattr(self.gui.ebay_tab, 'browserless_status'):
                self.gui.ebay_tab.browserless_status.set("No comparison results to clear")
            print("[CLEAR RESULTS] No results to clear")
            return

        # Confirm clearing
        response = messagebox.askyesno(
            "Clear Comparison Results",
            f"Clear comparison results for {compared_count} items?\n\n"
            f"This will reset ebay_compared, ebay_match_found, ebay_similarity, etc.\n"
            f"You can recompare items after clearing."
        )

        if response:
            try:
                # Clear comparison fields for all items
                for item in self.csv_compare_data:
                    item['ebay_compared'] = ''
                    item['ebay_match_found'] = ''
                    item['ebay_best_match_title'] = ''
                    item['ebay_similarity'] = ''
                    item['ebay_price'] = ''
                    item['ebay_profit_margin'] = ''

                # Save updated CSV
                self._save_updated_csv()

                # Log to status instead of popup
                if hasattr(self.gui.ebay_tab, 'browserless_status'):
                    self.gui.ebay_tab.browserless_status.set(f"Cleared comparison results for {compared_count} items")
                print(f"[CLEAR RESULTS] Cleared comparison results for {compared_count} items")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear results: {e}")
                print(f"[CLEAR RESULTS ERROR] {e}")

    def _start_thread(self, target: Callable, *args) -> None:
        """Start a background thread."""
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()
