"""Test Stores tab import and basic functionality"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Testing imports...")

    print("1. Importing shared UI components...")
    from gui.shared_ui_components import URLKeywordPanel, CategoryShopPanel, StoreOptionsPanel
    print("   [OK] Shared UI components imported")

    print("2. Importing base store tab...")
    from gui.base_store_tab import BaseStoreTab
    print("   [OK] Base store tab imported")

    print("3. Importing Mandarake store tab...")
    from gui.mandarake_store_tab import MandarakeStoreTab
    print("   [OK] Mandarake store tab imported")

    print("4. Importing Suruga-ya store tab...")
    from gui.surugaya_store_tab import SurugayaStoreTab
    print("   [OK] Suruga-ya store tab imported")

    print("5. Importing main Stores tab...")
    from gui.stores_tab import StoresTab
    print("   [OK] Main Stores tab imported")

    print("\n[SUCCESS] All imports successful!")
    print("\nNext step: Integrate into gui_config.py")

except Exception as e:
    print(f"\n[ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
