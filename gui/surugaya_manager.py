"""
Suruga-ya Scraper Manager

Handles Suruga-ya scraping coordination including:
- Running scraper in background thread
- CSV merging with timestamps
- Title translation
- Parallel image downloading
"""

import csv
import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from deep_translator import GoogleTranslator


class SurugayaManager:
    """Manager for Suruga-ya scraping operations."""

    def __init__(self, run_queue: queue.Queue, settings_manager):
        """
        Initialize Suruga-ya Manager.

        Args:
            run_queue: Queue for communicating status to main thread
            settings_manager: Settings manager for accessing configuration
        """
        self.run_queue = run_queue
        self.settings = settings_manager
        self.current_scraper = None

    def run_scraper(self, config_path: str, cancel_flag: threading.Event) -> None:
        """
        Run Suruga-ya scraper in background thread.

        Args:
            config_path: Path to JSON configuration file
            cancel_flag: Event flag to check for cancellation
        """
        config_path = Path(config_path)

        try:
            # Load config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Check if URL was provided directly
            provided_url = config.get('search_url')

            keyword = config.get('keyword', '')
            category1 = config.get('category1', '7')  # Main category - default to Books
            category2 = config.get('category2')  # Detailed category
            shop_code = config.get('shop', 'all')
            max_pages = config.get('max_pages', 2)
            show_out_of_stock = config.get('show_out_of_stock', False)
            exclude_word = config.get('exclude_word', '')
            condition = config.get('condition', 'all')
            adult_only = config.get('adult_only', False)

            # Calculate max results from max_pages (assuming ~50 items per page)
            try:
                max_pages = int(max_pages) if max_pages else 2
            except (ValueError, TypeError):
                max_pages = 2
            max_results = max_pages * 50

            # Initialize scraper
            from scrapers.surugaya_scraper import SurugayaScraper
            scraper = SurugayaScraper()
            self.current_scraper = scraper
            scraper._cancel_requested = False

            # Use provided URL or build from params
            if provided_url and 'suruga-ya.jp' in provided_url:
                print(f"[SURUGA-YA SEARCH] Using provided URL: {provided_url}")
                search_desc = f"Searching Suruga-ya with provided URL"

                # Run search with provided URL
                results = scraper.search(
                    keyword=keyword,
                    category1=category1,
                    category2=category2,
                    shop_code=shop_code,
                    exclude_word=exclude_word,
                    condition=condition,
                    max_results=max_results,
                    show_out_of_stock=show_out_of_stock,
                    adult_only=adult_only,
                    search_url=provided_url  # Pass the provided URL directly
                )
            else:
                # Build URL with new parameters
                from store_codes.surugaya_codes import build_surugaya_search_url
                search_url = build_surugaya_search_url(
                    keyword=keyword,
                    category1=category1,
                    category2=category2,
                    shop_code=shop_code,
                    exclude_word=exclude_word,
                    condition=condition,
                    in_stock_only=not show_out_of_stock,
                    adult_only=adult_only
                )
                print(f"[SURUGA-YA SEARCH] Built URL from params: {search_url}")
                search_desc = f"Searching Suruga-ya: {keyword}"
                if exclude_word:
                    search_desc += f" (excluding: {exclude_word})"

                # Run search with built URL
                results = scraper.search(
                    keyword=keyword,
                    category1=category1,
                    category2=category2,
                    shop_code=shop_code,
                    exclude_word=exclude_word,
                    condition=condition,
                    max_results=max_results,
                    show_out_of_stock=show_out_of_stock,
                    adult_only=adult_only
                )

            self.run_queue.put(("status", search_desc))

            # Save results to CSV and download images
            if results:
                csv_path = self._save_results_to_csv(results, config_path)

                # Update config with CSV path
                config['csv'] = str(csv_path)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                # DISPLAY RESULTS IMMEDIATELY (before downloading images)
                self.run_queue.put(("results", str(config_path)))

                # Download images in parallel
                self._download_images(results, config_path, csv_path)

                # Reload the results in the treeview (to show images)
                self.run_queue.put(("results", str(config_path)))
            else:
                self.run_queue.put(("status", "No results found"))

        except Exception as exc:
            import traceback
            traceback.print_exc()
            if cancel_flag.is_set():
                self.run_queue.put(("status", "Search cancelled."))
            else:
                self.run_queue.put(("error", f"Suruga-ya search failed: {exc}"))
        finally:
            self.current_scraper = None
            self.run_queue.put(("cleanup", str(config_path)))

    def _save_results_to_csv(self, results: List[Dict], config_path: Path) -> Path:
        """
        Save Suruga-ya results to CSV with translation and merging.

        Args:
            results: List of scraped results
            config_path: Path to config file (used for CSV naming)

        Returns:
            Path: Path to saved CSV file
        """
        csv_filename = config_path.stem + '.csv'
        csv_path = Path('results') / csv_filename
        csv_path.parent.mkdir(exist_ok=True)

        # Translate all titles quickly
        translator = GoogleTranslator(source='ja', target='en')
        print(f"[SURUGAYA] Translating {len(results)} titles...", flush=True)
        for i, item in enumerate(results):
            title = item.get('title', '')
            if title:
                try:
                    if len(title) > 4000:
                        title_en = translator.translate(title[:4000])
                    else:
                        title_en = translator.translate(title)
                    item['title_en'] = title_en
                    if (i + 1) % 10 == 0:
                        print(f"[SURUGAYA] Translated {i+1}/{len(results)}", flush=True)
                except Exception as e:
                    print(f"[SURUGAYA] Failed to translate title {i+1}: {e}", flush=True)
                    item['title_en'] = title
            else:
                item['title_en'] = ''

        # Merge with existing CSV if it exists
        current_time = datetime.now()
        existing_items = {}

        if csv_path.exists():
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get('url', '')
                        if url:
                            existing_items[url] = row
                print(f"[SURUGA-YA] Loaded {len(existing_items)} existing items from CSV")
            except Exception as e:
                print(f"[SURUGA-YA] Could not read existing CSV: {e}")
                existing_items = {}

        # Merge new results with existing items
        new_count = 0
        updated_count = 0
        merged_items = {}

        # First, add all existing items
        for url, item in existing_items.items():
            merged_items[url] = item

        # Then add/update with new results
        for result in results:
            url = result.get('url', '')
            if not url:
                continue

            # Add timestamps
            if url in existing_items:
                # Update last_seen but keep first_seen from existing
                result['first_seen'] = existing_items[url].get('first_seen', current_time.isoformat())
                result['last_seen'] = current_time.isoformat()
                # Preserve eBay comparison results if they exist
                result['ebay_compared'] = existing_items[url].get('ebay_compared', '')
                result['ebay_match_found'] = existing_items[url].get('ebay_match_found', '')
                result['ebay_best_match_title'] = existing_items[url].get('ebay_best_match_title', '')
                result['ebay_similarity'] = existing_items[url].get('ebay_similarity', '')
                result['ebay_price'] = existing_items[url].get('ebay_price', '')
                result['ebay_profit_margin'] = existing_items[url].get('ebay_profit_margin', '')
                updated_count += 1
            else:
                # New item
                result['first_seen'] = current_time.isoformat()
                result['last_seen'] = current_time.isoformat()
                result['ebay_compared'] = ''
                result['ebay_match_found'] = ''
                result['ebay_best_match_title'] = ''
                result['ebay_similarity'] = ''
                result['ebay_price'] = ''
                result['ebay_profit_margin'] = ''
                new_count += 1

            merged_items[url] = result

        # Sort by first_seen (newest first)
        sorted_items = sorted(merged_items.values(), key=lambda x: x.get('first_seen', ''), reverse=True)

        # Trim old items if max_csv_items is set
        max_csv_items = self.settings.get_setting('scraper.max_csv_items', 0) if self.settings else 0
        if max_csv_items > 0 and len(sorted_items) > max_csv_items:
            removed_count = len(sorted_items) - max_csv_items
            sorted_items = sorted_items[:max_csv_items]
            print(f"[SURUGA-YA] Trimmed {removed_count} old items (keeping newest {max_csv_items})")

        # Write merged results to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['first_seen', 'last_seen', 'title', 'title_en', 'price', 'condition', 'stock_status', 'url', 'image_url', 'local_image',
                          'ebay_compared', 'ebay_match_found', 'ebay_best_match_title', 'ebay_similarity', 'ebay_price', 'ebay_profit_margin']
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(sorted_items)

        self.run_queue.put(("status", f"Found {len(merged_items)} items ({new_count} new, {updated_count} updated) - saved to {csv_path.name}"))

        return csv_path

    def _download_images(self, results: List[Dict], config_path: Path, csv_path: Path) -> None:
        """
        Download Suruga-ya images in parallel.

        Args:
            results: List of scraped results
            config_path: Path to config file (used for image directory naming)
            csv_path: Path to CSV file (for updating with image paths)
        """
        images_dir = Path('images') / config_path.stem
        images_dir.mkdir(parents=True, exist_ok=True)

        print(f"[SURUGAYA] Downloading {len(results)} images in parallel...", flush=True)

        # Create session with connection pooling
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=2
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        def download_image(args):
            i, item = args
            image_url = item.get('image_url', '')
            if not image_url:
                return (i, None)

            try:
                response = session.get(image_url, timeout=10)
                if response.status_code == 200:
                    img_filename = f"thumb_product_{i:04d}.jpg"
                    img_path = images_dir / img_filename
                    with open(img_path, 'wb') as img_file:
                        img_file.write(response.content)
                    return (i, str(img_path))
            except Exception as e:
                print(f"[SURUGAYA] Failed to download image {i+1}: {e}", flush=True)
            return (i, None)

        # Helper to write CSV
        def write_csv(sorted_items):
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['first_seen', 'last_seen', 'title', 'title_en', 'price', 'condition', 'stock_status', 'url', 'image_url', 'local_image',
                              'ebay_compared', 'ebay_match_found', 'ebay_best_match_title', 'ebay_similarity', 'ebay_price', 'ebay_profit_margin']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(sorted_items)

        # Read current CSV to get sorted_items
        sorted_items = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sorted_items = list(reader)

        # Download in parallel with 20 workers
        downloaded_count = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(download_image, (i, item)): i for i, item in enumerate(results)}

            for future in as_completed(futures):
                i, img_path = future.result()
                if img_path:
                    # Update the item in sorted_items
                    for item in sorted_items:
                        if item.get('url') == results[i].get('url'):
                            item['local_image'] = img_path
                            break
                    downloaded_count += 1

                    if downloaded_count % 20 == 0:
                        print(f"[SURUGAYA] Downloaded {downloaded_count}/{len(results)} images", flush=True)
                        # Update CSV periodically
                        write_csv(sorted_items)

        session.close()

        # Final CSV write with all images
        write_csv(sorted_items)
        print(f"[SURUGAYA] ✓ Downloaded {downloaded_count}/{len(results)} images", flush=True)
