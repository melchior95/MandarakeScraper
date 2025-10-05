"""CSV Comparison Manager - Handles CSV loading, filtering, and comparison operations."""

import csv
import logging
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

            # Clear image cache when loading new CSV file
            self.csv_images.clear()

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

        # Clear existing tree items (but keep image cache for performance)
        for item in self.gui.csv_items_tree.get_children():
            self.gui.csv_items_tree.delete(item)
        # NOTE: Don't clear self.csv_images - it's a persistent cache cleared only on new CSV load

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
                    except (ValueError, TypeError) as e:
                        logging.debug(f"Skipping item with invalid first_seen date '{first_seen_str}': {e}")
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
                except (ValueError, TypeError):
                    pass  # Skip NEW indicator for items with invalid dates

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
                except (ValueError, TypeError):
                    price = price_raw  # Fallback to original
            else:
                # Already formatted (e.g., "¥1,234")
                price = price_raw

            shop = row.get('shop', row.get('shop_text', ''))
            stock_display = 'Yes' if row.get('in_stock', '').lower() in ('true', 'yes', '1') else 'No'
            category = row.get('category', '')
            url = row.get('url', '')
            # Check if item has been compared (ebay_compared field exists and is not empty)
            compared_display = '✓' if row.get('ebay_compared', '') else ''

            # Insert WITHOUT image for fast loading (use 0-based index as iid for proper mapping)
            self.gui.csv_items_tree.insert('', 'end', iid=str(i), text=str(i+1),
                                          values=(title, price, shop, stock_display, category, compared_display, url))

        print(f"[CSV COMPARE] Displayed {len(filtered_items)} items (newly listed: {newly_listed_only}, in-stock: {in_stock_only})")

        # Store filtered items for thumbnail toggling
        self.csv_filtered_items = filtered_items

        # Load thumbnails in background thread if enabled
        # Access csv_show_thumbnails from advanced_tab through main_window
        show_thumbnails = False
        if hasattr(self.gui, 'main_window') and hasattr(self.gui.main_window, 'advanced_tab'):
            show_thumbnails = self.gui.main_window.advanced_tab.csv_show_thumbnails.get()

        if show_thumbnails:
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
                        # Get stable cache key from item (use URL as unique identifier)
                        item_idx = int(item_id)
                        cache_key = filtered_items[item_idx].get('product_url', f'item_{item_id}')

                        # Reuse cached PhotoImage if available, otherwise create new one
                        if cache_key in self.csv_images:
                            photo = self.csv_images[cache_key]
                        else:
                            from PIL import ImageTk
                            photo = ImageTk.PhotoImage(pil_img)
                            self.csv_images[cache_key] = photo  # Cache by stable key

                        self.gui.csv_items_tree.item(item_id, image=photo, text='')
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

        # Access csv_show_thumbnails from advanced_tab through main_window
        show_thumbnails = False
        if hasattr(self.gui, 'main_window') and hasattr(self.gui.main_window, 'advanced_tab'):
            show_thumbnails = self.gui.main_window.advanced_tab.csv_show_thumbnails.get()

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
            # Access csv_show_thumbnails from advanced_tab through main_window
            show_thumbnails = False
            if hasattr(self.gui, 'main_window') and hasattr(self.gui.main_window, 'advanced_tab'):
                show_thumbnails = self.gui.main_window.advanced_tab.csv_show_thumbnails.get()

            if (show_thumbnails and
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
                # Access main_window through ebay_tab
                main_window = self.gui.main_window if hasattr(self.gui, 'main_window') else self.gui
                self.gui.after(0, main_window.apply_results_filter)

                # Save comparison results to CSV (update ebay_compared field)
                self.save_comparison_results_to_csv(comparison_results)
                # Refresh the CSV tree to show checkmarks
                self.gui.after(0, self.filter_csv_items)

                # Auto-send to alerts if threshold is active
                if (hasattr(self.gui, 'alert_threshold_active') and
                    self.gui.alert_threshold_active.get()):
                    min_sim = self.gui.alert_min_similarity.get()
                    min_profit = self.gui.alert_min_profit.get()
                    self.gui.after(0, lambda: main_window._send_to_alerts_with_thresholds(
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
                # Access main_window through ebay_tab
                main_window = self.gui.main_window if hasattr(self.gui, 'main_window') else self.gui
                self.gui.after(0, main_window.apply_results_filter)

                # Save comparison results to CSV (update ebay_compared field)
                self.save_comparison_results_to_csv(comparison_results)
                # Refresh the CSV tree to show checkmarks
                self.gui.after(0, self.filter_csv_items)

                # Auto-send to alerts if threshold is active
                if (hasattr(self.gui, 'alert_threshold_active') and
                    self.gui.alert_threshold_active.get()):
                    min_sim = self.gui.alert_min_similarity.get()
                    min_profit = self.gui.alert_min_profit.get()
                    self.gui.after(0, lambda: main_window._send_to_alerts_with_thresholds(
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
        """Search selected CSV item by image using eBay API and display results."""
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

                # Get credentials from settings
                main_window = self.gui.main_window if hasattr(self.gui, 'main_window') else self.gui
                if hasattr(main_window, 'settings'):
                    credentials = main_window.settings.get_ebay_credentials()
                    client_id = credentials.get('client_id', '')
                    client_secret = credentials.get('client_secret', '')
                else:
                    client_id = ''
                    client_secret = ''

                if not client_id or not client_secret:
                    messagebox.showerror(
                        "eBay Credentials Required",
                        "Please configure your eBay API credentials in Advanced tab.\n\n"
                        "You need:\n"
                        "• eBay Client ID (App ID)\n"
                        "• eBay Client Secret (Cert ID)\n\n"
                        "Get them from: https://developer.ebay.com/my/keys"
                    )
                    return

                ebay_api = EbayAPI(client_id, client_secret)

                if hasattr(self.gui, 'browserless_status'):
                    self.gui.browserless_status.set("Searching by image on eBay (API)...")

                # Use new method that returns full results
                results = ebay_api.search_by_image_api_full(local_image_path)

                if results is None:
                    messagebox.showerror("Error", "eBay API search failed. Check credentials and logs.")
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set("Search by image (API) failed.")
                    return

                if not results:
                    messagebox.showinfo("No Results", "No matching items found on eBay.")
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set("No results found.")
                    return

                print(f"[IMAGE SEARCH API] Got {len(results)} raw results, now comparing images...")

                # Get the CSV item data for profit calculation
                selection = self.gui.csv_items_tree.selection()
                item_id = selection[0]
                index = int(item_id)
                items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data
                csv_item = items_list[index]

                # Compare images and calculate similarity/profit for each result
                if hasattr(self.gui, 'browserless_status'):
                    self.gui.browserless_status.set(f"Comparing {len(results)} images...")

                compared_results = self._compare_image_search_results(local_image_path, results, csv_item)

                if not compared_results:
                    messagebox.showinfo("No Matches", "No matching items found after image comparison.")
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set("No matches found.")
                    return

                # Display compared results in eBay results tree
                if hasattr(self.gui, 'ebay_search_manager') and self.gui.ebay_search_manager:
                    self.gui.ebay_search_manager.display_browserless_results(compared_results)
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set(f"Found {len(compared_results)} matches (filtered from {len(results)})")
                    print(f"[IMAGE SEARCH API] Displayed {len(compared_results)} matching results")
                else:
                    messagebox.showinfo("Results Found", f"Found {len(compared_results)} matching items.\n\nNote: Results display not available.")
                    if hasattr(self.gui, 'browserless_status'):
                        self.gui.browserless_status.set(f"Found {len(compared_results)} matches")

        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
            if hasattr(self.gui, 'browserless_status'):
                self.gui.browserless_status.set("Search failed")
            print(f"[IMAGE SEARCH API ERROR] {e}")

    def _compare_image_search_results(self, query_image_path: str, ebay_results: List[Dict], csv_item: Dict) -> List[Dict]:
        """
        Compare query image against eBay search results and calculate similarity/profit.

        Args:
            query_image_path: Path to the query image
            ebay_results: List of eBay search results from API
            csv_item: CSV item data for profit calculation

        Returns:
            List of results with similarity and profit, filtered by threshold
        """
        import cv2
        import numpy as np
        import requests
        from gui.workers import compare_images
        from gui.utils import extract_price

        try:
            # Load query image
            query_img = cv2.imread(query_image_path)
            if query_img is None:
                print(f"[IMAGE COMPARE] Failed to load query image: {query_image_path}")
                return []

            print(f"[IMAGE COMPARE] Loaded query image: {query_img.shape}")

            # Get USD/JPY rate from settings
            usd_jpy_rate = 150.0
            if hasattr(self.gui, 'settings'):
                usd_jpy_rate = self.gui.settings.get_setting('ebay_analysis.usd_jpy_rate', 150.0)

            # Get max image comparison results from settings
            max_image_results = 10
            if hasattr(self.gui, 'settings'):
                max_image_results = self.gui.settings.get_setting('ebay_analysis.max_image_comparison_results', 10)

            # Limit eBay results to top X (image search returns them in relevance order)
            limited_ebay_results = ebay_results[:max_image_results]
            print(f"[IMAGE COMPARE] Comparing top {len(limited_ebay_results)} results (from {len(ebay_results)} total)")

            # Get CSV item price
            csv_price_text = csv_item.get('price_text', csv_item.get('price', '0'))
            csv_price_jpy = extract_price(csv_price_text)

            compared_results = []
            min_similarity = 50.0  # Minimum similarity threshold

            for idx, ebay_result in enumerate(limited_ebay_results):
                try:
                    # Get eBay image URL
                    ebay_image_url = ebay_result.get('image_url', '')
                    if not ebay_image_url:
                        continue

                    # Download eBay image
                    response = requests.get(ebay_image_url, timeout=10)
                    if response.status_code != 200:
                        continue

                    img_array = np.frombuffer(response.content, np.uint8)
                    ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    if ebay_img is None:
                        continue

                    # Compare images
                    similarity = compare_images(query_img, ebay_img)

                    # Only include results above threshold
                    if similarity < min_similarity:
                        continue

                    # Calculate profit margin
                    ebay_price_text = ebay_result.get('price', '$0')
                    ebay_price_usd = extract_price(ebay_price_text)

                    shipping_text = ebay_result.get('shipping', '$0')
                    shipping_usd = extract_price(shipping_text)

                    csv_price_usd = csv_price_jpy / usd_jpy_rate if usd_jpy_rate > 0 else 0
                    total_ebay_usd = ebay_price_usd + shipping_usd

                    profit_margin = ((total_ebay_usd / csv_price_usd - 1) * 100) if csv_price_usd > 0 else 0

                    # Add similarity and profit to result (formatted for display)
                    result_with_comparison = ebay_result.copy()
                    result_with_comparison['similarity'] = f"{similarity:.1f}%"
                    result_with_comparison['profit_margin'] = f"{profit_margin:.1f}%"
                    result_with_comparison['mandarake_price'] = f"¥{csv_price_jpy:,.0f}"

                    compared_results.append(result_with_comparison)

                    print(f"[IMAGE COMPARE] Result {idx+1}: {similarity:.1f}% similarity, {profit_margin:.1f}% profit - {ebay_result.get('title', 'N/A')[:50]}")

                except Exception as e:
                    print(f"[IMAGE COMPARE] Error comparing result {idx+1}: {e}")
                    continue

            # Sort by similarity descending
            compared_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)

            print(f"[IMAGE COMPARE] Found {len(compared_results)} matches above {min_similarity}% similarity (compared top {len(limited_ebay_results)} of {len(ebay_results)} results)")

            return compared_results

        except Exception as e:
            print(f"[IMAGE COMPARE ERROR] {e}")
            import traceback
            traceback.print_exc()
            return []

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

    def _image_compare_all_csv_items(self, silent: bool = False) -> None:
        """
        Batch image comparison for all filtered CSV items using eBay API.

        Args:
            silent: If True, skip confirmation dialogs (for scheduled execution)
        """
        if not hasattr(self.gui, 'csv_items_tree'):
            if not silent:
                messagebox.showwarning("No Data", "Please load a CSV file first.")
            return

        # Get filtered items
        items_list = self.csv_filtered_items if hasattr(self, 'csv_filtered_items') and self.csv_filtered_items else self.csv_compare_data

        if not items_list:
            if not silent:
                messagebox.showwarning("No Items", "No CSV items to compare.")
            return

        # Validate items have images
        items_with_images = [item for item in items_list if item.get('local_image') and Path(item.get('local_image')).exists()]

        if not items_with_images:
            if not silent:
                messagebox.showwarning("No Images", "No CSV items have local images. Please download images first.")
            return

        # Confirm action (skip if silent mode)
        if not silent:
            if not messagebox.askyesno(
                "Confirm Batch Image Search",
                f"This will perform image comparison for {len(items_with_images)} items using eBay API.\n\n"
                f"This may take several minutes. Continue?"
            ):
                return

        # Start batch comparison in background thread
        self._start_thread(self._run_batch_image_comparison, items_with_images)

    def _run_batch_image_comparison(self, items: List[Dict]) -> None:
        """Background worker for batch image comparison."""
        from ebay_api import EbayAPI

        try:
            # Get API credentials
            client_id = None
            client_secret = None

            if hasattr(self.gui, 'settings'):
                client_id = self.gui.settings.get_setting('ebay_api.client_id')
                client_secret = self.gui.settings.get_setting('ebay_api.client_secret')

            if not client_id or not client_secret:
                if hasattr(self.gui, 'run_queue'):
                    self.gui.run_queue.put(("error", "eBay API credentials not configured."))
                return

            # Initialize eBay API
            ebay_api = EbayAPI(client_id, client_secret)

            # Accumulate all results
            all_compared_results = []

            # Process each item
            for idx, csv_item in enumerate(items):
                local_image_path = csv_item.get('local_image', '')

                if hasattr(self.gui, 'run_queue'):
                    self.gui.run_queue.put(("browserless_status", f"Image comparing {idx + 1}/{len(items)}..."))

                print(f"[BATCH IMAGE COMPARE] Processing item {idx + 1}/{len(items)}: {csv_item.get('title', 'Unknown')}")

                try:
                    # Search by image
                    results = ebay_api.search_by_image_api_full(local_image_path)

                    if not results:
                        print(f"[BATCH IMAGE COMPARE] No results for item {idx + 1}")
                        continue

                    print(f"[BATCH IMAGE COMPARE] Got {len(results)} raw results for item {idx + 1}, comparing...")

                    # Compare images and filter
                    compared_results = self._compare_image_search_results(local_image_path, results, csv_item)

                    if compared_results:
                        all_compared_results.extend(compared_results)
                        print(f"[BATCH IMAGE COMPARE] Found {len(compared_results)} matches for item {idx + 1}")

                except Exception as e:
                    print(f"[BATCH IMAGE COMPARE] Error processing item {idx + 1}: {e}")
                    continue

            # Display all results
            if all_compared_results:
                if hasattr(self.gui, 'run_queue'):
                    self.gui.run_queue.put(("browserless_results", all_compared_results))
                    self.gui.run_queue.put(("browserless_status", f"Batch complete: Found {len(all_compared_results)} total matches from {len(items)} items"))

                # Save comparison results to CSV (update ebay_compared field)
                self.save_comparison_results_to_csv(all_compared_results)
                # Refresh the CSV tree to show checkmarks
                if hasattr(self.gui, 'run_queue'):
                    self.gui.run_queue.put(("refresh_csv_tree", None))

                print(f"[BATCH IMAGE COMPARE] Complete: {len(all_compared_results)} total matches")
            else:
                if hasattr(self.gui, 'run_queue'):
                    self.gui.run_queue.put(("browserless_status", f"Batch complete: No matches found from {len(items)} items"))
                    self.gui.run_queue.put(("info", "Batch image comparison complete. No matches found."))
                print(f"[BATCH IMAGE COMPARE] Complete: No matches found")

        except Exception as e:
            print(f"[BATCH IMAGE COMPARE ERROR] {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self.gui, 'run_queue'):
                self.gui.run_queue.put(("error", f"Batch image comparison failed: {e}"))

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
        if (hasattr(self.gui, 'ebay_search_manager') and
            self.gui.ebay_search_manager):
            self.gui.ebay_search_manager.display_browserless_results(display_results)

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
                # Support both old format (mandarake_item) and new format (store_link)
                mandarake_item = result.get('mandarake_item', {})
                url = mandarake_item.get('url', mandarake_item.get('product_url', ''))

                # If no URL from mandarake_item, try store_link (image comparison format)
                if not url:
                    url = result.get('store_link', '')

                if url:
                    # Handle both old format (best_match) and new format (direct fields)
                    best_match = result.get('best_match', {})
                    has_match = bool(best_match) or result.get('similarity', 0) > 0

                    # Get similarity - could be float or already formatted string
                    similarity = result.get('similarity', 0)
                    if isinstance(similarity, str):
                        similarity = float(similarity.rstrip('%')) if similarity and similarity != '-' else 0

                    # Get profit margin - could be float or already formatted string
                    profit = result.get('profit_margin', 0)
                    if isinstance(profit, str):
                        profit = float(profit.rstrip('%')) if profit else 0

                    url_to_results[url] = {
                        'ebay_compared': datetime.now().isoformat(),
                        'ebay_match_found': 'Yes' if has_match else 'No',
                        'ebay_best_match_title': best_match.get('title', '') if best_match else result.get('ebay_title', ''),
                        'ebay_similarity': f"{similarity:.1f}" if similarity > 0 else '',
                        'ebay_price': best_match.get('price', '') if best_match else result.get('ebay_price', ''),
                        'ebay_profit_margin': f"{profit:.1f}%" if profit != 0 else ''
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
            if hasattr(self.gui, 'browserless_status'):
                self.gui.browserless_status.set("No items have been compared yet")
            messagebox.showinfo(
                "No Comparison Results",
                "No items have been compared yet.\n\n"
                "Please run 'Compare Selected' or 'Compare All' first."
            )
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
                if hasattr(self.gui, 'browserless_status'):
                    self.gui.browserless_status.set(f"Cleared comparison results for {compared_count} items")
                print(f"[CLEAR RESULTS] Cleared comparison results for {compared_count} items")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear results: {e}")
                print(f"[CLEAR RESULTS ERROR] {e}")

    def _start_thread(self, target: Callable, *args) -> None:
        """Start a background thread."""
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()
