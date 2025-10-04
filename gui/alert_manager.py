"""
Alert manager - core logic for managing alerts.

Handles filtering comparison results and managing alert lifecycle.
"""

import logging
from typing import Dict, List, Optional

from gui.alert_states import AlertState, AlertStateTransition
from gui.alert_storage import AlertStorage


class AlertManager:
    """Manages alert items from eBay comparison results."""

    def __init__(self, storage_path: str = "alerts.json"):
        """
        Initialize alert manager.

        Args:
            storage_path: Path to alerts storage file
        """
        self.storage = AlertStorage(storage_path)

    def create_alert_from_comparison(self, comparison_result: Dict) -> Dict:
        """
        Create an alert from a comparison result.

        Args:
            comparison_result: Dictionary from eBay comparison with keys:
                - ebay_title
                - store_title (or mandarake_title or csv_title)
                - store_link (or mandarake_link)
                - ebay_link
                - similarity
                - profit_margin
                - store_price (or mandarake_price)
                - ebay_price
                - shipping
                - sold_date
                - thumbnail
                - store_title_en (or mandarake_title_en, optional)
                - store_images (or mandarake_images, optional)
                - store_thumbnail (or mandarake_thumbnail, optional)

        Returns:
            Created alert dictionary with alert_id
        """
        # Extract store title from any field name (prefer generic, fallback to legacy)
        store_title = (comparison_result.get('store_title') or
                      comparison_result.get('mandarake_title') or
                      comparison_result.get('csv_title', 'N/A'))
        store_title_en = (comparison_result.get('store_title_en') or
                         comparison_result.get('mandarake_title_en', store_title))

        # Extract store link (prefer generic, fallback to legacy)
        store_link = (comparison_result.get('store_link') or
                     comparison_result.get('mandarake_link', ''))

        # Extract store price (prefer generic, fallback to legacy)
        store_price = (comparison_result.get('store_price') or
                      comparison_result.get('mandarake_price', '¥0'))

        # Extract store images/thumbnail (prefer generic, fallback to legacy)
        store_thumbnail = (comparison_result.get('store_thumbnail') or
                          comparison_result.get('mandarake_thumbnail', ''))
        store_images = (comparison_result.get('store_images') or
                       comparison_result.get('mandarake_images', []))

        alert_data = {
            'state': AlertState.PENDING,
            'ebay_title': comparison_result.get('ebay_title', 'N/A'),
            'mandarake_title': store_title,  # Keep legacy field name for backwards compatibility
            'mandarake_title_en': store_title_en,
            'mandarake_link': store_link,
            'ebay_link': comparison_result.get('ebay_link', ''),
            'similarity': comparison_result.get('similarity', 0),
            'profit_margin': comparison_result.get('profit_margin', 0),
            'mandarake_price': store_price,
            'ebay_price': comparison_result.get('ebay_price', '$0'),
            'shipping': comparison_result.get('shipping', '$0'),
            'sold_date': comparison_result.get('sold_date', ''),
            'thumbnail': comparison_result.get('thumbnail', ''),
            'mandarake_thumbnail': store_thumbnail,
            'mandarake_images': store_images
        }

        return self.storage.add_alert(alert_data)

    def should_create_alert(self, comparison_result: Dict,
                           min_similarity: float = 0.0,
                           min_profit: float = 0.0) -> bool:
        """
        Check if comparison result meets threshold for creating an alert.

        Args:
            comparison_result: Comparison result dictionary
            min_similarity: Minimum similarity percentage (0-100)
            min_profit: Minimum profit margin percentage

        Returns:
            True if result meets thresholds
        """
        similarity = comparison_result.get('similarity', 0)
        profit = comparison_result.get('profit_margin', 0)

        return similarity >= min_similarity and profit >= min_profit

    def process_comparison_results(self, comparison_results: List[Dict],
                                   min_similarity: float = 70.0,
                                   min_profit: float = 20.0) -> List[Dict]:
        """
        Process comparison results and create alerts for items meeting thresholds.

        Args:
            comparison_results: List of comparison result dictionaries
            min_similarity: Minimum similarity % to create alert (default 70%)
            min_profit: Minimum profit margin % to create alert (default 20%)

        Returns:
            List of created alerts
        """
        created_alerts = []

        for result in comparison_results:
            if self.should_create_alert(result, min_similarity, min_profit):
                try:
                    alert = self.create_alert_from_comparison(result)
                    created_alerts.append(alert)
                except Exception as e:
                    logging.error(f"Failed to create alert: {e}")

        logging.info(f"Created {len(created_alerts)} alerts from {len(comparison_results)} comparison results")
        return created_alerts

    def get_all_alerts(self) -> List[Dict]:
        """Get all alerts from storage."""
        return self.storage.load_alerts()

    def get_alerts_by_state(self, state: AlertState) -> List[Dict]:
        """Get alerts filtered by state."""
        return self.storage.filter_alerts(state=state)

    def get_pending_alerts(self) -> List[Dict]:
        """Get all pending alerts awaiting review."""
        return self.get_alerts_by_state(AlertState.PENDING)

    def get_yay_alerts(self) -> List[Dict]:
        """Get all 'yay' alerts (approved for purchase)."""
        return self.get_alerts_by_state(AlertState.YAY)

    def update_alert_state(self, alert_id: int, new_state: AlertState) -> bool:
        """
        Update alert state with validation.

        Args:
            alert_id: Alert ID
            new_state: New state

        Returns:
            True if update succeeded
        """
        alert = self.storage.get_alert_by_id(alert_id)
        if not alert:
            logging.error(f"Alert {alert_id} not found")
            return False

        current_state = alert.get('state', AlertState.PENDING)

        # Validate transition
        if not AlertStateTransition.can_transition(current_state, new_state):
            logging.warning(f"Invalid state transition: {current_state.value} -> {new_state.value}")
            # Allow it anyway for manual overrides
            pass

        self.storage.update_alert_state(alert_id, new_state)
        logging.info(f"Alert {alert_id} state updated: {current_state.value} -> {new_state.value}")
        return True

    def bulk_update_state(self, alert_ids: List[int], new_state: AlertState) -> int:
        """
        Update multiple alerts to new state.

        Args:
            alert_ids: List of alert IDs
            new_state: New state for all alerts

        Returns:
            Number of alerts successfully updated
        """
        success_count = 0
        for alert_id in alert_ids:
            if self.update_alert_state(alert_id, new_state):
                success_count += 1

        return success_count

    def delete_alerts(self, alert_ids: List[int]):
        """Delete multiple alerts."""
        self.storage.delete_alerts(alert_ids)

    def mark_yay(self, alert_ids: List[int]) -> int:
        """Mark alerts as 'yay' (approved)."""
        return self.bulk_update_state(alert_ids, AlertState.YAY)

    def mark_nay(self, alert_ids: List[int]) -> int:
        """Mark alerts as 'nay' (rejected)."""
        return self.bulk_update_state(alert_ids, AlertState.NAY)

    def mark_purchased(self, alert_ids: List[int]) -> int:
        """Mark alerts as purchased."""
        return self.bulk_update_state(alert_ids, AlertState.PURCHASED)

    def mark_shipped(self, alert_ids: List[int]) -> int:
        """Mark alerts as shipped."""
        return self.bulk_update_state(alert_ids, AlertState.SHIPPED)

    def mark_received(self, alert_ids: List[int]) -> int:
        """Mark alerts as received."""
        return self.bulk_update_state(alert_ids, AlertState.RECEIVED)

    def mark_posted(self, alert_ids: List[int]) -> int:
        """Mark alerts as posted to eBay."""
        return self.bulk_update_state(alert_ids, AlertState.POSTED)

    def mark_sold(self, alert_ids: List[int]) -> int:
        """Mark alerts as sold."""
        return self.bulk_update_state(alert_ids, AlertState.SOLD)

    def get_alerts_by_ids(self, alert_ids: List[int]) -> List[Dict]:
        """
        Get alert data for multiple alert IDs.

        Args:
            alert_ids: List of alert IDs

        Returns:
            List of alert dictionaries
        """
        alerts = []
        for alert_id in alert_ids:
            alert = self.storage.get_alert_by_id(alert_id)
            if alert:
                alerts.append(alert)
        return alerts
