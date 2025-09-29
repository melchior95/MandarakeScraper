#!/usr/bin/env python3
"""
Test script to validate eBay OAuth endpoints and API configuration
"""

import json
import requests
import base64
import logging
from typing import Dict, Any

def load_config(config_path: str = "configs/naruto.json") -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return {}

def get_oauth_token(config: Dict[str, Any]) -> str:
    """Get OAuth access token using client credentials flow"""

    # Get environment-specific endpoints
    env = config.get('ebay_environment', 'sandbox')
    endpoints = config.get('oauth_endpoints', {}).get(env, {})
    token_url = endpoints.get('token_url')

    if not token_url:
        raise ValueError(f"Token URL not found for environment: {env}")

    # Prepare credentials
    client_id = config.get('client_id')
    client_secret = config.get('client_secret')

    if not client_id or not client_secret:
        raise ValueError("Client ID and Client Secret are required")

    # Encode credentials for Basic auth
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    # Prepare request
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_credentials}'
    }

    data = {
        'grant_type': 'client_credentials',
        'scope': ' '.join(config.get('oauth_scopes', ['https://api.ebay.com/oauth/api_scope']))
    }

    print(f"Testing OAuth endpoint: {token_url}")
    print(f"Environment: {env}")
    print(f"Client ID: {client_id}")
    print(f"Scopes: {data['scope']}")

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            token_data = response.json()
            print("SUCCESS: OAuth token obtained successfully!")
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Expires In: {token_data.get('expires_in')} seconds")
            print(f"Access Token: {token_data.get('access_token')[:20]}...")
            return token_data.get('access_token')
        else:
            print("FAILED: Failed to get OAuth token")
            print(f"Error Response: {response.text}")
            return None

    except Exception as e:
        print(f"ERROR: Exception during OAuth request: {e}")
        return None

def test_ebay_api_call(access_token: str, config: Dict[str, Any]) -> bool:
    """Test a simple eBay API call to validate token"""

    env = config.get('ebay_environment', 'sandbox')

    # Use Browse API search endpoint for testing
    if env == 'sandbox':
        api_url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
    else:
        api_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
    }

    params = {
        'q': 'pokemon card',
        'limit': 3
    }

    print(f"\nTesting API call: {api_url}")

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=30)

        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: API call successful!")
            print(f"Total found: {data.get('total', 0)} items")

            items = data.get('itemSummaries', [])
            for i, item in enumerate(items[:2], 1):
                print(f"  Item {i}: {item.get('title', 'No title')}")
                print(f"    Price: {item.get('price', {}).get('value', 'N/A')} {item.get('price', {}).get('currency', '')}")

            return True
        else:
            print("FAILED: API call failed")
            print(f"Error Response: {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: Exception during API call: {e}")
        return False

def main():
    """Main test function"""

    print("eBay OAuth and API Endpoint Validation Test")
    print("=" * 50)

    # Load configuration
    config = load_config()
    if not config:
        print("❌ Failed to load configuration")
        return

    print(f"Configuration loaded: {len(config)} settings")

    # Test OAuth token acquisition
    print("\n1. Testing OAuth Token Acquisition")
    print("-" * 30)

    access_token = get_oauth_token(config)

    if not access_token:
        print("ERROR: Cannot proceed without valid access token")
        return

    # Test API call
    print("\n2. Testing API Call with Token")
    print("-" * 30)

    api_success = test_ebay_api_call(access_token, config)

    # Summary
    print("\nTest Results Summary")
    print("=" * 30)
    print(f"OAuth Token: {'SUCCESS' if access_token else 'FAILED'}")
    print(f"API Call: {'SUCCESS' if api_success else 'FAILED'}")

    if access_token and api_success:
        print("\nAll tests passed! eBay API integration is properly configured.")
    else:
        print("\nSome tests failed. Check configuration and credentials.")

if __name__ == "__main__":
    main()