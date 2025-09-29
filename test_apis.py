#!/usr/bin/env python3
"""
API Test Script - Test all configured APIs
"""

import json
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mandarake_scraper import EbayAPI, GoogleSheetsAPI, GoogleDriveAPI

def test_ebay_api(config):
    """Test eBay API connectivity"""
    print("[EBAY] Testing eBay API...")

    client_id = config.get('client_id')
    client_secret = config.get('client_secret')

    if not client_id or not client_secret:
        print("[FAIL] eBay API: Credentials not configured")
        return False

    if client_id == "YOUR_EBAY_CLIENT_ID" or client_secret == "YOUR_EBAY_CLIENT_SECRET":
        print("[FAIL] eBay API: Still using placeholder credentials")
        return False

    try:
        api = EbayAPI(client_id, client_secret)

        # Test token acquisition
        token = api._get_access_token()
        if token:
            print("[PASS] eBay API: Token acquired successfully")

            # Test a simple search
            result = api.search_product("test")
            print(f"[PASS] eBay API: Search test completed (found {result.get('ebay_listings', 0)} listings)")
            return True
        else:
            print("[FAIL] eBay API: Failed to get access token")
            return False

    except Exception as e:
        print(f"[FAIL] eBay API: Error - {e}")
        return False

def test_google_sheets_api(config):
    """Test Google Sheets API connectivity"""
    print("\n[SHEETS] Testing Google Sheets API...")

    sheets_config = config.get('google_sheets') or config.get('sheet')
    if not sheets_config:
        print("[FAIL] Google Sheets: Not configured")
        return False

    sheet_name = sheets_config.get('sheet_name') if isinstance(sheets_config, dict) else sheets_config
    if not sheet_name:
        print("[FAIL] Google Sheets: Sheet name not specified")
        return False

    # Check for credentials files
    creds_files = ['credentials.json', 'service_account.json', 'google_credentials.json']
    creds_path = None

    for filename in creds_files:
        if os.path.exists(filename):
            creds_path = filename
            break

    if not creds_path:
        print("[FAIL] Google Sheets: Credentials file not found")
        print(f"   Expected one of: {', '.join(creds_files)}")
        return False

    try:
        api = GoogleSheetsAPI(sheet_name)
        if api.client:
            print(f"[PASS] Google Sheets: Connected successfully using {creds_path}")

            # Test opening/creating the sheet
            try:
                sheet = api.client.open(sheet_name).sheet1
                print(f"[PASS] Google Sheets: Sheet '{sheet_name}' accessible")
                return True
            except Exception as e:
                print(f"[WARN] Google Sheets: Connected but sheet '{sheet_name}' not accessible - {e}")
                print("   (This might be normal if the sheet doesn't exist yet)")
                return True  # Still consider this a success since API works
        else:
            print("[FAIL] Google Sheets: Failed to initialize client")
            return False

    except Exception as e:
        print(f"[FAIL] Google Sheets: Error - {e}")
        return False

def test_google_drive_api(config):
    """Test Google Drive API connectivity"""
    print("\n[DRIVE] Testing Google Drive API...")

    if not config.get('upload_drive', False):
        print("[INFO] Google Drive: Upload disabled in config")
        return True

    drive_folder = config.get('drive_folder')
    if not drive_folder or drive_folder == "YOUR_DRIVE_FOLDER_ID":
        print("[FAIL] Google Drive: Folder ID not configured")
        return False

    # Check for credentials files
    creds_files = ['credentials.json', 'service_account.json', 'google_credentials.json']
    creds_path = None

    for filename in creds_files:
        if os.path.exists(filename):
            creds_path = filename
            break

    if not creds_path:
        print("[FAIL] Google Drive: Credentials file not found")
        print(f"   Expected one of: {', '.join(creds_files)}")
        return False

    try:
        api = GoogleDriveAPI(drive_folder)
        if api.service:
            print(f"[PASS] Google Drive: Connected successfully using {creds_path}")

            # Test folder access
            try:
                folder_info = api.service.files().get(fileId=drive_folder).execute()
                print(f"[PASS] Google Drive: Folder '{folder_info.get('name', 'Unknown')}' accessible")
                return True
            except Exception as e:
                print(f"[FAIL] Google Drive: Folder ID '{drive_folder}' not accessible - {e}")
                return False
        else:
            print("[FAIL] Google Drive: Failed to initialize service")
            return False

    except Exception as e:
        print(f"[FAIL] Google Drive: Error - {e}")
        return False

def main():
    """Main test function"""
    print("API Configuration Test\n" + "="*50)

    # Load config
    config_path = "configs/naruto.json"
    if not os.path.exists(config_path):
        print(f"[FAIL] Configuration file not found: {config_path}")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"Using config: {config_path}")
    print(f"Keyword: {config.get('keyword', 'Not set')}")

    # Test all APIs
    results = []
    results.append(("eBay API", test_ebay_api(config)))
    results.append(("Google Sheets API", test_google_sheets_api(config)))
    results.append(("Google Drive API", test_google_drive_api(config)))

    # Summary
    print("\n" + "="*50)
    print("SUMMARY:")

    for name, success in results:
        status = "[PASS] Working" if success else "[FAIL] Failed"
        print(f"   {name}: {status}")

    working_count = sum(1 for _, success in results if success)
    print(f"\n{working_count}/{len(results)} APIs are working properly")

    if working_count == len(results):
        print("All APIs are configured and working!")
    else:
        print("Some APIs need attention - see details above")

if __name__ == "__main__":
    main()