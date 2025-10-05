#!/usr/bin/env python3
"""Results Display Manager for modular GUI results visualization."""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import csv
import webbrowser
import logging
from PIL import Image, ImageTk
from typing import Dict, Any, Optional, List
import requests
from io import BytesIO


class ResultsDisplayManager:
    """Manages the display and visualization of search results."""

    def __init__(self, main_window):
        """
        Initialize Results Display Manager.
        
        Args:
            main_window: The main GUI window instance
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
    def load_results_table(self, csv_path: Path):
        """
        Load results table from CSV file with thumbnail support.
        
        Args:
            csv_path: Path to the CSV file to load
        """
        print(f"[RESULTS DISPLAY] Loading results table from: {csv_path}")
        if not hasattr(self.main_window, 'result_tree'):
            return
            
        # Clear existing results
        for item in self.main_window.result_tree.get_children():
            self.main_window.result_tree.delete(item)
        self.main_window.result_links.clear()
        self.main_window.result_images.clear()
        self.main_window.result_data.clear()
        
        if not csv_path or not csv_path.exists():
            print(f"[RESULTS DISPLAY] CSV not found: {csv_path}")
            self.main_window.status_var.set(f'CSV not found: {csv_path}')
            return
            
        show_images = getattr(self.main_window, 'show_images_var', None)
        show_images = show_images.get() if show_images else False
        print(f"[RESULTS DISPLAY] Show images setting: {show_images}")
        
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
                            print(f"[RESULTS DISPLAY] Attempting to load local image: {local_image_path}")
                            try:
                                pil_img = Image.open(local_image_path)
                                pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                                photo = ImageTk.PhotoImage(pil_img)
                                item_kwargs['image'] = photo
                                print(f"[RESULTS DISPLAY] Successfully loaded local thumbnail: {local_image_path}")
                            except Exception as e:
                                print(f"[RESULTS DISPLAY] Failed to load local image {local_image_path}: {e}")
                                photo = None

                        # If no local image or local image failed, try web image
                        if not photo and web_image_url:
                            print(f"[RESULTS DISPLAY] Attempting to download web image: {web_image_url}")
                            try:
                                response = requests.get(web_image_url, timeout=10)
                                response.raise_for_status()
                                pil_img = Image.open(BytesIO(response.content))
                                pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                                photo = ImageTk.PhotoImage(pil_img)
                                item_kwargs['image'] = photo
                                print(f"[RESULTS DISPLAY] Successfully downloaded web thumbnail: {web_image_url}")
                            except Exception as e:
                                print(f"[RESULTS DISPLAY] Failed to download web image {web_image_url}: {e}")
                                photo = None

                        if not photo:
                            print(f"[RESULTS DISPLAY] No image available for row: {title}")
                    else:
                        print(f"[RESULTS DISPLAY] Show images disabled")
                        
                    item_id = self.main_window.result_tree.insert('', tk.END, **item_kwargs)
                    self.main_window.result_data[item_id] = row
                    if photo:
                        self.main_window.result_images[item_id] = photo
                    self.main_window.result_links[item_id] = link
                    
            self.main_window.status_var.set(f'Loaded results from {csv_path}')
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to load results: {exc}')

    def toggle_thumbnails(self):
        """Toggle thumbnail display in the results tree."""
        show_images = getattr(self.main_window, 'show_images_var', None)
        if not show_images:
            return
            
        show_images_value = show_images.get()

        # Iterate through all items in the treeview
        for item_id in self.main_window.result_tree.get_children():
            if show_images_value:
                # Show image if available
                if item_id in self.main_window.result_images:
                    self.main_window.result_tree.item(item_id, image=self.main_window.result_images[item_id])
            else:
                # Hide image by setting empty image
                self.main_window.result_tree.item(item_id, image='')

    def handle_result_double_click(self, event=None):
        """Handle double-click on result item to open URL."""
        selection = self.main_window.result_tree.selection()
        if not selection:
            return
        item = selection[0]
        link = self.main_window.result_links.get(item)
        if link:
            webbrowser.open(link)

    def show_result_tree_menu(self, event):
        """Show context menu on the result tree."""
        selection = self.main_window.result_tree.selection()
        if selection:
            self.main_window.result_tree_menu.post(event.x_root, event.y_root)

    def search_by_image_api(self):
        """Search selected result item by image using eBay API."""
        selection = self.main_window.result_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item_data = self.main_window.result_data.get(item_id)
        if not item_data:
            messagebox.showerror("Error", "Could not find data for the selected item.")
            return

        local_image_path = item_data.get('local_image')
        if not local_image_path or not Path(local_image_path).exists():
            messagebox.showerror("Error", "Local image not found for this item. Please download images first.")
            return

        from mandarake_scraper import EbayAPI
        # Note: eBay API credentials removed from GUI - using web scraping instead
        ebay_api = EbayAPI("", "")

        self.main_window.status_var.set("Searching by image on eBay (API)...")
        url = ebay_api.search_by_image_api(local_image_path)
        if url:
            webbrowser.open(url)
            self.main_window.status_var.set("Search by image (API) complete.")
        else:
            messagebox.showerror("Error", "Could not find results using eBay API. Check logs for details.")
            self.main_window.status_var.set("Search by image (API) failed.")

    def search_by_image_web(self):
        """Search selected result item by image using web method."""
        selection = self.main_window.result_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item_data = self.main_window.result_data.get(item_id)
        if not item_data:
            messagebox.showerror("Error", "Could not find data for the selected item.")
            return

        local_image_path = item_data.get('local_image')
        if not local_image_path or not Path(local_image_path).exists():
            messagebox.showerror("Error", "Local image not found for this item. Please download images first.")
            return

        self.main_window.status_var.set("Searching by image on eBay (Web)...")
        self.main_window._start_thread(self._run_web_image_search, local_image_path)

    def _run_web_image_search(self, image_path):
        """Run web image search in background thread."""
        from ebay_image_search import run_ebay_image_search
        url = run_ebay_image_search(image_path)
        if "Error" not in url:
            webbrowser.open(url)
            self.main_window.run_queue.put(("status", "Search by image (Web) complete."))
        else:
            self.main_window.run_queue.put(("error", "Could not find results using web search."))

    def display_ebay_analysis_results(self, results):
        """
        Display eBay analysis results in the treeview.
        
        Args:
            results: List of result dictionaries to display
        """
        # Clear existing results
        for item in self.main_window.ebay_results_tree.get_children():
            self.main_window.ebay_results_tree.delete(item)

        # Check if these are image comparison results (have string values) or regular eBay results (have numeric values)
        is_image_comparison = results and isinstance(results[0].get('store_price'), str)

        if is_image_comparison:
            # Image comparison results - display as-is without numeric formatting
            for result in results:
                values = (
                    result['title'][:40] + ('...' if len(result['title']) > 40 else ''),
                    result['store_price'],  # Already formatted string
                    str(result['ebay_sold_count']),
                    result['ebay_median_price'],  # Already formatted string
                    result.get('ebay_price_range', 'N/A'),
                    result['profit_margin'],  # Already formatted string
                    result.get('estimated_profit', 'N/A')  # Already formatted string
                )
                self.main_window.ebay_results_tree.insert('', tk.END, values=values)
        else:
            # Regular eBay results - format as numbers
            # Sort by profit margin (highest first)
            results.sort(key=lambda x: x['profit_margin'], reverse=True)

            # Add results to treeview
            for result in results:
                values = (
                    result['title'][:40] + ('...' if len(result['title']) > 40 else ''),
                    f"¥{result['store_price']:,}",
                    str(result['ebay_sold_count']),
                    f"${result['ebay_median_price']:.2f}",
                    result.get('ebay_price_range', 'N/A'),
                    f"{result['profit_margin']:+.1f}%",
                    f"${result.get('estimated_profit', 0):.2f}"
                )
                self.main_window.ebay_results_tree.insert('', tk.END, values=values)

    def display_browserless_results(self, results):
        """
        Display browserless search results in the tree view with thumbnails.
        
        Args:
            results: List of search result dictionaries
        """
        # Clear existing results and images
        for item in self.main_window.browserless_tree.get_children():
            self.main_window.browserless_tree.delete(item)
        self.main_window.browserless_images.clear()

        # Store results for URL opening
        self.main_window.browserless_results_data = results

        # Add new results with thumbnails
        for i, result in enumerate(results, 1):
            values = (
                result['title'],  # Show full title, no truncation
                result['price'],
                result['shipping'],
                result.get('store_price', ''),
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
                    print(f"[RESULTS DISPLAY] Failed to load thumbnail {i}: {e}")
                    photo = None

            # Insert with or without image
            if photo:
                self.main_window.browserless_tree.insert('', 'end', iid=str(i), text='', values=values, image=photo)
                self.main_window.browserless_images[str(i)] = photo  # Keep reference to prevent garbage collection
            else:
                self.main_window.browserless_tree.insert('', 'end', iid=str(i), text=str(i), values=values)

        print(f"[RESULTS DISPLAY] Displayed {len(results)} results in tree view ({len(self.main_window.browserless_images)} with thumbnails)")

    def open_browserless_url(self, event):
        """Open selected eBay URL from browserless results."""
        selection = self.main_window.browserless_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.main_window.browserless_results_data):
                url = self.main_window.browserless_results_data[index]['url']
                if url and not any(x in url for x in ["No URL available", "Placeholder URL", "Invalid URL", "URL Error"]):
                    print(f"[RESULTS DISPLAY] Opening URL: {url}")
                    webbrowser.open(url)
                else:
                    messagebox.showwarning("Invalid URL", f"Cannot open URL: {url}")
        except (ValueError, IndexError) as e:
            print(f"[RESULTS DISPLAY] Error opening URL: {e}")

    def clean_ebay_url(self, url: str) -> str:
        """
        Clean and validate eBay URL.
        
        Args:
            url: The URL to clean
            
        Returns:
            Cleaned and validated URL
        """
        if not url:
            return "No URL available"

        # Handle descriptive URLs (like search results pages)
        if url.startswith("Search Results Page:"):
            return url  # Return as-is for descriptive URLs

        try:
            from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
            import re

            # Remove any placeholder URLs
            if ("listing/" in url and url.count("/") < 4) or re.match(r'https://www\.ebay\.com/listing/\d+$', url):
                return "Placeholder URL - not accessible"

            # Handle relative URLs
            if url.startswith("/"):
                url = f"https://www.ebay.com{url}"
            elif not url.startswith("http"):
                url = f"https://www.ebay.com/{url}"

            # Parse the URL
            parsed = urlparse(url)

            # Extract item ID from various eBay URL formats
            item_id = None

            # Try to extract from /itm/ URLs
            itm_match = re.search(r'/itm/([^/?]+)', parsed.path)
            if itm_match:
                item_id = itm_match.group(1)

            # Try to extract from query parameters
            if not item_id and parsed.query:
                query_params = parse_qs(parsed.query)
                if 'item' in query_params:
                    item_id = query_params['item'][0]

            # If we found an item ID, construct a clean URL
            if item_id:
                # Remove non-numeric characters from item ID to get core ID
                clean_item_id = re.sub(r'[^0-9]', '', item_id)
                if clean_item_id:
                    return f"https://www.ebay.com/itm/{clean_item_id}"

            # If no item ID found, return the cleaned original URL
            if parsed.netloc and 'ebay.com' in parsed.netloc.lower():
                # Remove tracking parameters but keep essential ones
                essential_params = ['_nkw', '_sacat', 'item', 'hash']
                if parsed.query:
                    query_params = parse_qs(parsed.query, keep_blank_values=True)
                    cleaned_params = {k: v for k, v in query_params.items() if k in essential_params}
                    clean_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""
                else:
                    clean_query = ""

                return urlunparse((
                    parsed.scheme or 'https',
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    clean_query,
                    ''  # Remove fragment
                ))

            # Fallback - return original if it looks like a valid URL
            return url if url.startswith('http') else f"Invalid URL: {url}"

        except Exception as e:
            print(f"[RESULTS DISPLAY] URL cleaning error: {e}")
            return f"URL Error: {url}"

    def convert_image_results_to_analysis(self, search_result: dict) -> list:
        """
        Convert image search results to the format expected by the analysis display.
        
        Args:
            search_result: Dictionary containing image search results
            
        Returns:
            List of analysis results formatted for display
        """
        results = []

        # Get configuration values
        try:
            usd_to_jpy = float(self.main_window.usd_jpy_rate.get())
            min_profit = float(self.main_window.min_profit_margin.get())
            min_sold = int(self.main_window.min_sold_items.get())
        except (ValueError, AttributeError):
            usd_to_jpy = 150
            min_profit = 20
            min_sold = 3

        # Check if we have enough sold items
        if search_result['sold_count'] < min_sold:
            return results

        # Calculate profit margins for the image search result
        median_price_usd = search_result['median_price']
        avg_price_usd = search_result['avg_price']

        # Estimate various store price points for comparison
        # (since we don't have a specific store price for the image)
        estimated_store_prices = [
            median_price_usd * usd_to_jpy * 0.3,  # 30% of USD median
            median_price_usd * usd_to_jpy * 0.5,  # 50% of USD median
            median_price_usd * usd_to_jpy * 0.7,  # 70% of USD median
        ]

        for i, store_price_jpy in enumerate(estimated_store_prices):
            store_usd = store_price_jpy / usd_to_jpy

            # Estimate shipping and fees
            estimated_fees = median_price_usd * 0.15 + 5
            net_proceeds = median_price_usd - estimated_fees

            profit_margin = ((net_proceeds - store_usd) / store_usd) * 100 if store_usd > 0 else 0

            if profit_margin > min_profit:
                # Create search term info
                search_term = search_result.get('search_term', 'Image search result')
                if search_result.get('lens_results', {}).get('product_names'):
                    search_term = search_result['lens_results']['product_names'][0]

                title = f"{search_term} (Est. {int((i+1)*30)}% of eBay price)"

                results.append({
                    'title': title,
                    'store_price': int(store_price_jpy),
                    'ebay_sold_count': search_result['sold_count'],
                    'ebay_median_price': median_price_usd,
                    'ebay_avg_price': avg_price_usd,
                    'ebay_price_range': f"${search_result['min_price']:.2f} - ${search_result['max_price']:.2f}",
                    'profit_margin': profit_margin,
                    'estimated_profit': net_proceeds - store_usd
                })

        # Sort by profit margin (highest first)
        results.sort(key=lambda x: x['profit_margin'], reverse=True)

        return results[:5]  # Return top 5 scenarios

    def display_csv_comparison_results(self, results):
        """
        Display CSV comparison results in the browserless tree.
        
        Args:
            results: List of comparison result dictionaries
        """
        # Convert format to match existing display
        display_results = []
        for r in results:
            display_results.append({
                'title': r['ebay_title'],
                'price': r['ebay_price'],
                'shipping': r['shipping'],
                'store_price': r.get('store_price', ''),
                'profit_margin': r['profit_display'],
                'sold_date': r.get('sold_date', ''),  # Keep actual sold date
                'similarity': r['similarity_display'],
                'url': r['ebay_link'],
                'image_url': r['thumbnail']
            })

        self.display_browserless_results(display_results)
