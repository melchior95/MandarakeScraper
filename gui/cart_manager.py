"""
Cart Manager

Manages Mandarake cart operations with:
- Shop-level cart tracking and thresholds
- ROI verification before checkout
- Integration with alert system
- Smart recommendations
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.mandarake_cart_api import MandarakeCartAPI, MandarakeCartSession
from gui.cart_storage import CartStorage
from gui.cart_roi_verifier import CartROIVerifier
from mandarake_codes import MANDARAKE_STORES


class CartManager:
    """Manages Mandarake cart operations and tracking"""

    def __init__(self, alert_manager=None, ebay_search_manager=None, csv_comparison_manager=None):
        """
        Initialize cart manager

        Args:
            alert_manager: AlertManager instance for fetching alert data
            ebay_search_manager: EbaySearchManager for ROI verification
            csv_comparison_manager: CSVComparisonManager for image comparison
        """
        self.alert_manager = alert_manager
        self.ebay_search_manager = ebay_search_manager
        self.csv_comparison_manager = csv_comparison_manager
        self.storage = CartStorage()
        self.session_manager = MandarakeCartSession()
        self.cart_api: Optional[MandarakeCartAPI] = None
        self.logger = logging.getLogger(__name__)

        # Initialize ROI verifier
        self.roi_verifier = CartROIVerifier(
            ebay_search_manager=ebay_search_manager,
            csv_comparison_manager=csv_comparison_manager
        )

        # Session will be loaded asynchronously (don't block GUI startup)
        # Call load_session_async() from GUI after initialization

        # Cache connection status to avoid blocking verify_session() calls
        self._connection_verified = False
        self._last_verify_time = 0

    def load_session_async(self, callback=None):
        """
        Load saved session in background thread (non-blocking)

        Args:
            callback: Optional callback(success: bool) to call on main thread when done
        """
        import threading
        import time

        def load_in_background():
            self.cart_api = self.session_manager.load_session()
            # Set verified flag if session was loaded successfully
            if self.cart_api:
                self._connection_verified = True
                self._last_verify_time = time.time()
            else:
                self._connection_verified = False

            if callback:
                # Schedule callback on main thread
                import tkinter as tk
                # Use after_idle to ensure we're on main thread
                tk._default_root.after_idle(lambda: callback(self.cart_api is not None))

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def connect_with_url(self, cart_url: str) -> Tuple[bool, str]:
        """
        Connect to Mandarake cart using cart URL

        Args:
            cart_url: Full cart URL with jsessionid

        Returns:
            Tuple of (success, message)
        """
        try:
            self.cart_api = self.session_manager.login_with_url(cart_url)
            return True, "Connected to Mandarake cart successfully"
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False, f"Connection failed: {str(e)}"

    def is_connected(self) -> bool:
        """
        Check if cart API is connected (uses cached status, doesn't verify)

        For actual verification, use verify_connection_async()
        """
        if not self.cart_api:
            return False

        # Return cached status (don't block with network request)
        return self._connection_verified

    def verify_connection_async(self, callback=None):
        """
        Verify cart connection in background (non-blocking)

        Args:
            callback: Optional callback(is_valid: bool) to call when done
        """
        import threading
        import time

        def verify_in_background():
            if not self.cart_api:
                self._connection_verified = False
                if callback:
                    import tkinter as tk
                    tk._default_root.after_idle(lambda: callback(False))
                return

            # Verify session with network request
            is_valid = self.cart_api.verify_session()
            self._connection_verified = is_valid
            self._last_verify_time = time.time()

            if callback:
                import tkinter as tk
                tk._default_root.after_idle(lambda: callback(is_valid))

        thread = threading.Thread(target=verify_in_background, daemon=True)
        thread.start()

    def add_yays_to_cart(self, force_below_threshold: bool = False,
                        progress_callback=None) -> Dict:
        """
        Add all "Yay" alerts to Mandarake cart

        Convenience method that fetches all Yay alerts and adds them to cart.

        Args:
            force_below_threshold: Add even if below minimum threshold
            progress_callback: Optional callback(current, total, message)

        Returns:
            dict: {
                'success': bool,
                'added': [...],
                'failed': [...],
                'warnings': [...]
            }
        """
        if not self.alert_manager:
            return {
                'success': False,
                'error': 'Alert manager not connected',
                'added': [],
                'failed': [],
                'warnings': []
            }

        # Get all Yay alerts
        from gui.alert_states import AlertState
        yay_alerts = self.alert_manager.get_alerts_by_state(AlertState.YAY)
        if not yay_alerts:
            return {
                'success': False,
                'error': 'No Yay alerts found',
                'added': [],
                'failed': [],
                'warnings': []
            }

        yay_ids = [alert['alert_id'] for alert in yay_alerts]
        return self.add_alerts_to_cart(yay_ids, force_below_threshold, progress_callback)

    def add_alerts_to_cart(self, alert_ids: List[int],
                          force_below_threshold: bool = False,
                          progress_callback=None) -> Dict:
        """
        Add alert items to Mandarake cart

        Args:
            alert_ids: Alert IDs to add (usually all "Yay" items)
            force_below_threshold: Add even if thresholds will be violated
            progress_callback: Optional callback(current, total, message)

        Returns:
            dict: {
                'success': bool,
                'added': [...],
                'failed': [...],
                'shop_totals': {...},
                'threshold_warnings': {...}  # Shops that will violate thresholds
            }
        """
        if not self.is_connected():
            return {
                'success': False,
                'error': 'Not connected to Mandarake cart',
                'added': [],
                'failed': [],
                'shop_totals': {},
                'threshold_warnings': {}
            }

        # 1. Get alert data
        alerts = self._fetch_alert_data(alert_ids)
        if not alerts:
            return {
                'success': False,
                'error': 'No alerts found',
                'added': [],
                'failed': [],
                'shop_totals': {},
                'threshold_warnings': {}
            }

        # 2. Group by shop
        by_shop = self._group_by_shop(alerts)

        # 3. Check thresholds (if not forcing)
        if not force_below_threshold:
            threshold_warnings = self._check_add_thresholds(by_shop)
            if threshold_warnings:
                # Return warnings without adding items
                return {
                    'success': False,
                    'error': 'Threshold violations detected',
                    'added': [],
                    'failed': [],
                    'shop_totals': {},
                    'threshold_warnings': threshold_warnings
                }

        # 3. Add items to cart via API
        added = []
        failed = []

        # Count total for progress
        total_items = sum(len(items) for items in by_shop.values())
        current_item = 0

        for shop_code, items in by_shop.items():
            for item in items:
                current_item += 1

                if progress_callback:
                    progress_callback(current_item, total_items, f"Adding: {item['title'][:50]}...")

                try:
                    # Get referer URL from store_link
                    referer = item.get('store_link', 'https://order.mandarake.co.jp/')

                    success = self.cart_api.add_to_cart(
                        product_id=item['product_id'],
                        shop_code=shop_code,
                        referer=referer
                    )

                    if success:
                        added.append(item)
                        # Save to local cart tracking
                        self.storage.add_cart_item(
                            alert_id=item['alert_id'],
                            product_data=item
                        )
                        self.storage.mark_in_cart(item['alert_id'], True)

                        # Update alert state: Yay → Purchased (if alert_manager available)
                        if self.alert_manager:
                            try:
                                from gui.alert_states import AlertState
                                self.alert_manager.update_alert_state(item['alert_id'], AlertState.PURCHASED)
                            except Exception as e:
                                self.logger.warning(f"Could not update alert state: {e}")
                    else:
                        failed.append({**item, 'error': 'API request failed'})

                except Exception as e:
                    self.logger.error(f"Error adding {item['title']}: {e}")
                    failed.append({**item, 'error': str(e)})

        # Calculate shop totals from added items
        shop_totals = {}
        for shop_code, items in by_shop.items():
            added_in_shop = [item for item in added if item.get('shop_code') == shop_code]
            if added_in_shop:
                total = sum(item['price_jpy'] for item in added_in_shop)
                shop_totals[shop_code] = {
                    'items': len(added_in_shop),
                    'total_jpy': total
                }

        return {
            'success': True,
            'added': added,
            'failed': failed,
            'shop_totals': shop_totals
        }

    def verify_cart_roi(self, method: str = 'hybrid',
                       exchange_rate: float = None,
                       min_similarity: float = 70.0,
                       use_ransac: bool = False,
                       progress_callback=None) -> Dict:
        """
        Verify cart ROI using eBay comparison

        Args:
            method: 'text', 'image', or 'hybrid' (default: 'hybrid')
            exchange_rate: USD/JPY rate (auto-fetched if not provided)
            min_similarity: Minimum similarity % for image matching (default: 70%)
            use_ransac: Enable RANSAC verification for image matching
            progress_callback: Optional callback(current, total, message)

        Returns:
            dict: {
                'total_cost_jpy': int,
                'total_cost_usd': float,
                'est_revenue_usd': float,
                'profit_usd': float,
                'roi_percent': float,
                'exchange_rate': float,
                'items_verified': int,
                'items_flagged': int,
                'verified_items': [...],
                'flagged_items': [...],
                'method': str
            }
        """
        # Get cart items from storage or live cart
        cart_items = self._get_all_cart_items()

        if not cart_items:
            return {
                'error': 'No items in cart',
                'total_cost_jpy': 0,
                'total_cost_usd': 0,
                'est_revenue_usd': 0,
                'profit_usd': 0,
                'roi_percent': 0,
                'items_verified': 0,
                'items_flagged': 0,
                'verified_items': [],
                'flagged_items': []
            }

        # Use ROI verifier based on method
        if method == 'text':
            result = self.roi_verifier.verify_cart_text_based(
                cart_items,
                exchange_rate=exchange_rate,
                progress_callback=progress_callback
            )
        elif method == 'image':
            result = self.roi_verifier.verify_cart_image_based(
                cart_items,
                exchange_rate=exchange_rate,
                min_similarity=min_similarity,
                use_ransac=use_ransac,
                progress_callback=progress_callback
            )
        else:  # hybrid
            result = self.roi_verifier.verify_cart_hybrid(
                cart_items,
                exchange_rate=exchange_rate,
                min_similarity=min_similarity,
                use_ransac=use_ransac,
                progress_callback=progress_callback
            )

        # Save verification to storage
        if 'error' not in result:
            self.storage.save_verification(result)

        return result

    def _check_add_thresholds(self, items_to_add: Dict[str, List[Dict]]) -> Dict:
        """
        Check if adding items will violate thresholds

        Args:
            items_to_add: Dict of {shop_code: [items]} to be added

        Returns:
            dict: {
                'shop_code': {
                    'violation_type': 'below_min' | 'over_max' | 'too_many_items',
                    'current_total': int,
                    'items_to_add': int,
                    'value_to_add': int,
                    'new_total': int,
                    'threshold': int,
                    'shop_name': str
                }
            }
            Empty dict if no violations
        """
        warnings = {}

        # Get current cart state
        try:
            current_cart = self.cart_api.get_cart_items()
            if current_cart is None:
                current_cart = []
        except Exception:
            current_cart = []

        # Calculate current totals per shop
        current_totals = {}
        current_counts = {}
        for item in current_cart:
            shop_code = item.get('shop_code', 'unknown')
            price_str = item.get('price', '¥0')
            price_jpy = int(''.join(c for c in price_str if c.isdigit()))

            current_totals[shop_code] = current_totals.get(shop_code, 0) + price_jpy
            current_counts[shop_code] = current_counts.get(shop_code, 0) + 1

        # Check each shop's items to add
        for shop_code, items in items_to_add.items():
            # Get threshold for this shop
            threshold = self.storage.get_shop_threshold(shop_code)

            if not threshold or not threshold.get('enabled', True):
                continue  # Skip if no threshold or disabled

            min_val = threshold.get('min_cart_value', 0)
            max_val = threshold.get('max_cart_value', float('inf'))
            max_items = threshold.get('max_items', float('inf'))

            # Calculate new totals
            current_total = current_totals.get(shop_code, 0)
            current_count = current_counts.get(shop_code, 0)

            items_to_add_count = len(items)
            value_to_add = sum(item.get('price_jpy', 0) for item in items)

            new_total = current_total + value_to_add
            new_count = current_count + items_to_add_count

            # Get shop name
            from mandarake_codes import MANDARAKE_STORES
            shop_name = MANDARAKE_STORES.get(shop_code, shop_code.title())

            # Check for violations
            violation = None

            if new_total > max_val:
                violation = {
                    'violation_type': 'over_max',
                    'current_total': current_total,
                    'items_to_add': items_to_add_count,
                    'value_to_add': value_to_add,
                    'new_total': new_total,
                    'threshold': max_val,
                    'shop_name': shop_name,
                    'excess': new_total - max_val
                }
            elif new_count > max_items:
                violation = {
                    'violation_type': 'too_many_items',
                    'current_count': current_count,
                    'items_to_add': items_to_add_count,
                    'new_count': new_count,
                    'threshold': max_items,
                    'shop_name': shop_name,
                    'excess': new_count - max_items
                }

            # Note: We don't warn about below minimum when ADDING items
            # Below minimum is only relevant for checkout warnings

            if violation:
                warnings[shop_code] = violation

        return warnings

    def get_shop_breakdown(self) -> Dict[str, Dict]:
        """
        Get current cart breakdown by shop

        Returns:
            dict: {
                'shop_code': {
                    'shop_name': str,
                    'items': int,
                    'total_jpy': int,
                    'status': 'ready|below|over',
                    'threshold': {...}
                }
            }
        """
        cart_items = self.storage.get_cart_items()
        thresholds = self.storage.get_all_thresholds()

        breakdown = {}

        # Get unique shops
        shops = set(item['shop_code'] for item in cart_items if item.get('shop_code'))

        for shop_code in shops:
            shop_items = [i for i in cart_items if i.get('shop_code') == shop_code]
            total = sum(i['price_jpy'] for i in shop_items)
            threshold = thresholds.get(shop_code, self.storage.get_default_threshold())

            # Determine status
            min_val = threshold.get('min_cart_value', 0)
            max_val = threshold.get('max_cart_value', float('inf'))

            if total < min_val:
                status = 'below'
            elif total > max_val:
                status = 'over'
            else:
                status = 'ready'

            shop_name = MANDARAKE_STORES.get(shop_code, {}).get('en', shop_code)

            breakdown[shop_code] = {
                'shop_name': shop_name,
                'items': len(shop_items),
                'total_jpy': total,
                'status': status,
                'threshold': threshold
            }

        return breakdown

    def get_cart_summary(self) -> Dict:
        """
        Get overall cart summary

        Returns:
            dict: {
                'total_items': int,
                'total_value_jpy': int,
                'total_value_usd': float,
                'shop_count': int,
                'ready_shops': int,
                'last_verified': datetime or None
            }
        """
        breakdown = self.get_shop_breakdown()

        total_items = sum(shop['items'] for shop in breakdown.values())
        total_jpy = sum(shop['total_jpy'] for shop in breakdown.values())
        ready_shops = sum(1 for shop in breakdown.values() if shop['status'] == 'ready')

        exchange_rate = self._get_exchange_rate()
        total_usd = total_jpy / exchange_rate

        last_verified = self.storage.get_last_verification_time()

        return {
            'total_items': total_items,
            'total_value_jpy': total_jpy,
            'total_value_usd': round(total_usd, 2),
            'shop_count': len(breakdown),
            'ready_shops': ready_shops,
            'last_verified': last_verified
        }

    def get_recommendations(self) -> List[str]:
        """
        Generate smart recommendations for cart optimization

        Returns:
            List of recommendation strings
        """
        recommendations = []
        breakdown = self.get_shop_breakdown()
        summary = self.get_cart_summary()

        # Check shops below threshold
        below_threshold = [
            shop for shop, data in breakdown.items()
            if data['status'] == 'below'
        ]

        if below_threshold:
            total_below = sum(breakdown[shop]['total_jpy'] for shop in below_threshold)
            recommendations.append(
                f"💡 {len(below_threshold)} shop(s) below minimum threshold "
                f"(¥{total_below:,} total). Consider waiting for more items."
            )

        # Check shops over threshold
        over_threshold = [
            shop for shop, data in breakdown.items()
            if data['status'] == 'over'
        ]

        if over_threshold:
            recommendations.append(
                f"⚠️ {len(over_threshold)} shop(s) exceed maximum threshold. "
                f"Consider splitting orders to avoid oversized shipments."
            )

        # Check verification age
        last_verified = summary.get('last_verified')
        if last_verified:
            age = datetime.now() - last_verified
            if age > timedelta(days=1):
                recommendations.append(
                    f"⏰ Cart not verified in {age.days} day(s). "
                    f"eBay prices may have changed - recommend ROI verification."
                )
        elif summary['total_items'] > 0:
            recommendations.append(
                "🔍 Cart has never been verified. Run ROI verification before checkout."
            )

        # Check if ready to checkout
        if summary['ready_shops'] == summary['shop_count'] and summary['shop_count'] > 0:
            recommendations.append(
                f"✅ All {summary['ready_shops']} shop cart(s) ready for checkout!"
            )

        return recommendations

    def sync_with_mandarake(self) -> Tuple[bool, str]:
        """
        Sync local cart state with actual Mandarake cart

        Returns:
            Tuple of (success, message)
        """
        if not self.is_connected():
            return False, "Not connected to Mandarake"

        try:
            # Fetch actual cart from Mandarake
            actual_cart = self.cart_api.get_cart()

            # Compare with local tracking
            # Mark items as confirmed in cart
            # This is a placeholder for full sync logic

            return True, f"Synced {len(actual_cart)} shop cart(s)"

        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            return False, f"Sync failed: {str(e)}"

    def open_cart_in_browser(self):
        """Open Mandarake cart in default browser"""
        if self.cart_api:
            self.cart_api.open_cart_in_browser()

    # Helper methods

    def _fetch_alert_data(self, alert_ids: List[int]) -> List[Dict]:
        """
        Fetch alert data from alert manager and enrich with product/shop info

        Returns:
            List of alert dicts with added fields:
            - product_id: Extracted from store_link
            - shop_code: Extracted from store_link
            - price_jpy: Parsed from store_price
            - title: From store_title_en or store_title
        """
        if not self.alert_manager:
            return []

        import re

        # Get all alerts at once
        all_alerts = self.alert_manager.get_alerts_by_ids(alert_ids)
        if not all_alerts:
            return []

        enriched_alerts = []
        for alert in all_alerts:
            # Extract product_id from store_link
            # Example: https://order.mandarake.co.jp/order/detailPage/item?itemCode=1234567890
            store_link = alert.get('store_link', '')
            product_id_match = re.search(r'itemCode=(\d+)', store_link)
            if not product_id_match:
                self.logger.warning(f"Could not extract product_id from: {store_link}")
                continue

            product_id = product_id_match.group(1)

            # Parse price from store_price (e.g., "¥3,000" -> 3000)
            store_price = alert.get('store_price', '¥0')
            price_match = re.search(r'[\d,]+', store_price.replace('¥', ''))
            price_jpy = int(price_match.group(0).replace(',', '')) if price_match else 0

            # Use English title if available
            title = alert.get('store_title_en') or alert.get('store_title', 'Unknown')

            # Shop code is not in URL, but we can derive from store name if needed
            # For now, use a placeholder since add_to_cart doesn't require it
            shop_code = 'webshop'  # All items are webshop

            enriched_alert = {
                **alert,
                'alert_id': alert.get('alert_id'),
                'product_id': product_id,
                'shop_code': shop_code,
                'price_jpy': price_jpy,
                'title': title
            }
            enriched_alerts.append(enriched_alert)

        return enriched_alerts

    def _group_by_shop(self, alerts: List[Dict]) -> Dict[str, List[Dict]]:
        """Group alerts by shop code"""
        by_shop = {}
        for alert in alerts:
            shop_code = alert.get('shop_code', 'unknown')
            if shop_code not in by_shop:
                by_shop[shop_code] = []
            by_shop[shop_code].append(alert)
        return by_shop

    def _get_all_cart_items(self) -> List[Dict]:
        """Get all cart items (from storage or live cart)"""
        # Try to get from live cart first if connected
        if self.is_connected():
            try:
                live_cart = self.cart_api.get_cart()
                # Flatten shop-grouped cart into single list
                all_items = []
                for shop, items in live_cart.items():
                    all_items.extend(items)
                return all_items
            except Exception as e:
                self.logger.error(f"Failed to fetch live cart: {e}")

        # Fall back to storage
        return self.storage.get_cart_items()

    def _calculate_roi(self, price_jpy: int, ebay_price_usd: float,
                      exchange_rate: float) -> float:
        """
        Calculate ROI percentage

        Args:
            price_jpy: Mandarake price in JPY
            ebay_price_usd: eBay average price in USD
            exchange_rate: USD/JPY rate

        Returns:
            ROI as percentage
        """
        cost_usd = price_jpy / exchange_rate
        if cost_usd == 0:
            return 0
        profit = ebay_price_usd - cost_usd
        roi = (profit / cost_usd) * 100
        return round(roi, 2)

    def _get_exchange_rate(self) -> float:
        """
        Get current USD/JPY exchange rate

        Returns:
            Exchange rate (defaults to 150 if fetch fails)
        """
        try:
            # Try to fetch from utils or API
            from gui.utils import get_exchange_rate
            return get_exchange_rate()
        except Exception:
            self.logger.warning("Failed to fetch exchange rate, using default 150")
            return 150.0

    # ==================== Auto-Purchase Methods ====================

    def add_item_to_cart(self, url: str, shop_code: str = None) -> Dict:
        """
        Add single item to cart by URL (for auto-purchase).

        Args:
            url: Item URL
            shop_code: Shop code (optional, not used by API)

        Returns:
            {'success': bool, 'error': str}
        """
        if not self.cart_api:
            return {'success': False, 'error': 'Not connected to cart'}

        try:
            # Extract item code from URL
            import re
            match = re.search(r'itemCode=(\d+)', url)
            if not match:
                return {'success': False, 'error': 'Could not extract item code from URL'}

            item_code = match.group(1)

            # Add to cart using API
            success = self.cart_api.add_to_cart(
                product_id=item_code,
                shop_code=shop_code,
                quantity=1,
                referer=url
            )

            if success:
                self.logger.info(f"[AUTO-PURCHASE] Added item {item_code} to cart")
                return {'success': True}
            else:
                return {'success': False, 'error': 'API returned failure'}

        except Exception as e:
            self.logger.error(f"[AUTO-PURCHASE] Error adding to cart: {e}")
            return {'success': False, 'error': str(e)}

    def execute_checkout(self, use_auto_checkout: bool = None) -> Dict:
        """
        Execute full checkout process.

        Args:
            use_auto_checkout: Override auto-checkout setting (None = use stored setting)

        Returns:
            {
                'success': bool,
                'order_id': str,
                'total_jpy': int,
                'error': str,
                'message': str
            }
        """
        if not self.cart_api:
            return {'success': False, 'error': 'Not connected to cart'}

        try:
            from gui.checkout_settings_storage import CheckoutSettingsStorage

            # Get cart summary
            summary = self.cart_api.get_cart_summary()

            if not summary or summary.get('total_items', 0) == 0:
                return {'success': False, 'error': 'Cart is empty'}

            total_jpy = summary.get('total_value_jpy', 0)

            # Load checkout settings
            checkout_storage = CheckoutSettingsStorage()
            settings = checkout_storage.load_settings()

            # Determine if auto-checkout should be used
            if use_auto_checkout is None:
                use_auto_checkout = checkout_storage.is_auto_checkout_enabled()

            # Auto-checkout if enabled and configured
            if use_auto_checkout and settings:
                self.logger.info(f"[AUTO-PURCHASE] Executing automatic checkout - Total: ¥{total_jpy}")

                # Validate spending limits
                limits = settings.get('spending_limits', {})
                max_per_purchase = limits.get('max_per_purchase_jpy', 50000)

                if total_jpy > max_per_purchase:
                    self.logger.warning(f"[AUTO-PURCHASE] Purchase exceeds limit: ¥{total_jpy} > ¥{max_per_purchase}")
                    # Fall back to manual
                    self.cart_api.open_cart_in_browser()
                    return {
                        'success': False,
                        'error': f'Amount ¥{total_jpy:,} exceeds spending limit ¥{max_per_purchase:,}',
                        'message': 'Cart opened for manual review'
                    }

                # Execute automatic checkout
                shipping_info = settings.get('shipping_info', {})
                payment_method = settings.get('payment_method', 'stored')

                result = self.cart_api.execute_checkout(
                    shipping_info=shipping_info,
                    payment_method=payment_method
                )

                if result['success']:
                    self.logger.info(f"[AUTO-PURCHASE] ✓ Checkout completed! Order: {result['order_id']}")

                return result

            else:
                # Manual checkout (open browser)
                self.logger.info(f"[AUTO-PURCHASE] Opening cart for manual checkout - Total: ¥{total_jpy}")
                self.cart_api.open_cart_in_browser()

                return {
                    'success': True,
                    'order_id': 'MANUAL',
                    'total_jpy': total_jpy,
                    'message': 'Cart opened in browser for manual checkout'
                }

        except Exception as e:
            self.logger.error(f"[AUTO-PURCHASE] Checkout error: {e}")
            return {'success': False, 'error': str(e)}
