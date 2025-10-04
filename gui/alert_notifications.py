"""
Alert notification system for high-value alerts.

Provides desktop notifications when new alerts meet specified criteria.
"""

import logging
from typing import Dict, List, Optional
import platform


class AlertNotifier:
    """Manages desktop notifications for high-value alerts."""

    def __init__(self, enabled: bool = True):
        """
        Initialize alert notifier.

        Args:
            enabled: Whether notifications are enabled
        """
        self.enabled = enabled
        self.notifier = None
        self._init_notifier()

    def _init_notifier(self):
        """Initialize the appropriate notification backend for the platform."""
        if not self.enabled:
            return

        try:
            # Try plyer for cross-platform notifications
            from plyer import notification
            self.notifier = notification
            logging.info("Alert notifications initialized (plyer)")
        except ImportError:
            # Fall back to platform-specific implementations
            system = platform.system()

            if system == "Windows":
                try:
                    from win10toast import ToastNotifier
                    self.notifier = ToastNotifier()
                    logging.info("Alert notifications initialized (win10toast)")
                except ImportError:
                    logging.warning("No notification library available. Install 'plyer' or 'win10toast'")
                    self.enabled = False
            elif system == "Darwin":  # macOS
                # macOS can use osascript
                self.notifier = "osascript"
                logging.info("Alert notifications initialized (osascript)")
            elif system == "Linux":
                # Linux can use notify-send
                self.notifier = "notify-send"
                logging.info("Alert notifications initialized (notify-send)")
            else:
                logging.warning(f"Notifications not supported on {system}")
                self.enabled = False

    def notify_new_alert(self, alert: Dict, sound: bool = True):
        """
        Send notification for a new high-value alert.

        Args:
            alert: Alert dictionary
            sound: Whether to play notification sound
        """
        if not self.enabled or not self.notifier:
            return

        try:
            profit = alert.get('profit_margin', 0)
            store_title = alert.get('store_title', 'Unknown Item')
            store_price = alert.get('store_price', '')
            ebay_price = alert.get('ebay_price', '')

            # Truncate title for notification
            if len(store_title) > 50:
                store_title = store_title[:47] + "..."

            title = "🔥 High-Profit Alert!"
            message = (
                f"{store_title}\n"
                f"Profit: {profit:.1f}%\n"
                f"Store: {store_price} → eBay: {ebay_price}"
            )

            self._send_notification(title, message, timeout=10)
            logging.info(f"Sent notification for alert: {store_title[:30]}")

        except Exception as e:
            logging.error(f"Failed to send notification: {e}")

    def notify_batch_alerts(self, count: int, max_profit: float):
        """
        Send notification for multiple new alerts added at once.

        Args:
            count: Number of new alerts
            max_profit: Highest profit margin in batch
        """
        if not self.enabled or not self.notifier:
            return

        try:
            title = f"🔔 {count} New Alert{'s' if count != 1 else ''}!"
            message = (
                f"Added {count} new high-profit alert{'s' if count != 1 else ''}\n"
                f"Max Profit: {max_profit:.1f}%"
            )

            self._send_notification(title, message, timeout=8)
            logging.info(f"Sent batch notification for {count} alerts")

        except Exception as e:
            logging.error(f"Failed to send batch notification: {e}")

    def _send_notification(self, title: str, message: str, timeout: int = 10):
        """
        Send notification using available backend.

        Args:
            title: Notification title
            message: Notification message
            timeout: Notification timeout in seconds
        """
        if not self.notifier:
            return

        try:
            # Plyer notification
            if hasattr(self.notifier, 'notify'):
                self.notifier.notify(
                    title=title,
                    message=message,
                    app_name="Mandarake Scraper",
                    timeout=timeout
                )

            # win10toast
            elif hasattr(self.notifier, 'show_toast'):
                self.notifier.show_toast(
                    title,
                    message,
                    duration=timeout,
                    threaded=True
                )

            # macOS osascript
            elif self.notifier == "osascript":
                import subprocess
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{message}" with title "{title}"'
                ], check=False)

            # Linux notify-send
            elif self.notifier == "notify-send":
                import subprocess
                subprocess.run([
                    'notify-send',
                    '-t', str(timeout * 1000),
                    title,
                    message
                ], check=False)

        except Exception as e:
            logging.error(f"Notification send failed: {e}")


class AlertNotificationFilter:
    """Filters alerts to determine which should trigger notifications."""

    def __init__(self,
                 min_similarity: float = 80.0,
                 min_profit: float = 30.0,
                 enabled: bool = True):
        """
        Initialize notification filter.

        Args:
            min_similarity: Minimum similarity % for notifications
            min_profit: Minimum profit % for notifications
            enabled: Whether notifications are enabled
        """
        self.min_similarity = min_similarity
        self.min_profit = min_profit
        self.enabled = enabled

    def should_notify(self, alert: Dict) -> bool:
        """
        Check if an alert should trigger a notification.

        Args:
            alert: Alert dictionary

        Returns:
            True if notification should be sent
        """
        if not self.enabled:
            return False

        similarity = alert.get('similarity', 0)
        profit = alert.get('profit_margin', 0)

        return similarity >= self.min_similarity and profit >= self.min_profit

    def filter_alerts_for_notification(self, alerts: List[Dict]) -> List[Dict]:
        """
        Filter list of alerts to those meeting notification criteria.

        Args:
            alerts: List of alert dictionaries

        Returns:
            Filtered list of alerts that should trigger notifications
        """
        if not self.enabled:
            return []

        return [alert for alert in alerts if self.should_notify(alert)]
