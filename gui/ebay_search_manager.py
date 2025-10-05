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
        
        self.tree['columns'] = ('title', 'price', 'shipping', 'store_price',
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
            'store_price': 'Store ¥',
            'profit_margin': 'Profit %',
            'sold_date': 'Sold Date',
            'similarity': 'Similarity %',
            'url': 'eBay URL'
        }
        
        widths = {
            'title': 280,
            'price': 80,
            'shipping': 70,
            'store_price': 90,
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

    def display_browserless_results(self, results):
        """Display browserless search results in the tree view with thumbnails."""
        from PIL import Image, ImageTk
        import requests
        from io import BytesIO

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
                result['url'],  # eBay URL
                result.get('mandarake_url', '')  # Mandarake URL
            )

            # Try to load thumbnails (eBay and Mandarake side-by-side if both exist)
            ebay_image_url = result.get('image_url', '')
            mandarake_image_url = result.get('mandarake_image_url', '')
            photo = None

            try:
                ebay_img = None
                mandarake_img = None

                # Load eBay image
                if ebay_image_url:
                    try:
                        response = requests.get(ebay_image_url, timeout=5)
                        response.raise_for_status()
                        ebay_img = Image.open(BytesIO(response.content))
                        ebay_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    except Exception as e:
                        print(f"[THUMB] Failed to load eBay thumbnail {i}: {e}")

                # Load Mandarake image
                if mandarake_image_url:
                    try:
                        response = requests.get(mandarake_image_url, timeout=5)
                        response.raise_for_status()
                        mandarake_img = Image.open(BytesIO(response.content))
                        mandarake_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    except Exception as e:
                        print(f"[THUMB] Failed to load Mandarake thumbnail {i}: {e}")

                # Create composite image if we have both, or use single image
                if ebay_img and mandarake_img:
                    # Side-by-side composite
                    total_width = ebay_img.width + mandarake_img.width + 2  # +2 for separator
                    max_height = max(ebay_img.height, mandarake_img.height)
                    composite = Image.new('RGB', (total_width, max_height), 'white')
                    composite.paste(ebay_img, (0, 0))
                    composite.paste(mandarake_img, (ebay_img.width + 2, 0))
                    photo = ImageTk.PhotoImage(composite)
                elif ebay_img:
                    photo = ImageTk.PhotoImage(ebay_img)
                elif mandarake_img:
                    photo = ImageTk.PhotoImage(mandarake_img)

            except Exception as e:
                print(f"[SCRAPY SEARCH] Failed to load thumbnails {i}: {e}")
                photo = None

            # Insert with or without image
            if photo:
                self.tree.insert('', 'end', iid=str(i), text='', values=values, image=photo)
                self.images[str(i)] = photo  # Keep reference to prevent garbage collection
            else:
                self.tree.insert('', 'end', iid=str(i), text=str(i), values=values)

        print(f"[SCRAPY SEARCH] Displayed {len(results)} results in tree view ({len(self.images)} with thumbnails)")

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

    def search_ebay_sold(self, title: str) -> dict | None:
        """Search eBay for sold listings of an item with optional lazy search optimization.

        Args:
            title: Product title to search for

        Returns:
            dict: Search results with sold_count, median_price, etc., or None if failed
        """
        try:
            # Import required modules
            from mandarake_scraper import EbayAPI

            # Create a dummy EbayAPI instance. No credentials needed for web scraping.
            ebay_api = EbayAPI("", "")

            # Get settings from main GUI
            try:
                days_back = int(self.main.ebay_days_back.get()) if hasattr(self.main, 'ebay_days_back') else 90
            except (ValueError, AttributeError):
                days_back = 90

            # Check if lazy search is enabled
            lazy_search_enabled = getattr(self.main, 'lazy_search_enabled', None)
            use_lazy_search = lazy_search_enabled.get() if lazy_search_enabled else False

            print(f"[EBAY DEBUG] Searching eBay for: '{title}' (last {days_back} days) using WEB SCRAPING")
            if use_lazy_search:
                print(f"[LAZY SEARCH] Enabled - will try optimized terms if initial search fails")

            # Search for sold listings using web scraping
            result = ebay_api.search_sold_listings_web(title, days_back=days_back)

            # If lazy search is enabled and we got poor results OR eBay is blocking, try optimized search terms
            if use_lazy_search and (not result or result.get('sold_count', 0) < 3 or result.get('error')):
                error_info = f" (Error: {result.get('error')})" if result and result.get('error') else ""
                print(f"[LAZY SEARCH] Initial search yielded {result.get('sold_count', 0) if result else 0} results{error_info} - trying optimized terms")

                try:
                    from search_optimizer import SearchOptimizer
                    optimizer = SearchOptimizer()

                    # Get optimized search terms
                    optimization = optimizer.optimize_search_term(title, lazy_mode=True)
                    optimized_terms = optimization['confidence_order'][:5]  # Try top 5 optimized terms

                    print(f"[LAZY SEARCH] Trying {len(optimized_terms)} optimized terms: {optimized_terms}")

                    best_result = result  # Keep original result as fallback
                    best_count = result.get('sold_count', 0) if result else 0

                    for optimized_term in optimized_terms:
                        if optimized_term != title:  # Skip if same as original
                            print(f"[LAZY SEARCH] Trying optimized term: '{optimized_term}'")

                            opt_result = ebay_api.search_sold_listings_web(optimized_term, days_back=days_back)

                            if opt_result and opt_result.get('sold_count', 0) > best_count:
                                print(f"[LAZY SEARCH] Better result found: {opt_result['sold_count']} items vs {best_count}")
                                best_result = opt_result
                                best_result['search_term_used'] = optimized_term
                                best_count = opt_result['sold_count']

                                # If we found good results (5+ items), stop searching
                                if best_count >= 5:
                                    break

                    result = best_result

                except Exception as e:
                    print(f"[LAZY SEARCH] Error during optimization: {e}")
                    # Continue with original result

                    # If eBay is blocking, explain why lazy search can't help
                    if result and result.get('error') and any(term in str(result.get('error')).lower() for term in ['captcha', 'blocked', 'error page']):
                        print(f"[LAZY SEARCH] Note: eBay is blocking automated access entirely. Lazy search cannot overcome CAPTCHA/blocking issues.")
                        print(f"[LAZY SEARCH] Recommendation: Use the regular eBay Analysis tab with manual product titles instead.")

            if result and result.get('error'):
                print(f"[EBAY DEBUG] eBay web scrape error: {result['error']}")
                return None

            if not result or result.get('sold_count', 0) == 0:
                search_term_used = result.get('search_term_used', title) if result else title
                print(f"[EBAY DEBUG] No sold listings found for: {search_term_used}")
                return None

            search_term_used = result.get('search_term_used', title)
            if search_term_used != title:
                print(f"[LAZY SEARCH] Success! Used optimized term: '{search_term_used}'")

            print(f"[EBAY DEBUG] Found {result['sold_count']} sold items, median price: ${result['median_price']}")
            return result

        except Exception as e:
            print(f"[EBAY DEBUG] eBay search error: {e}")
            return None

    def convert_image_results_to_analysis(self, search_result: dict) -> list:
        """Convert image search results to the format expected by the analysis display.

        Args:
            search_result: Dict with sold_count, median_price, avg_price, etc.

        Returns:
            list: Up to 5 scenarios with different Mandarake price estimates
        """
        results = []

        # Get configuration values from main GUI
        try:
            usd_to_jpy = float(self.main.usd_jpy_rate.get()) if hasattr(self.main, 'usd_jpy_rate') else 150.0
            min_profit = float(self.main.min_profit_margin.get()) if hasattr(self.main, 'min_profit_margin') else 20.0
            min_sold = int(self.main.min_sold_items.get()) if hasattr(self.main, 'min_sold_items') else 3
        except (ValueError, AttributeError):
            usd_to_jpy = 150.0
            min_profit = 20.0
            min_sold = 3

        # Check if we have enough sold items
        if search_result['sold_count'] < min_sold:
            return results

        # Calculate profit margins for the image search result
        median_price_usd = search_result['median_price']
        avg_price_usd = search_result['avg_price']

        # Estimate various Mandarake price points for comparison
        # (since we don't have a specific Mandarake price for the image)
        estimated_mandarake_prices = [
            median_price_usd * usd_to_jpy * 0.3,  # 30% of USD median
            median_price_usd * usd_to_jpy * 0.5,  # 50% of USD median
            median_price_usd * usd_to_jpy * 0.7,  # 70% of USD median
        ]

        for i, mandarake_price_jpy in enumerate(estimated_mandarake_prices):
            mandarake_usd = mandarake_price_jpy / usd_to_jpy

            # Estimate shipping and fees
            estimated_fees = median_price_usd * 0.15 + 5
            net_proceeds = median_price_usd - estimated_fees

            profit_margin = ((net_proceeds - mandarake_usd) / mandarake_usd) * 100 if mandarake_usd > 0 else 0

            if profit_margin > min_profit:
                # Create search term info
                search_term = search_result.get('search_term', 'Image search result')
                if search_result.get('lens_results', {}).get('product_names'):
                    search_term = search_result['lens_results']['product_names'][0]

                title = f"{search_term} (Est. {int((i+1)*30)}% of eBay price)"

                results.append({
                    'title': title,
                    'mandarake_price': int(mandarake_price_jpy),
                    'ebay_sold_count': search_result['sold_count'],
                    'ebay_median_price': median_price_usd,
                    'ebay_avg_price': avg_price_usd,
                    'ebay_price_range': f"${search_result['min_price']:.2f} - ${search_result['max_price']:.2f}",
                    'profit_margin': profit_margin,
                    'estimated_profit': net_proceeds - mandarake_usd
                })

        # Sort by profit margin (highest first)
        results.sort(key=lambda x: x['profit_margin'], reverse=True)

        return results[:5]  # Return top 5 scenarios

    def send_browserless_to_review(self, alert_tab) -> None:
        """Send selected eBay result to Review/Alerts tab.

        Args:
            alert_tab: AlertTab instance to send results to
        """
        selection = self.tree.selection()
        if not selection:
            self.status.set("No item selected")
            return

        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.results_data):
                result = self.results_data[index]

                # Check if this is a comparison result (has similarity/profit data)
                if 'similarity' in result or 'profit_margin' in result:
                    # Find the corresponding item in all_comparison_results
                    matching_result = None
                    for comp_result in getattr(self.gui, 'all_comparison_results', []):
                        if comp_result.get('ebay_link') == result.get('url'):
                            matching_result = comp_result
                            break

                    if matching_result:
                        # Send to alerts using existing method
                        alert_tab.add_filtered_alerts([matching_result])
                        # Explicitly refresh the alert tab to ensure it displays the new item
                        alert_tab._load_alerts()
                        self.status.set(f"Sent '{result['title'][:50]}...' to Review/Alerts")
                        print(f"[SEND TO REVIEW] Added item to alerts: {result['title']}")
                    else:
                        self.status.set("Could not find comparison data for this item")
                else:
                    # This is a raw eBay search result without comparison data
                    self.status.set("Item has no comparison data - use 'Compare Selected' first")
                    print("[SEND TO REVIEW] Item has no comparison data")
        except (ValueError, IndexError) as e:
            print(f"[SEND TO REVIEW] Error: {e}")
            self.status.set(f"Error sending to review: {e}")

    def open_browserless_url(self, event) -> None:
        """Open eBay or Mandarake URL based on which column is double-clicked.

        Args:
            event: Mouse event with x, y coordinates
        """
        import webbrowser

        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]

        # Identify which column was clicked
        column = self.tree.identify_column(event.x)
        # Column format is '#0', '#1', '#2', etc. where #0 is thumbnail, #1 is first data column

        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.results_data):
                result = self.results_data[index]

                # Determine which URL to open based on column
                # Columns: title(#1), price(#2), shipping(#3), mandarake_price(#4), profit_margin(#5),
                #          sold_date(#6), similarity(#7), url(#8), mandarake_url(#9)
                if column == '#9':  # Mandarake URL column
                    url = result.get('mandarake_url', '')
                    url_type = "Mandarake"
                else:  # Default to eBay URL for all other columns
                    url = result.get('url', '')
                    url_type = "eBay"

                if url and not any(x in url for x in ["No URL available", "Placeholder URL", "Invalid URL", "URL Error"]):
                    print(f"[BROWSERLESS SEARCH] Opening {url_type} URL: {url}")
                    webbrowser.open(url)
                else:
                    print(f"[BROWSERLESS SEARCH] Cannot open {url_type} URL: {url}")
            else:
                print(f"[URL DEBUG] Index {index} out of range (data length: {len(self.results_data)})")
        except (ValueError, IndexError) as e:
            print(f"[BROWSERLESS SEARCH] Error opening URL: {e}")
            pass
