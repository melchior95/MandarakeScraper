#!/usr/bin/env python3
"""
eBay Marketplace Account Deletion Endpoint Configuration

This file helps you configure and test the eBay deletion endpoint
before deploying it and registering with eBay.
"""

import hashlib
import secrets
import string
import os
from datetime import datetime

def generate_verification_token(length: int = 64) -> str:
    """
    Generate a secure verification token for eBay endpoint

    Args:
        length: Token length (32-80 characters allowed by eBay)

    Returns:
        Secure random token using alphanumeric, underscore, and hyphen
    """
    if length < 32 or length > 80:
        raise ValueError("Token length must be between 32 and 80 characters")

    # eBay allows: alphanumeric, underscore (_), and hyphen (-)
    alphabet = string.ascii_letters + string.digits + '_-'
    token = ''.join(secrets.choice(alphabet) for _ in range(length))

    return token

def test_challenge_response(challenge_code: str, verification_token: str, endpoint_url: str) -> str:
    """
    Test the challenge response generation to ensure it matches eBay's expectations

    Args:
        challenge_code: Code sent by eBay during verification
        verification_token: Your 32-80 character token
        endpoint_url: Your HTTPS endpoint URL

    Returns:
        SHA-256 hash that should be returned to eBay
    """
    # Hash in the exact order required by eBay
    hash_input = challenge_code + verification_token + endpoint_url
    challenge_response = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    print(f"Challenge Code: {challenge_code}")
    print(f"Verification Token: {verification_token}")
    print(f"Endpoint URL: {endpoint_url}")
    print(f"Hash Input: {hash_input}")
    print(f"Challenge Response: {challenge_response}")

    return challenge_response

def create_env_file(verification_token: str, endpoint_url: str):
    """
    Create .env file with configuration for the endpoint

    Args:
        verification_token: Generated verification token
        endpoint_url: Your HTTPS endpoint URL
    """
    env_content = f"""# eBay Marketplace Account Deletion Endpoint Configuration
# Generated on {datetime.now().isoformat()}

# Verification token (32-80 characters, alphanumeric + underscore + hyphen)
EBAY_VERIFICATION_TOKEN={verification_token}

# Your HTTPS endpoint URL (must be accessible from internet)
EBAY_ENDPOINT_URL={endpoint_url}

# Optional: Add your domain for CORS if needed
# ALLOWED_ORIGIN=https://your-domain.com
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    print(f"Created .env file with configuration")
    print(f"Verification token length: {len(verification_token)}")

def validate_configuration():
    """
    Validate the current configuration
    """
    print("=== eBay Endpoint Configuration Validation ===\n")

    # Check environment variables
    token = os.getenv('EBAY_VERIFICATION_TOKEN')
    url = os.getenv('EBAY_ENDPOINT_URL')

    print(f"Verification Token Set: {'✓' if token else '✗'}")
    if token:
        print(f"Token Length: {len(token)} ({'✓' if 32 <= len(token) <= 80 else '✗'})")
        # Check allowed characters
        allowed_chars = set(string.ascii_letters + string.digits + '_-')
        token_chars = set(token)
        valid_chars = token_chars.issubset(allowed_chars)
        print(f"Valid Characters: {'✓' if valid_chars else '✗'}")
        if not valid_chars:
            invalid_chars = token_chars - allowed_chars
            print(f"  Invalid characters found: {invalid_chars}")

    print(f"\nEndpoint URL Set: {'✓' if url else '✗'}")
    if url:
        print(f"HTTPS Protocol: {'✓' if url.startswith('https://') else '✗'}")
        print(f"URL: {url}")

    print(f"\nConfiguration Complete: {'✓' if token and url and url.startswith('https://') and 32 <= len(token) <= 80 else '✗'}")

def setup_configuration():
    """
    Interactive setup for eBay endpoint configuration
    """
    print("=== eBay Marketplace Account Deletion Endpoint Setup ===\n")

    # Generate verification token
    print("1. Generating verification token...")
    token = generate_verification_token(64)  # Use 64 characters for good security
    print(f"Generated token: {token}")

    # Get endpoint URL
    print(f"\n2. Endpoint URL configuration:")
    print("   You need to provide an HTTPS URL where this endpoint will be accessible.")
    print("   Examples:")
    print("   - https://your-domain.com/ebay-deletion-endpoint")
    print("   - https://api.your-app.com/webhooks/ebay-deletion")
    print("   - https://your-server.herokuapp.com/ebay-deletion-endpoint")

    url = input("\nEnter your HTTPS endpoint URL: ").strip()

    if not url.startswith('https://'):
        print("Warning: URL must use HTTPS protocol")
        url = 'https://' + url.lstrip('http://')
        print(f"Corrected URL: {url}")

    # Create configuration
    create_env_file(token, url)

    # Test challenge response
    print(f"\n3. Testing challenge response generation...")
    test_challenge_code = "test123"
    challenge_response = test_challenge_response(test_challenge_code, token, url)

    print(f"\n=== Configuration Complete ===")
    print(f"Verification Token: {token}")
    print(f"Endpoint URL: {url}")
    print(f"Configuration saved to .env file")

    print(f"\n=== Next Steps ===")
    print("1. Deploy the ebay_deletion_endpoint.py to your server")
    print("2. Make sure it's accessible at the URL you specified")
    print("3. Test the /health endpoint to verify it's working")
    print("4. Go to your eBay Developer Console > Alerts and Notifications")
    print("5. Enter your endpoint URL and verification token")
    print("6. eBay will send a challenge code to verify your endpoint")
    print("7. Once verified, your production API keys will be enabled")

    return token, url

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "generate-token":
            length = int(sys.argv[2]) if len(sys.argv) > 2 else 64
            token = generate_verification_token(length)
            print(f"Generated verification token ({length} chars): {token}")

        elif command == "test-challenge":
            if len(sys.argv) < 5:
                print("Usage: python ebay_endpoint_config.py test-challenge <challenge_code> <token> <url>")
                sys.exit(1)

            challenge_code = sys.argv[2]
            token = sys.argv[3]
            url = sys.argv[4]
            test_challenge_response(challenge_code, token, url)

        elif command == "validate":
            validate_configuration()

        elif command == "setup":
            setup_configuration()

        else:
            print("Unknown command. Available commands: generate-token, test-challenge, validate, setup")

    else:
        print("eBay Marketplace Account Deletion Endpoint Configuration")
        print("\nCommands:")
        print("  python ebay_endpoint_config.py setup              # Interactive setup")
        print("  python ebay_endpoint_config.py generate-token     # Generate verification token")
        print("  python ebay_endpoint_config.py validate           # Validate current config")
        print("  python ebay_endpoint_config.py test-challenge <code> <token> <url>  # Test challenge response")
        print("\nFor initial setup, run: python ebay_endpoint_config.py setup")