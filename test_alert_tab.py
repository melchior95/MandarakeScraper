"""
Quick test script for Alert tab functionality.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from gui.alert_manager import AlertManager
from gui.alert_states import AlertState

def test_alert_manager():
    """Test alert manager basic functionality."""
    print("=" * 60)
    print("TESTING ALERT TAB")
    print("=" * 60)

    # Create manager
    manager = AlertManager(storage_path="test_alerts.json")
    print("✓ Alert manager created")

    # Create test comparison results
    test_results = [
        {
            'ebay_title': 'Yura Kano Photobook Test Item 1',
            'mandarake_title': 'Yura Kano Photo Collection',
            'mandarake_link': 'https://order.mandarake.co.jp/order/detailPage/item?itemCode=1234567',
            'ebay_link': 'https://www.ebay.com/itm/12345',
            'similarity': 85.5,
            'profit_margin': 45.2,
            'mandarake_price': '¥3,000',
            'ebay_price': '$35.00',
            'shipping': '$5.00',
            'sold_date': '2025-01-15',
            'thumbnail': 'https://example.com/image1.jpg'
        },
        {
            'ebay_title': 'Naruto Manga Volume 1',
            'mandarake_title': 'Naruto Vol 1 Japanese',
            'mandarake_link': 'https://order.mandarake.co.jp/order/detailPage/item?itemCode=7654321',
            'ebay_link': 'https://www.ebay.com/itm/67890',
            'similarity': 92.3,
            'profit_margin': 67.8,
            'mandarake_price': '¥500',
            'ebay_price': '$15.00',
            'shipping': '$3.00',
            'sold_date': '2025-01-14',
            'thumbnail': 'https://example.com/image2.jpg'
        },
        {
            'ebay_title': 'Low similarity item',
            'mandarake_title': 'Different item',
            'mandarake_link': 'https://order.mandarake.co.jp/order/detailPage/item?itemCode=999999',
            'ebay_link': 'https://www.ebay.com/itm/99999',
            'similarity': 45.0,  # Below 70% threshold
            'profit_margin': 10.0,  # Below 20% threshold
            'mandarake_price': '¥1,000',
            'ebay_price': '$8.00',
            'shipping': '$2.00',
            'sold_date': '2025-01-13',
            'thumbnail': 'https://example.com/image3.jpg'
        }
    ]

    print(f"\n✓ Created {len(test_results)} test comparison results")

    # Process results with default thresholds (70% similarity, 20% profit)
    created_alerts = manager.process_comparison_results(
        test_results,
        min_similarity=70.0,
        min_profit=20.0
    )

    print(f"✓ Created {len(created_alerts)} alerts (filtered by thresholds)")
    print(f"  Expected: 2 alerts (items 1 and 2 meet thresholds)")

    # Verify correct filtering
    assert len(created_alerts) == 2, f"Expected 2 alerts, got {len(created_alerts)}"
    print("✓ Threshold filtering works correctly")

    # Test state transitions
    alert_id = created_alerts[0]['alert_id']
    print(f"\n✓ Testing state transitions on alert #{alert_id}")

    # Mark as YAY
    manager.update_alert_state(alert_id, AlertState.YAY)
    alert = manager.storage.get_alert_by_id(alert_id)
    assert alert['state'] == AlertState.YAY
    print("  ✓ PENDING → YAY")

    # Mark as PURCHASED
    manager.update_alert_state(alert_id, AlertState.PURCHASED)
    alert = manager.storage.get_alert_by_id(alert_id)
    assert alert['state'] == AlertState.PURCHASED
    print("  ✓ YAY → PURCHASED")

    # Mark as SHIPPED
    manager.update_alert_state(alert_id, AlertState.SHIPPED)
    alert = manager.storage.get_alert_by_id(alert_id)
    assert alert['state'] == AlertState.SHIPPED
    print("  ✓ PURCHASED → SHIPPED")

    # Mark as RECEIVED
    manager.update_alert_state(alert_id, AlertState.RECEIVED)
    alert = manager.storage.get_alert_by_id(alert_id)
    assert alert['state'] == AlertState.RECEIVED
    print("  ✓ SHIPPED → RECEIVED")

    # Mark as POSTED
    manager.update_alert_state(alert_id, AlertState.POSTED)
    alert = manager.storage.get_alert_by_id(alert_id)
    assert alert['state'] == AlertState.POSTED
    print("  ✓ RECEIVED → POSTED")

    # Mark as SOLD
    manager.update_alert_state(alert_id, AlertState.SOLD)
    alert = manager.storage.get_alert_by_id(alert_id)
    assert alert['state'] == AlertState.SOLD
    print("  ✓ POSTED → SOLD")

    # Test bulk operations
    print("\n✓ Testing bulk operations")
    all_alerts = manager.get_all_alerts()
    all_ids = [a['alert_id'] for a in all_alerts]

    manager.bulk_update_state(all_ids, AlertState.NAY)
    print(f"  ✓ Bulk updated {len(all_ids)} alerts to NAY")

    # Clean up
    manager.delete_alerts(all_ids)
    remaining = manager.get_all_alerts()
    assert len(remaining) == 0
    print(f"  ✓ Deleted all {len(all_ids)} alerts")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print("\nAlert tab is ready to use!")
    print("Run the GUI and check the 'Review/Alerts' tab")

if __name__ == "__main__":
    test_alert_manager()
