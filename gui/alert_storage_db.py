"""
Alert storage using SQLite database for improved performance.

Provides same API as alert_storage.py but uses SQLite backend instead of JSON.
Includes automatic migration from JSON to SQLite on first use.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from gui.alert_states import AlertState


class AlertStorageDB:
    """Manages persistence of alert items using SQLite database."""

    def __init__(self, db_path: str = "alerts.db", json_path: str = "alerts.json"):
        """
        Initialize alert storage with SQLite backend.

        Args:
            db_path: Path to SQLite database file
            json_path: Path to legacy JSON file (for migration)
        """
        self.db_path = Path(db_path)
        self.json_path = Path(json_path)
        self._init_database()
        self._migrate_from_json_if_needed()

    def _init_database(self):
        """Initialize database schema if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL,
                    ebay_title TEXT,
                    store_title TEXT,
                    store_title_en TEXT,
                    store_link TEXT,
                    ebay_link TEXT,
                    similarity REAL,
                    profit_margin REAL,
                    store_price TEXT,
                    ebay_price TEXT,
                    shipping TEXT,
                    sold_date TEXT,
                    thumbnail TEXT,
                    store_thumbnail TEXT,
                    store_images TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indices for fast filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_state
                ON alerts(state)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_created_at
                ON alerts(created_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_similarity
                ON alerts(similarity)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_profit_margin
                ON alerts(profit_margin)
            """)

            conn.commit()
            logging.info(f"Initialized SQLite database: {self.db_path}")

    def _migrate_from_json_if_needed(self):
        """Migrate data from JSON file to SQLite if JSON exists and DB is empty."""
        # Check if database is empty
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts")
            count = cursor.fetchone()[0]

        # If database is empty and JSON file exists, migrate
        if count == 0 and self.json_path.exists():
            try:
                logging.info(f"Migrating alerts from {self.json_path} to {self.db_path}...")

                with open(self.json_path, 'r', encoding='utf-8') as f:
                    json_alerts = json.load(f)

                # Convert and insert all alerts
                for alert in json_alerts:
                    # Convert AlertState enum to string if needed
                    if isinstance(alert.get('state'), AlertState):
                        alert['state'] = alert['state'].value

                    self._insert_alert_raw(alert)

                logging.info(f"Successfully migrated {len(json_alerts)} alerts to database")

                # Backup JSON file
                backup_path = self.json_path.with_suffix('.json.backup')
                self.json_path.rename(backup_path)
                logging.info(f"Backed up JSON file to {backup_path}")

            except Exception as e:
                logging.error(f"Failed to migrate from JSON: {e}")

    def _insert_alert_raw(self, alert: Dict) -> int:
        """
        Insert alert into database (internal method).

        Args:
            alert: Alert dictionary with all fields

        Returns:
            alert_id of inserted alert
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Serialize store_images list to JSON string
            store_images = alert.get('store_images', [])
            if isinstance(store_images, list):
                store_images_json = json.dumps(store_images)
            else:
                store_images_json = '[]'

            cursor.execute("""
                INSERT INTO alerts (
                    state, ebay_title, store_title, store_title_en,
                    store_link, ebay_link, similarity, profit_margin,
                    store_price, ebay_price, shipping, sold_date,
                    thumbnail, store_thumbnail, store_images,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.get('state', 'pending'),
                alert.get('ebay_title'),
                alert.get('store_title'),
                alert.get('store_title_en'),
                alert.get('store_link'),
                alert.get('ebay_link'),
                alert.get('similarity'),
                alert.get('profit_margin'),
                alert.get('store_price'),
                alert.get('ebay_price'),
                alert.get('shipping'),
                alert.get('sold_date'),
                alert.get('thumbnail'),
                alert.get('store_thumbnail'),
                store_images_json,
                alert.get('created_at', datetime.now().isoformat()),
                alert.get('updated_at', datetime.now().isoformat())
            ))

            conn.commit()
            return cursor.lastrowid

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert database row to alert dictionary."""
        alert = dict(row)

        # Deserialize store_images from JSON string
        if alert.get('store_images'):
            try:
                alert['store_images'] = json.loads(alert['store_images'])
            except (json.JSONDecodeError, TypeError):
                alert['store_images'] = []
        else:
            alert['store_images'] = []

        # Convert state string to AlertState enum
        state_str = alert.get('state', 'pending')
        try:
            alert['state'] = AlertState(state_str)
        except ValueError:
            alert['state'] = AlertState.PENDING

        return alert

    def save_alerts(self, alerts: List[Dict]):
        """
        Save alerts to storage (replaces all existing alerts).

        Args:
            alerts: List of alert dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Clear existing alerts
            cursor.execute("DELETE FROM alerts")

            # Insert all alerts
            for alert in alerts:
                # Convert AlertState enum to string for storage
                state = alert.get('state')
                if isinstance(state, AlertState):
                    alert['state'] = state.value

                self._insert_alert_raw(alert)

            conn.commit()
            logging.info(f"Saved {len(alerts)} alerts to database")

    def load_alerts(self) -> List[Dict]:
        """
        Load all alerts from storage.

        Returns:
            List of alert dictionaries with AlertState enums restored
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC")
            rows = cursor.fetchall()

            alerts = [self._row_to_dict(row) for row in rows]
            logging.info(f"Loaded {len(alerts)} alerts from database")
            return alerts

    def add_alert(self, alert_data: Dict) -> Dict:
        """
        Add a new alert to storage.

        Args:
            alert_data: Alert dictionary (without alert_id, will be generated)

        Returns:
            Complete alert dictionary with generated alert_id
        """
        # Add metadata
        now = datetime.now().isoformat()
        alert_data['created_at'] = now
        alert_data['updated_at'] = now

        # Set default state if not provided
        if 'state' not in alert_data:
            alert_data['state'] = AlertState.PENDING

        # Convert AlertState to string for storage
        if isinstance(alert_data.get('state'), AlertState):
            alert_data['state'] = alert_data['state'].value

        # Insert and get generated ID
        alert_id = self._insert_alert_raw(alert_data)
        alert_data['alert_id'] = alert_id

        return alert_data

    def update_alert(self, alert_id: int, updates: Dict):
        """
        Update an existing alert.

        Args:
            alert_id: ID of alert to update
            updates: Dictionary of fields to update
        """
        # Convert AlertState enum to string if present
        if isinstance(updates.get('state'), AlertState):
            updates['state'] = updates['state'].value

        # Serialize store_images if present
        if 'store_images' in updates and isinstance(updates['store_images'], list):
            updates['store_images'] = json.dumps(updates['store_images'])

        # Add updated timestamp
        updates['updated_at'] = datetime.now().isoformat()

        # Build UPDATE query dynamically
        set_clauses = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [alert_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE alerts SET {set_clauses} WHERE alert_id = ?", values)
            conn.commit()

    def update_alert_state(self, alert_id: int, new_state: AlertState):
        """
        Update the state of an alert.

        Args:
            alert_id: ID of alert to update
            new_state: New AlertState
        """
        self.update_alert(alert_id, {'state': new_state})

    def delete_alerts(self, alert_ids: List[int]):
        """
        Delete alerts by ID.

        Args:
            alert_ids: List of alert IDs to delete
        """
        if not alert_ids:
            return

        placeholders = ','.join(['?'] * len(alert_ids))

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM alerts WHERE alert_id IN ({placeholders})", alert_ids)
            deleted_count = cursor.rowcount
            conn.commit()
            logging.info(f"Deleted {deleted_count} alerts")

    def get_alert_by_id(self, alert_id: int) -> Optional[Dict]:
        """
        Get a single alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert dictionary or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def filter_alerts(self, state: Optional[AlertState] = None,
                     min_similarity: Optional[float] = None,
                     min_profit: Optional[float] = None) -> List[Dict]:
        """
        Filter alerts by criteria using efficient database queries.

        Args:
            state: Filter by state (None = all states)
            min_similarity: Minimum similarity percentage
            min_profit: Minimum profit margin percentage

        Returns:
            Filtered list of alerts
        """
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []

        if state is not None:
            query += " AND state = ?"
            params.append(state.value)

        if min_similarity is not None:
            query += " AND similarity >= ?"
            params.append(min_similarity)

        if min_profit is not None:
            query += " AND profit_margin >= ?"
            params.append(min_profit)

        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about alerts.

        Returns:
            Dictionary with counts by state
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT state, COUNT(*) as count
                FROM alerts
                GROUP BY state
            """)

            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]

            return stats
