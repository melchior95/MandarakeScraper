"""
Alert storage - persists alerts to JSON file.

Handles saving/loading alert items with their states and metadata.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from gui.alert_states import AlertState


class AlertStorage:
    """Manages persistence of alert items to JSON file."""

    def __init__(self, storage_path: str = "alerts.json"):
        """
        Initialize alert storage.

        Args:
            storage_path: Path to JSON file for storing alerts
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Create storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_raw([])

    def _save_raw(self, data: List[Dict]):
        """Save raw data to JSON file."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save alerts: {e}")

    def _load_raw(self) -> List[Dict]:
        """Load raw data from JSON file."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load alerts: {e}")
        return []

    def save_alerts(self, alerts: List[Dict]):
        """
        Save alerts to storage.

        Args:
            alerts: List of alert dictionaries with keys:
                - alert_id: Unique identifier
                - state: Current AlertState
                - ebay_title: eBay listing title
                - store_title: Store listing title
                - store_link: URL to store listing
                - ebay_link: URL to eBay listing
                - similarity: Similarity percentage
                - profit_margin: Profit margin percentage
                - store_price: Store price
                - ebay_price: eBay price
                - shipping: Shipping cost
                - sold_date: eBay sold date
                - thumbnail: Image URL
                - created_at: Timestamp when alert was created
                - updated_at: Timestamp when alert was last updated
        """
        # Convert AlertState enums to strings for JSON serialization
        serializable_alerts = []
        for alert in alerts:
            alert_copy = alert.copy()
            if isinstance(alert_copy.get('state'), AlertState):
                alert_copy['state'] = alert_copy['state'].value
            serializable_alerts.append(alert_copy)

        self._save_raw(serializable_alerts)
        logging.info(f"Saved {len(alerts)} alerts to {self.storage_path}")

    def load_alerts(self) -> List[Dict]:
        """
        Load alerts from storage.

        Returns:
            List of alert dictionaries with AlertState enums restored
        """
        raw_alerts = self._load_raw()

        # Convert state strings back to AlertState enums
        alerts = []
        for alert in raw_alerts:
            alert_copy = alert.copy()
            state_str = alert_copy.get('state', 'pending')
            try:
                alert_copy['state'] = AlertState(state_str)
            except ValueError:
                alert_copy['state'] = AlertState.PENDING
            alerts.append(alert_copy)

        logging.info(f"Loaded {len(alerts)} alerts from {self.storage_path}")
        return alerts

    def add_alert(self, alert_data: Dict) -> Dict:
        """
        Add a new alert to storage.

        Args:
            alert_data: Alert dictionary (without alert_id, will be generated)

        Returns:
            Complete alert dictionary with generated alert_id
        """
        alerts = self.load_alerts()

        # Generate unique ID
        existing_ids = {a.get('alert_id') for a in alerts}
        alert_id = 1
        while alert_id in existing_ids:
            alert_id += 1

        # Add metadata
        now = datetime.now().isoformat()
        alert_data['alert_id'] = alert_id
        alert_data['created_at'] = now
        alert_data['updated_at'] = now

        # Set default state if not provided
        if 'state' not in alert_data:
            alert_data['state'] = AlertState.PENDING

        alerts.append(alert_data)
        self.save_alerts(alerts)

        return alert_data

    def update_alert(self, alert_id: int, updates: Dict):
        """
        Update an existing alert.

        Args:
            alert_id: ID of alert to update
            updates: Dictionary of fields to update
        """
        alerts = self.load_alerts()

        for alert in alerts:
            if alert.get('alert_id') == alert_id:
                alert.update(updates)
                alert['updated_at'] = datetime.now().isoformat()
                break

        self.save_alerts(alerts)

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
        alerts = self.load_alerts()
        alerts = [a for a in alerts if a.get('alert_id') not in alert_ids]
        self.save_alerts(alerts)
        logging.info(f"Deleted {len(alert_ids)} alerts")

    def get_alert_by_id(self, alert_id: int) -> Optional[Dict]:
        """
        Get a single alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert dictionary or None if not found
        """
        alerts = self.load_alerts()
        for alert in alerts:
            if alert.get('alert_id') == alert_id:
                return alert
        return None

    def filter_alerts(self, state: Optional[AlertState] = None,
                     min_similarity: Optional[float] = None,
                     min_profit: Optional[float] = None) -> List[Dict]:
        """
        Filter alerts by criteria.

        Args:
            state: Filter by state (None = all states)
            min_similarity: Minimum similarity percentage
            min_profit: Minimum profit margin percentage

        Returns:
            Filtered list of alerts
        """
        alerts = self.load_alerts()

        if state is not None:
            alerts = [a for a in alerts if a.get('state') == state]

        if min_similarity is not None:
            alerts = [a for a in alerts if a.get('similarity', 0) >= min_similarity]

        if min_profit is not None:
            alerts = [a for a in alerts if a.get('profit_margin', 0) >= min_profit]

        return alerts
