"""
eBay Listing Creator - Create draft eBay listings from alert data

Creates draft listings using eBay Inventory API when items are marked as "Posted"
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, unquote


class EbayListingCreator:
    """Create eBay draft listings from Mandarake items"""

    # Default listing description template
    DEFAULT_DESCRIPTION = """Pre-owned item in very good condition. No marks or writing. Clean and crisp pages. See pictures for details. Items ship in 2 business days."""

    def __init__(self):
        """Initialize eBay listing creator"""
        self.settings = self._load_settings()
        self.oauth_token = self.settings.get('ebay_listing', {}).get('oauth_token')
        self.use_sandbox = self.settings.get('ebay_listing', {}).get('use_sandbox', False)

        # API endpoints
        if self.use_sandbox:
            self.api_base = "https://api.sandbox.ebay.com"
        else:
            self.api_base = "https://api.ebay.com"

    def _load_settings(self) -> Dict:
        """Load user settings"""
        settings_path = Path(__file__).parent / "user_settings.json"
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def is_configured(self) -> bool:
        """Check if OAuth token is configured"""
        return bool(self.oauth_token)

    def download_mandarake_images(self, image_urls: List[str], alert_id: str) -> List[Path]:
        """
        Download full-size images from Mandarake

        Args:
            image_urls: List of Mandarake image URLs
            alert_id: Alert ID for folder naming

        Returns:
            List of local image paths
        """
        images_dir = Path(__file__).parent / "listing_images" / alert_id
        images_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []

        for i, url in enumerate(image_urls):
            if not url:
                continue

            try:
                # Get full-size image URL (Mandarake uses different URLs for thumbs vs full)
                # Thumbnail: https://img.mandarake.co.jp/webshopimg/02/00/123/0200000123456s.jpg
                # Full-size: https://img.mandarake.co.jp/webshopimg/02/00/123/0200000123456.jpg
                full_url = url.replace('s.jpg', '.jpg').replace('_thumb', '')

                # Download image
                response = requests.get(full_url, timeout=30)
                response.raise_for_status()

                # Determine filename
                parsed_url = urlparse(full_url)
                original_filename = Path(unquote(parsed_url.path)).name

                if original_filename and '.' in original_filename:
                    filename = f"{i:02d}_{original_filename}"
                else:
                    filename = f"{i:02d}_image.jpg"

                image_path = images_dir / filename

                # Save image
                with open(image_path, 'wb') as f:
                    f.write(response.content)

                downloaded.append(image_path)
                print(f"[LISTING IMAGES] Downloaded: {image_path.name}")

            except Exception as e:
                print(f"[LISTING IMAGES] Failed to download {url}: {e}")
                continue

        return downloaded

    def create_draft_listing(self, alert_data: Dict) -> Optional[str]:
        """
        Create eBay draft listing from alert data

        Args:
            alert_data: Alert dictionary with Mandarake and eBay data

        Returns:
            Listing ID if successful, None otherwise
        """
        if not self.is_configured():
            print("[EBAY LISTING] Error: OAuth token not configured")
            print("[EBAY LISTING] Add 'ebay_listing' section to user_settings.json with 'oauth_token'")
            return None

        try:
            # Extract data from alert
            mandarake_title = alert_data.get('mandarake_title_en', alert_data.get('mandarake_title', 'Untitled'))
            ebay_price = alert_data.get('ebay_price', 0)
            mandarake_url = alert_data.get('mandarake_link', '')
            image_urls = alert_data.get('mandarake_images', [])

            # Download images
            alert_id = alert_data.get('id', 'unknown')
            image_paths = self.download_mandarake_images(image_urls, alert_id)

            if not image_paths:
                print(f"[EBAY LISTING] Warning: No images downloaded for {mandarake_title}")

            # Get description template from settings or use default
            description = self.settings.get('ebay_listing', {}).get('description_template', self.DEFAULT_DESCRIPTION)

            # Build listing data (eBay Inventory API format)
            listing_data = {
                "product": {
                    "title": mandarake_title[:80],  # eBay title limit
                    "description": description,
                    "imageUrls": [],  # Would need to upload images to eBay EPS or use external hosting
                    "aspects": {
                        "Condition": ["Used"],
                        "Type": ["Book"]  # Adjust based on category
                    }
                },
                "condition": "USED_EXCELLENT",
                "availability": {
                    "shipToLocationAvailability": {
                        "quantity": 1
                    }
                },
                "merchantLocationKey": "default",  # Needs to be configured
                "pricingSummary": {
                    "price": {
                        "value": str(ebay_price),
                        "currency": "USD"
                    }
                },
                "listingPolicies": {
                    # These need to be configured in eBay seller account
                    "paymentPolicyId": self.settings.get('ebay_listing', {}).get('payment_policy_id'),
                    "returnPolicyId": self.settings.get('ebay_listing', {}).get('return_policy_id'),
                    "fulfillmentPolicyId": self.settings.get('ebay_listing', {}).get('fulfillment_policy_id')
                },
                "categoryId": "267",  # Books > Nonfiction (adjust as needed)
                "format": "FIXED_PRICE"
            }

            # Save listing data locally for review
            listings_dir = Path(__file__).parent / "draft_listings"
            listings_dir.mkdir(exist_ok=True)

            listing_file = listings_dir / f"{alert_id}_listing.json"
            with open(listing_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "alert_id": alert_id,
                    "listing_data": listing_data,
                    "images": [str(p) for p in image_paths],
                    "mandarake_url": mandarake_url
                }, f, indent=2, ensure_ascii=False)

            print(f"[EBAY LISTING] Saved draft listing to: {listing_file}")

            # Create draft via eBay API
            if self._create_inventory_item(alert_id, listing_data):
                print(f"[EBAY LISTING] ✓ Created draft listing for: {mandarake_title}")
                return alert_id
            else:
                print(f"[EBAY LISTING] ✗ Failed to create listing via API")
                print(f"[EBAY LISTING] Manual listing data saved to: {listing_file}")
                return None

        except Exception as e:
            print(f"[EBAY LISTING] Error creating listing: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_inventory_item(self, sku: str, listing_data: Dict) -> bool:
        """
        Create inventory item via eBay Inventory API

        Args:
            sku: Stock keeping unit (using alert_id)
            listing_data: Listing data dictionary

        Returns:
            True if successful
        """
        if not self.oauth_token:
            print("[EBAY API] No OAuth token configured - listing saved locally only")
            return False

        url = f"{self.api_base}/sell/inventory/v1/inventory_item/{sku}"

        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }

        try:
            response = requests.put(url, headers=headers, json=listing_data, timeout=30)

            if response.status_code in [200, 201, 204]:
                print(f"[EBAY API] Created inventory item: {sku}")
                return True
            else:
                print(f"[EBAY API] Failed to create inventory item: {response.status_code}")
                print(f"[EBAY API] Response: {response.text}")
                return False

        except Exception as e:
            print(f"[EBAY API] Request failed: {e}")
            return False

    def get_listing_url(self, alert_id: str) -> Optional[str]:
        """Get eBay listing URL for an alert"""
        # In sandbox: https://www.sandbox.ebay.com/itm/{itemId}
        # In production: https://www.ebay.com/itm/{itemId}
        # Note: Inventory items need to be published to get listing URLs
        base = "https://www.sandbox.ebay.com" if self.use_sandbox else "https://www.ebay.com"
        return f"{base}/sl/prelist"  # Pre-listing page where drafts can be reviewed


# Standalone function for easy import
def create_listing_from_alert(alert_data: Dict) -> Optional[str]:
    """
    Create eBay draft listing from alert data

    Args:
        alert_data: Alert dictionary

    Returns:
        Listing ID if successful
    """
    creator = EbayListingCreator()
    return creator.create_draft_listing(alert_data)


# CLI testing
if __name__ == "__main__":
    # Test with sample data
    sample_alert = {
        "id": "test_123",
        "mandarake_title": "テスト写真集",
        "mandarake_title_en": "Test Photo Book",
        "ebay_price": 29.99,
        "mandarake_link": "https://order.mandarake.co.jp/order/detailPage/item?itemCode=1234567890",
        "mandarake_images": [
            "https://img.mandarake.co.jp/webshopimg/02/00/123/0200000123456s.jpg"
        ]
    }

    creator = EbayListingCreator()

    if not creator.is_configured():
        print("\n" + "="*80)
        print("SETUP REQUIRED: eBay OAuth Token")
        print("="*80)
        print("\nTo create eBay listings, you need to add OAuth token to user_settings.json:")
        print("""
{
  "ebay_listing": {
    "oauth_token": "YOUR_EBAY_OAUTH_TOKEN",
    "use_sandbox": true,
    "description_template": "Pre-owned item in very good condition...",
    "payment_policy_id": "YOUR_PAYMENT_POLICY_ID",
    "return_policy_id": "YOUR_RETURN_POLICY_ID",
    "fulfillment_policy_id": "YOUR_FULFILLMENT_POLICY_ID"
  }
}
        """)
        print("\nFor now, listings will be saved locally to draft_listings/ folder")
        print("="*80 + "\n")

    listing_id = creator.create_draft_listing(sample_alert)

    if listing_id:
        print(f"\n✓ Success! Listing created: {listing_id}")
    else:
        print(f"\n✗ Listing creation failed (check draft_listings/ folder for saved data)")
