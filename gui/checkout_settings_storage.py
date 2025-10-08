"""
Checkout settings storage for auto-purchase.

Stores shipping info and payment preferences securely.
"""

import json
from pathlib import Path
from typing import Optional, Dict


class CheckoutSettingsStorage:
    """Manages checkout settings persistence."""

    def __init__(self, storage_path: str = "checkout_settings.json"):
        """
        Initialize storage.

        Args:
            storage_path: Path to settings file
        """
        self.storage_path = Path(storage_path)

    def save_settings(self, shipping_info: Dict, payment_method: str = 'stored',
                     auto_checkout_enabled: bool = False, spending_limits: Dict = None):
        """
        Save checkout settings.

        Args:
            shipping_info: Shipping details
            payment_method: Payment method
            auto_checkout_enabled: Enable automatic checkout
            spending_limits: Spending limit settings
        """
        settings = {
            'shipping_info': shipping_info,
            'payment_method': payment_method,
            'auto_checkout_enabled': auto_checkout_enabled,
            'spending_limits': spending_limits or {
                'max_daily_jpy': 100000,
                'max_per_purchase_jpy': 50000,
                'max_purchases_per_hour': 3
            }
        }

        self.storage_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def load_settings(self) -> Optional[Dict]:
        """
        Load checkout settings.

        Returns:
            Settings dictionary or None
        """
        if not self.storage_path.exists():
            return None

        try:
            return json.loads(self.storage_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Error loading checkout settings: {e}")
            return None

    def is_configured(self) -> bool:
        """Check if checkout settings are configured."""
        settings = self.load_settings()
        if not settings:
            return False

        shipping = settings.get('shipping_info', {})
        required_fields = ['name', 'postal_code', 'address', 'phone', 'email']
        return all(shipping.get(field) for field in required_fields)

    def is_auto_checkout_enabled(self) -> bool:
        """Check if automatic checkout is enabled."""
        settings = self.load_settings()
        return settings.get('auto_checkout_enabled', False) if settings else False

    def clear_settings(self):
        """Clear all checkout settings."""
        if self.storage_path.exists():
            self.storage_path.unlink()
