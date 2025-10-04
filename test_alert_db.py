"""
Quick test for SQLite-based alert storage.

Tests basic CRUD operations and migration from JSON.
"""

import json
from pathlib import Path
from gui.alert_storage_db import AlertStorageDB
from gui.alert_states import AlertState


def test_basic_operations():
    """Test basic database operations."""
    print("=" * 60)
    print("Testing basic SQLite alert storage operations...")
    print("=" * 60)

    # Use test database (clean up first)
    db_path = "test_alerts.db"
    Path(db_path).unlink(missing_ok=True)
    storage = AlertStorageDB(db_path)

    # Test 1: Add alert
    print("\n1. Testing add_alert()...")
    alert_data = {
        'ebay_title': 'Test eBay Item',
        'store_title': 'Test Store Item',
        'store_link': 'https://example.com/store',
        'ebay_link': 'https://ebay.com/item',
        'similarity': 85.5,
        'profit_margin': 30.2,
        'store_price': '¥5,000',
        'ebay_price': '$75.00',
        'shipping': '$15.00',
        'sold_date': '2025-10-01',
        'thumbnail': 'https://example.com/image.jpg',
        'store_images': ['image1.jpg', 'image2.jpg']
    }

    added_alert = storage.add_alert(alert_data)
    alert_id = added_alert['alert_id']
    print(f"   [OK] Added alert with ID: {alert_id}")
    print(f"   [OK] State: {added_alert['state']}")
    print(f"   [OK] store_images: {added_alert.get('store_images')}")

    # Test 2: Load alerts
    print("\n2. Testing load_alerts()...")
    alerts = storage.load_alerts()
    print(f"   [OK] Loaded {len(alerts)} alerts")
    assert len(alerts) == 1, "Should have 1 alert"
    assert alerts[0]['alert_id'] == alert_id, "Alert ID should match"
    assert isinstance(alerts[0]['state'], AlertState), "State should be AlertState enum"
    assert isinstance(alerts[0]['store_images'], list), "store_images should be list"

    # Test 3: Get alert by ID
    print("\n3. Testing get_alert_by_id()...")
    alert = storage.get_alert_by_id(alert_id)
    assert alert is not None, "Alert should exist"
    print(f"   [OK] Retrieved alert: {alert['ebay_title']}")

    # Test 4: Update alert
    print("\n4. Testing update_alert()...")
    storage.update_alert(alert_id, {'profit_margin': 45.0})
    updated_alert = storage.get_alert_by_id(alert_id)
    assert updated_alert['profit_margin'] == 45.0, "Profit margin should be updated"
    print(f"   [OK] Updated profit margin to {updated_alert['profit_margin']}%")

    # Test 5: Update alert state
    print("\n5. Testing update_alert_state()...")
    storage.update_alert_state(alert_id, AlertState.YAY)
    updated_alert = storage.get_alert_by_id(alert_id)
    assert updated_alert['state'] == AlertState.YAY, "State should be YAY"
    print(f"   [OK] Updated state to {updated_alert['state']}")

    # Test 6: Filter alerts
    print("\n6. Testing filter_alerts()...")
    yay_alerts = storage.filter_alerts(state=AlertState.YAY)
    assert len(yay_alerts) == 1, "Should have 1 YAY alert"
    print(f"   [OK] Filtered {len(yay_alerts)} YAY alerts")

    high_profit_alerts = storage.filter_alerts(min_profit=40.0)
    assert len(high_profit_alerts) == 1, "Should have 1 high profit alert"
    print(f"   [OK] Filtered {len(high_profit_alerts)} alerts with profit >= 40%")

    # Test 7: Get stats
    print("\n7. Testing get_stats()...")
    stats = storage.get_stats()
    print(f"   [OK] Stats: {stats}")

    # Test 8: Delete alert
    print("\n8. Testing delete_alerts()...")
    storage.delete_alerts([alert_id])
    remaining_alerts = storage.load_alerts()
    assert len(remaining_alerts) == 0, "Should have 0 alerts after deletion"
    print(f"   [OK] Deleted alert {alert_id}")

    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    print("\n" + "=" * 60)
    print("[PASS] All basic tests passed!")
    print("=" * 60)


def test_json_migration():
    """Test migration from JSON to SQLite."""
    print("\n" + "=" * 60)
    print("Testing JSON to SQLite migration...")
    print("=" * 60)

    # Create test JSON file (clean up first)
    json_path = Path("test_alerts.json")
    db_path = Path("test_alerts_migrated.db")
    json_path.unlink(missing_ok=True)
    db_path.unlink(missing_ok=True)

    test_alerts = [
        {
            'alert_id': 1,
            'state': 'pending',
            'ebay_title': 'JSON Alert 1',
            'store_title': 'Store Item 1',
            'similarity': 75.0,
            'profit_margin': 25.0,
            'store_link': 'https://example.com/1',
            'ebay_link': 'https://ebay.com/1',
            'store_price': '¥3,000',
            'ebay_price': '$50.00',
            'shipping': '$10.00',
            'sold_date': '2025-10-01',
            'thumbnail': 'https://example.com/1.jpg',
            'created_at': '2025-10-01T10:00:00',
            'updated_at': '2025-10-01T10:00:00'
        },
        {
            'alert_id': 2,
            'state': 'yay',
            'ebay_title': 'JSON Alert 2',
            'store_title': 'Store Item 2',
            'similarity': 90.0,
            'profit_margin': 40.0,
            'store_link': 'https://example.com/2',
            'ebay_link': 'https://ebay.com/2',
            'store_price': '¥5,000',
            'ebay_price': '$80.00',
            'shipping': '$15.00',
            'sold_date': '2025-10-02',
            'thumbnail': 'https://example.com/2.jpg',
            'created_at': '2025-10-02T10:00:00',
            'updated_at': '2025-10-02T10:00:00'
        }
    ]

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(test_alerts, f, indent=2)

    print(f"\n[OK] Created test JSON with {len(test_alerts)} alerts")

    # Initialize database (should trigger migration)
    storage = AlertStorageDB(str(db_path), str(json_path))

    # Verify migration
    alerts = storage.load_alerts()
    print(f"[OK] Migrated {len(alerts)} alerts to SQLite")

    assert len(alerts) == 2, "Should have 2 migrated alerts"
    assert alerts[0]['ebay_title'] == 'JSON Alert 2', "Should be ordered by created_at DESC"
    assert isinstance(alerts[0]['state'], AlertState), "State should be AlertState enum"

    # Verify JSON was backed up
    backup_path = json_path.with_suffix('.json.backup')
    assert backup_path.exists(), "JSON backup should exist"
    print(f"[OK] JSON backed up to {backup_path}")

    # Cleanup
    db_path.unlink(missing_ok=True)
    backup_path.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("[PASS] Migration test passed!")
    print("=" * 60)


if __name__ == '__main__':
    test_basic_operations()
    test_json_migration()

    print("\n" + "=" * 60)
    print("[SUCCESS] All SQLite alert storage tests passed!")
    print("=" * 60)
