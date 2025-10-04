"""
Wrapper for running the Scrapy eBay spider from the GUI
"""
import sys
import subprocess
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Optional


def run_ebay_scrapy_search(query: str, max_results: int = 10, sold_listings: bool = True) -> List[Dict]:
    """
    Run the eBay Scrapy spider and return results

    Args:
        query: Search query
        max_results: Maximum number of results to fetch
        sold_listings: Whether to search sold listings only

    Returns:
        List of dictionaries containing scraped eBay data
    """
    # Create temporary file for results
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        temp_output = f.name

    try:
        # Build scrapy command
        spider_path = Path(__file__).parent / "ebay-scrapy-scraper-main"

        cmd = [
            sys.executable,  # Use current Python interpreter
            "-m", "scrapy", "crawl", "ebay_search",
            "-a", f"query={query}",
            "-a", f"max_results={max_results}",
            "-a", f"sold_listings={'True' if sold_listings else 'False'}",
            "-O", temp_output,
            "-s", "LOG_LEVEL=INFO"  # Show INFO logs to see URLs
        ]

        print(f"[SCRAPY] Running command: {' '.join(cmd)}")
        print(f"[SCRAPY] Working directory: {spider_path}")

        # Run scrapy spider with proper terminal detachment
        # On Windows, use CREATE_NO_WINDOW to prevent terminal takeover
        import platform
        kwargs = {
            'cwd': str(spider_path),
            'capture_output': True,
            'text': True,
            'timeout': 60,
            'stdin': subprocess.DEVNULL  # Don't inherit stdin
        }

        # Windows-specific: prevent console window
        if platform.system() == 'Windows':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(cmd, **kwargs)

        # Print spider logs (they go to stderr)
        if result.stderr:
            print(f"[SCRAPY LOG]\n{result.stderr}")

        if result.returncode != 0:
            print(f"[SCRAPY ERROR] Spider failed with code {result.returncode}")
            return []

        # Read results from temp file
        with open(temp_output, 'r', encoding='utf-8') as f:
            results = json.load(f)

        print(f"[SCRAPY] Successfully scraped {len(results)} items")
        return results

    except subprocess.TimeoutExpired:
        print("[SCRAPY ERROR] Spider timed out after 60 seconds")
        return []
    except Exception as e:
        print(f"[SCRAPY ERROR] {e}")
        return []
    finally:
        # Clean up temp file
        try:
            Path(temp_output).unlink(missing_ok=True)
        except (OSError, PermissionError) as e:
            logging.debug(f"Failed to delete temp file {temp_output}: {e}")


if __name__ == "__main__":
    # Test the wrapper
    print("Testing eBay Scrapy Search...")
    results = run_ebay_scrapy_search("pokemon card", max_results=3, sold_listings=True)

    if results:
        print(f"\nFound {len(results)} results:")
        for i, item in enumerate(results, 1):
            print(f"\n{i}. {item['product_title'][:60]}...")
            print(f"   Price: {item['current_price']}")
            print(f"   Shipping: {item.get('shipping_cost', 'N/A')}")
            print(f"   Sold: {item.get('sold_date', 'N/A')}")
    else:
        print("No results found")