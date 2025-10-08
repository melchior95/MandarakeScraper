"""
Schedule executor - runs scheduled tasks in background.

Monitors active schedules and executes them when due.
"""

import threading
import time
from typing import Optional, Callable
from pathlib import Path

from gui.schedule_manager import ScheduleManager
from gui.schedule_states import Schedule


class ScheduleExecutor:
    """
    Executes scheduled tasks in a background thread.

    This class monitors active schedules and triggers execution
    when they are due to run.
    """

    def __init__(self, gui_config_ref):
        """
        Initialize executor.

        Args:
            gui_config_ref: Reference to main GUI (ScraperGUI instance)
                           for accessing CSV tree, load_config, run_compare_all, etc.
        """
        self.gui = gui_config_ref
        self.manager = ScheduleManager()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.check_interval = 60  # Check every 60 seconds

    def start(self):
        """Start the background scheduler thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[SCHEDULE EXECUTOR] Started")

    def stop(self):
        """Stop the background scheduler thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[SCHEDULE EXECUTOR] Stopped")

    def _run_loop(self):
        """Main loop that checks for due schedules AND auto-purchase items."""
        while self.running:
            try:
                # Check scheduled tasks
                self._check_and_execute()

                # Check auto-purchase items
                self._check_auto_purchase_items()
            except Exception as e:
                print(f"[SCHEDULE EXECUTOR] Error in check loop: {e}")

            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_and_execute(self):
        """Check for due schedules and execute them."""
        due_schedules = self.manager.get_schedules_due_for_execution()

        for schedule in due_schedules:
            print(f"[SCHEDULE EXECUTOR] Executing schedule: {schedule.name} (ID: {schedule.schedule_id})")
            try:
                self._execute_schedule(schedule)
                self.manager.mark_schedule_executed(schedule.schedule_id)
                print(f"[SCHEDULE EXECUTOR] Completed schedule: {schedule.name}")
            except Exception as e:
                print(f"[SCHEDULE EXECUTOR] Error executing schedule {schedule.name}: {e}")

    def _execute_schedule(self, schedule: Schedule):
        """
        Execute a schedule by running all its config files.

        Args:
            schedule: Schedule to execute
        """
        configs_dir = Path("configs")

        for config_filename in schedule.config_files:
            config_path = configs_dir / config_filename

            if not config_path.exists():
                print(f"[SCHEDULE EXECUTOR] Config not found: {config_path}")
                continue

            print(f"[SCHEDULE EXECUTOR] Processing config: {config_filename}")

            # Execute on main thread using after()
            self.gui.after(0, lambda p=config_path: self._run_config_on_main_thread(p, schedule))

    def _run_config_on_main_thread(self, config_path: Path, schedule: Schedule):
        """
        Run a single config on the main GUI thread.

        This method:
        1. Sets CSV filter options from schedule
        2. Loads the config into the GUI
        3. Runs Compare All
        4. Sends results to alerts tab (items meeting thresholds)

        Args:
            config_path: Path to config JSON file
            schedule: Parent schedule (for logging)
        """
        try:
            # Set CSV filter options from schedule
            print(f"[SCHEDULE EXECUTOR] Setting CSV filters from schedule: newly_listed={schedule.csv_newly_listed}, in_stock={schedule.csv_in_stock}, 2nd_kw={schedule.csv_2nd_keyword}")
            self.gui.csv_newly_listed_only.set(schedule.csv_newly_listed)
            self.gui.csv_in_stock_only.set(schedule.csv_in_stock)
            self.gui.csv_add_secondary_keyword.set(schedule.csv_2nd_keyword)

            # Load config into GUI
            print(f"[SCHEDULE EXECUTOR] Loading config: {config_path.name}")
            self.gui._load_config_file(config_path)

            # Wait a moment for config to load
            self.gui.after(500, lambda: self._run_comparison(config_path, schedule))

        except Exception as e:
            print(f"[SCHEDULE EXECUTOR] Error loading config {config_path.name}: {e}")

    def _run_comparison(self, config_path: Path, schedule: Schedule):
        """
        Run comparison after config is loaded.

        Args:
            config_path: Path to config (for logging)
            schedule: Parent schedule (for logging)
        """
        try:
            comparison_method = schedule.comparison_method if hasattr(schedule, 'comparison_method') else "text"
            print(f"[SCHEDULE EXECUTOR] Running {comparison_method} comparison for: {config_path.name}")

            # Get alert tab thresholds
            alert_tab = self.gui.alert_tab
            min_similarity, min_profit = alert_tab.get_threshold_values()

            # Run comparison based on method
            if comparison_method == "image":
                # Run image comparison (batch image search)
                print(f"[SCHEDULE EXECUTOR] Using image comparison method")
                if hasattr(self.gui.ebay_tab, 'csv_comparison_manager'):
                    # Pass silent=True to skip confirmation dialogs
                    self.gui.ebay_tab.csv_comparison_manager._image_compare_all_csv_items(silent=True)
            else:
                # Default to text comparison
                print(f"[SCHEDULE EXECUTOR] Using text comparison method")
                self.gui._run_csv_comparison_async()

            # Wait for comparison to complete, then send to alerts
            # We'll use a callback approach
            self.gui.after(2000, lambda: self._check_comparison_complete(
                config_path, schedule, min_similarity, min_profit
            ))

        except Exception as e:
            print(f"[SCHEDULE EXECUTOR] Error running comparison for {config_path.name}: {e}")

    def _check_comparison_complete(
        self,
        config_path: Path,
        schedule: Schedule,
        min_similarity: float,
        min_profit: float
    ):
        """
        Check if comparison is complete and send results to alerts.

        Args:
            config_path: Path to config (for logging)
            schedule: Parent schedule
            min_similarity: Similarity threshold
            min_profit: Profit threshold
        """
        # Check if comparison results exist
        if not hasattr(self.gui, 'csv_comparison_results') or not self.gui.csv_comparison_results:
            # Not ready yet, check again in 1 second
            self.gui.after(1000, lambda: self._check_comparison_complete(
                config_path, schedule, min_similarity, min_profit
            ))
            return

        try:
            # Send results to alerts tab
            results = self.gui.csv_comparison_results
            print(f"[SCHEDULE EXECUTOR] Sending {len(results)} results to alerts for {config_path.name}")

            # Filter results by thresholds and send to alerts
            filtered_results = []
            for result in results:
                similarity = result.get('similarity', 0)
                profit = result.get('profit_margin', 0)

                if similarity >= min_similarity and profit >= min_profit:
                    filtered_results.append(result)

            if filtered_results:
                self.gui.alert_tab.add_comparison_results_to_alerts(filtered_results)
                print(f"[SCHEDULE EXECUTOR] Added {len(filtered_results)} items to alerts")
            else:
                print(f"[SCHEDULE EXECUTOR] No items met thresholds for {config_path.name}")

        except Exception as e:
            print(f"[SCHEDULE EXECUTOR] Error sending to alerts: {e}")

    def execute_schedule_now(self, schedule_id: int):
        """
        Manually trigger a schedule execution immediately.

        Args:
            schedule_id: ID of schedule to execute
        """
        schedule = self.manager.storage.get_by_id(schedule_id)
        if schedule:
            print(f"[SCHEDULE EXECUTOR] Manual execution of: {schedule.name}")
            self._execute_schedule(schedule)
            self.manager.mark_schedule_executed(schedule_id)

    # ==================== Auto-Purchase Methods ====================

    def _check_auto_purchase_items(self):
        """Check all active auto-purchase schedules."""
        schedules = self.manager.get_all_schedules()

        for schedule in schedules:
            # Skip non-auto-purchase schedules
            if not schedule.auto_purchase_enabled:
                continue

            # Skip if not active
            if not schedule.active:
                continue

            # Skip if not time to check yet
            if not self._is_due_for_check(schedule):
                continue

            print(f"[AUTO-PURCHASE] Checking: {schedule.name}")

            try:
                # Check availability
                result = self._check_item_availability(schedule)

                if result['in_stock']:
                    # Validate price
                    if result['price'] <= schedule.auto_purchase_max_price:
                        print(f"[AUTO-PURCHASE] Item found! Price: ¥{result['price']} (max: ¥{schedule.auto_purchase_max_price})")
                        # Execute purchase
                        self._execute_auto_purchase(schedule, result)
                    else:
                        print(f"[AUTO-PURCHASE] Price too high: ¥{result['price']} > ¥{schedule.auto_purchase_max_price}")

                # Update last check time
                self.manager.update_auto_purchase_check_time(schedule.schedule_id)
            except Exception as e:
                print(f"[AUTO-PURCHASE] Error checking {schedule.name}: {e}")

    def _is_due_for_check(self, schedule) -> bool:
        """
        Check if schedule is due for availability check.

        Uses staggered polling for 30-min checks to avoid bursts of requests.

        Args:
            schedule: Schedule to check

        Returns:
            True if check is due
        """
        from datetime import datetime, timedelta
        import hashlib

        # First check ever
        if not schedule.auto_purchase_last_check:
            return True

        try:
            last_check = datetime.fromisoformat(schedule.auto_purchase_last_check)
            now = datetime.now()
            minutes_since_check = (now - last_check).total_seconds() / 60

            # Get check interval
            interval = schedule.auto_purchase_check_interval

            # For polling method (30 min), add stagger to spread requests
            if schedule.auto_purchase_monitoring_method == 'polling' and interval >= 30:
                # Use schedule ID to create consistent offset (0-29 minutes)
                stagger_offset = int(hashlib.md5(str(schedule.schedule_id).encode()).hexdigest(), 16) % 30

                # Add stagger to interval for this specific schedule
                staggered_interval = interval + stagger_offset / 60.0  # Convert offset to fraction of hour

                # Only check at staggered time
                return minutes_since_check >= staggered_interval

            # For RSS or other methods, use regular interval
            return minutes_since_check >= interval

        except (ValueError, AttributeError):
            # If parsing fails, assume due
            return True

    def _check_item_availability(self, schedule) -> dict:
        """
        Check if item is in stock using keyword search.

        Strategy:
        1. If direct URL: scrape that page
        2. If keyword: search all stores using keyword URL
        3. Parse results for in-stock items
        4. Return first in-stock match

        Args:
            schedule: Schedule with auto-purchase config

        Returns:
            {
                'in_stock': bool,
                'price': int,
                'url': str,
                'shop_code': str,
                'item_code': str
            }
        """
        from bs4 import BeautifulSoup
        from urllib.parse import quote
        from browser_mimic import BrowserMimic

        mimic = BrowserMimic()

        # Determine URL to check
        if schedule.auto_purchase_url and 'itemCode=' in schedule.auto_purchase_url:
            # Direct item URL
            check_url = schedule.auto_purchase_url
            is_search = False
        else:
            # Search keyword across all stores
            keyword = schedule.auto_purchase_keyword or schedule.name
            check_url = f"https://order.mandarake.co.jp/order/listPage/list?keyword={quote(keyword)}&lang=en"
            is_search = True

        print(f"[AUTO-PURCHASE] Checking URL: {check_url}")

        # Fetch page
        response = mimic.get(check_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        if is_search:
            # Parse search results
            result_items = soup.find_all('div', class_='block', attrs={'data-itemidx': True})

            for result in result_items:
                # Skip sold out
                soldout = result.find('div', class_='soldout')
                if soldout:
                    continue

                # Extract details
                item_code = result.get('data-itemidx', '')

                shop_elem = result.find('p', class_='shop')
                shop_name = shop_elem.get_text(strip=True) if shop_elem else 'unknown'

                price_div = result.find('div', class_='price')
                price_text = price_div.get_text(strip=True) if price_div else '0'
                price_jpy = int(''.join(c for c in price_text if c.isdigit()))

                title_div = result.find('div', class_='title')
                title_link = title_div.find('a') if title_div else None
                item_url = f"https://order.mandarake.co.jp{title_link['href']}" if title_link else ''

                # Found in-stock item!
                print(f"[AUTO-PURCHASE] Found in stock: {shop_name} - ¥{price_jpy}")
                return {
                    'in_stock': True,
                    'price': price_jpy,
                    'url': item_url,
                    'shop_code': self._shop_name_to_code(shop_name),
                    'shop_name': shop_name,
                    'item_code': item_code
                }

            return {'in_stock': False}

        else:
            # Direct item page check
            # Check for "Add to Cart" button or "Sold Out" indicator
            soldout = soup.find('div', class_='soldout') or soup.find(string=lambda t: t and 'Sold Out' in t)

            if soldout:
                print(f"[AUTO-PURCHASE] Still sold out")
                return {'in_stock': False}

            # Extract price
            price_elem = soup.find('td', class_='price') or soup.find('div', class_='price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_jpy = int(''.join(c for c in price_text if c.isdigit()))

                print(f"[AUTO-PURCHASE] Found in stock: ¥{price_jpy}")
                return {
                    'in_stock': True,
                    'price': price_jpy,
                    'url': schedule.auto_purchase_url,
                    'shop_code': self._extract_shop_from_url(schedule.auto_purchase_url),
                    'item_code': self._extract_item_code_from_url(schedule.auto_purchase_url)
                }

            return {'in_stock': False}

    def _shop_name_to_code(self, shop_name: str) -> str:
        """Convert shop name to shop code."""
        shop_map = {
            'nakano': 'nkn',
            'shibuya': 'sib',
            'umeda': 'umd',
            'fukuoka': 'fko',
            'kyoto': 'kyo',
            'chibashop': 'chi',
            'grandchaos': 'gc',
            'sahra': 'sah',
            'complex': 'com'
        }
        shop_lower = shop_name.lower()
        for name, code in shop_map.items():
            if name in shop_lower:
                return code
        return 'unknown'

    def _extract_shop_from_url(self, url: str) -> str:
        """Extract shop code from URL."""
        # Simple extraction - can be enhanced
        return 'unknown'

    def _extract_item_code_from_url(self, url: str) -> str:
        """Extract item code from URL."""
        import re
        match = re.search(r'itemCode=(\d+)', url)
        return match.group(1) if match else ''

    def _execute_auto_purchase(self, schedule, item_data: dict):
        """
        Execute automatic purchase notification.

        Steps:
        1. Send desktop notification to user
        2. Add item to alerts page (Pending state)
        3. Mark schedule as notified
        4. Open URL in browser (optional)

        Args:
            schedule: Schedule with auto-purchase config
            item_data: Item details from availability check
        """
        try:
            print(f"[AUTO-PURCHASE] Item in stock: {schedule.name} at ¥{item_data['price']}")

            # 1. Send desktop notification
            self._notify_item_found(schedule, item_data)

            # 2. Add to alerts page
            self._add_to_alerts(schedule, item_data)

            # 3. Mark schedule as notified (don't disable, user might want continuous monitoring)
            self.manager.update_auto_purchase_check_time(schedule.schedule_id)

            print(f"[AUTO-PURCHASE] ✓ Notified user: {schedule.name}")

        except Exception as e:
            print(f"[AUTO-PURCHASE] Error during notification: {e}")
            import traceback
            traceback.print_exc()

    def _notify_item_found(self, schedule, item_data: dict):
        """
        Send desktop notification when item is found.

        Args:
            schedule: Schedule that found the item
            item_data: Item details
        """
        try:
            message = (
                f"IN STOCK: {schedule.name}\n"
                f"Price: ¥{item_data['price']:,}\n"
                f"Shop: {item_data.get('shop_name', 'Unknown')}\n"
                f"URL: {item_data.get('url', 'N/A')[:50]}..."
            )

            print(f"[AUTO-PURCHASE] {message}")

            # Try to show desktop notification
            try:
                from plyer import notification
                notification.notify(
                    title="🔔 Item Back in Stock!",
                    message=message,
                    app_name="Mandarake Auto-Purchase",
                    timeout=15
                )
            except ImportError:
                print(f"[AUTO-PURCHASE] Desktop notification not available (install plyer)")
            except Exception as e:
                print(f"[AUTO-PURCHASE] Notification error: {e}")

        except Exception as e:
            print(f"[AUTO-PURCHASE] Error sending notification: {e}")

    def _add_to_alerts(self, schedule, item_data: dict):
        """
        Add item to alerts page in Pending state.

        Args:
            schedule: Schedule that found the item
            item_data: Item details
        """
        try:
            from gui.alert_storage import AlertStorage

            storage = AlertStorage()

            # Create alert entry
            alert_data = {
                'title': schedule.name,
                'mandarake_price': item_data['price'],
                'mandarake_url': item_data.get('url', ''),
                'mandarake_shop': item_data.get('shop_name', 'Unknown'),
                'mandarake_stock': 'In Stock',
                'state': 'pending',
                'similarity': 100,  # Direct match
                'profit_margin': 0,  # Unknown until eBay comparison
                'source': 'auto_purchase',
                'auto_purchase_schedule_id': schedule.schedule_id
            }

            storage.add_alert(alert_data)
            print(f"[AUTO-PURCHASE] Added to alerts: {schedule.name}")

        except Exception as e:
            print(f"[AUTO-PURCHASE] Error adding to alerts: {e}")

    def _notify_purchase_success(self, schedule, item_data: dict, checkout_result: dict):
        """
        Send desktop notification and log purchase.

        Args:
            schedule: Schedule that triggered purchase
            item_data: Item details
            checkout_result: Checkout result
        """
        try:
            message = (
                f"Auto-purchased: {schedule.name}\n"
                f"Price: ¥{item_data['price']:,}\n"
                f"Shop: {item_data.get('shop_name', 'Unknown')}\n"
                f"Status: {checkout_result.get('message', 'Success')}"
            )

            print(f"[AUTO-PURCHASE] {message}")

            # Try to show desktop notification
            try:
                from plyer import notification
                notification.notify(
                    title="Auto-Purchase Success!",
                    message=message,
                    timeout=10
                )
            except ImportError:
                # plyer not available, just print
                print(f"[AUTO-PURCHASE] Desktop notification not available (install plyer)")
            except Exception as e:
                print(f"[AUTO-PURCHASE] Notification failed: {e}")

        except Exception as e:
            print(f"[AUTO-PURCHASE] Error sending notification: {e}")
