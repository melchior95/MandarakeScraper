"""
Cart Storage

SQLite-based storage for cart tracking:
- Cart items
- Shop thresholds
- ROI verification history
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class CartStorage:
    """SQLite storage for cart management"""

    def __init__(self, db_path: str = 'cart.db'):
        """
        Initialize cart storage

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Cart items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cart_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER,
                    product_id TEXT,
                    title TEXT,
                    price_jpy INTEGER,
                    shop_code TEXT,
                    shop_name TEXT,
                    image_url TEXT,
                    product_url TEXT,
                    added_to_cart_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_roi REAL,
                    verified_at TIMESTAMP,
                    in_mandarake_cart BOOLEAN DEFAULT 0,
                    removed_at TIMESTAMP
                )
            ''')

            # Shop thresholds table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shop_thresholds (
                    shop_code TEXT PRIMARY KEY,
                    min_cart_value INTEGER DEFAULT 5000,
                    max_cart_value INTEGER DEFAULT 50000,
                    max_items INTEGER DEFAULT 20,
                    enabled BOOLEAN DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Cart verification history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cart_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_items INTEGER,
                    total_value_jpy INTEGER,
                    total_value_usd REAL,
                    total_roi_percent REAL,
                    exchange_rate REAL,
                    items_flagged INTEGER,
                    details TEXT
                )
            ''')

            conn.commit()

            # Initialize default thresholds
            self._init_default_thresholds(cursor)
            conn.commit()

    def _init_default_thresholds(self, cursor):
        """Initialize default thresholds for common shops"""
        default_shops = [
            ('nkn', 'Nakano', 5000, 50000, 20),
            ('shr', 'Shibuya', 5000, 50000, 20),
            ('umeda', 'Umeda', 5000, 50000, 20),
            ('cmp', 'Complex', 5000, 50000, 20),
            ('sah', 'Sahra', 10000, 100000, 30),
            ('gc', 'Grandchaos', 3000, 30000, 15),
        ]

        for shop_code, shop_name, min_val, max_val, max_items in default_shops:
            cursor.execute('''
                INSERT OR IGNORE INTO shop_thresholds
                (shop_code, min_cart_value, max_cart_value, max_items)
                VALUES (?, ?, ?, ?)
            ''', (shop_code, min_val, max_val, max_items))

    def add_cart_item(self, alert_id: int, product_data: Dict):
        """
        Add item to local cart tracking

        Args:
            alert_id: Alert ID from alerts.db
            product_data: Product information dict
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO cart_items
                (alert_id, product_id, title, price_jpy, shop_code, shop_name,
                 image_url, product_url, verified_roi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert_id,
                product_data.get('product_id', ''),
                product_data.get('title', ''),
                product_data.get('price_jpy', 0),
                product_data.get('shop_code', ''),
                product_data.get('shop_name', ''),
                product_data.get('image_url', ''),
                product_data.get('product_url', ''),
                product_data.get('verified_roi')
            ))

            conn.commit()

    def mark_in_cart(self, alert_id: int, in_cart: bool = True):
        """
        Mark item as added to Mandarake cart

        Args:
            alert_id: Alert ID
            in_cart: Whether item is in cart
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE cart_items
                SET in_mandarake_cart = ?
                WHERE alert_id = ? AND removed_at IS NULL
            ''', (in_cart, alert_id))

            conn.commit()

    def remove_cart_item(self, cart_item_id: int):
        """
        Mark item as removed from cart (soft delete)

        Args:
            cart_item_id: Cart item ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE cart_items
                SET removed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (cart_item_id,))

            conn.commit()

    def get_cart_items(self, shop_code: str = None, active_only: bool = True) -> List[Dict]:
        """
        Get cart items, optionally filtered by shop

        Args:
            shop_code: Optional shop code filter
            active_only: Only return items not removed

        Returns:
            List of cart item dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = 'SELECT * FROM cart_items WHERE 1=1'
            params = []

            if active_only:
                query += ' AND removed_at IS NULL'

            if shop_code:
                query += ' AND shop_code = ?'
                params.append(shop_code)

            query += ' ORDER BY added_to_cart_at DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_shop_threshold(self, shop_code: str) -> Dict:
        """
        Get threshold settings for a shop

        Args:
            shop_code: Shop code

        Returns:
            Threshold dict
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM shop_thresholds WHERE shop_code = ?
            ''', (shop_code,))

            row = cursor.fetchone()

            if row:
                return dict(row)
            else:
                # Return default threshold
                return self.get_default_threshold()

    def get_all_thresholds(self) -> Dict[str, Dict]:
        """
        Get all shop thresholds

        Returns:
            Dict of {shop_code: threshold_dict}
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM shop_thresholds')
            rows = cursor.fetchall()

            return {row['shop_code']: dict(row) for row in rows}

    def update_shop_threshold(self, shop_code: str, threshold_data: Dict):
        """
        Update shop threshold settings

        Args:
            shop_code: Shop code
            threshold_data: Dict with min_cart_value, max_cart_value, max_items
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO shop_thresholds
                (shop_code, min_cart_value, max_cart_value, max_items, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                shop_code,
                threshold_data.get('min_cart_value', 5000),
                threshold_data.get('max_cart_value', 50000),
                threshold_data.get('max_items', 20)
            ))

            conn.commit()

    def get_default_threshold(self) -> Dict:
        """Get default threshold for unknown shops"""
        return {
            'shop_code': 'default',
            'min_cart_value': 5000,
            'max_cart_value': 50000,
            'max_items': 20,
            'enabled': True
        }

    def save_verification(self, verification_data: Dict):
        """
        Save ROI verification results

        Args:
            verification_data: Verification result dict
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Save verification record
            cursor.execute('''
                INSERT INTO cart_verifications
                (total_items, total_value_jpy, total_value_usd, total_roi_percent,
                 exchange_rate, items_flagged, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                verification_data.get('items_verified', 0),
                verification_data.get('total_cost_jpy', 0),
                verification_data.get('total_cost_usd', 0),
                verification_data.get('roi_percent', 0),
                verification_data.get('exchange_rate', 150),
                verification_data.get('items_flagged', 0),
                json.dumps(verification_data.get('flagged_items', []))
            ))

            conn.commit()

            # Update verified_roi for cart items
            if 'items' in verification_data:
                for item in verification_data['items']:
                    if 'alert_id' in item:
                        cursor.execute('''
                            UPDATE cart_items
                            SET verified_roi = ?, verified_at = CURRENT_TIMESTAMP
                            WHERE alert_id = ? AND removed_at IS NULL
                        ''', (item.get('current_roi'), item['alert_id']))

                conn.commit()

    def get_last_verification(self) -> Optional[Dict]:
        """
        Get most recent verification record

        Returns:
            Verification dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM cart_verifications
                ORDER BY verified_at DESC
                LIMIT 1
            ''')

            row = cursor.fetchone()

            if row:
                result = dict(row)
                # Parse JSON details
                if result.get('details'):
                    result['flagged_items'] = json.loads(result['details'])
                return result

            return None

    def get_last_verification_time(self) -> Optional[datetime]:
        """
        Get timestamp of last verification

        Returns:
            datetime or None
        """
        verification = self.get_last_verification()
        if verification and verification.get('verified_at'):
            return datetime.fromisoformat(verification['verified_at'])
        return None

    def get_verification_history(self, limit: int = 10) -> List[Dict]:
        """
        Get verification history

        Args:
            limit: Maximum number of records to return

        Returns:
            List of verification dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM cart_verifications
                ORDER BY verified_at DESC
                LIMIT ?
            ''', (limit,))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                if result.get('details'):
                    result['flagged_items'] = json.loads(result['details'])
                results.append(result)

            return results

    def clear_cart(self):
        """Clear all cart items (soft delete)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE cart_items
                SET removed_at = CURRENT_TIMESTAMP
                WHERE removed_at IS NULL
            ''')

            conn.commit()

    def get_cart_stats(self) -> Dict:
        """
        Get overall cart statistics

        Returns:
            Stats dict
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT
                    COUNT(*) as total_items,
                    SUM(price_jpy) as total_value,
                    COUNT(DISTINCT shop_code) as shop_count,
                    SUM(CASE WHEN in_mandarake_cart THEN 1 ELSE 0 END) as confirmed_items
                FROM cart_items
                WHERE removed_at IS NULL
            ''')

            row = cursor.fetchone()

            return {
                'total_items': row[0] or 0,
                'total_value_jpy': row[1] or 0,
                'shop_count': row[2] or 0,
                'confirmed_in_cart': row[3] or 0
            }
