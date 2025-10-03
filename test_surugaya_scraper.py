#!/usr/bin/env python3
"""
Test Suruga-ya scraper standalone
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.surugaya_scraper import SurugayaScraper

def test_scraper():
    scraper = SurugayaScraper()

    # Test with Pokemon games (category 200)
    keyword = "pokemon"
    category = "200"  # Games
    max_results = 5

    print(f"Testing Suruga-ya scraper...")
    print(f"Keyword: {keyword}")
    print(f"Category: {category}")
    print(f"Max results: {max_results}")
    print("=" * 80)

    try:
        results = scraper.search(keyword, category=category, max_results=max_results)

        print(f"\n[SUCCESS] Found {len(results)} results")

        # Save to JSON
        output_file = "surugaya_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"[SUCCESS] Results saved to: {output_file}")

        # Print first result details
        if results:
            item = results[0]
            print(f"\nFirst result:")
            print(f"  Title: {item['title'][:80]}...")
            print(f"  Price: ¥{item['price']:.0f}")
            print(f"  Condition: {item['condition']}")
            print(f"  Stock: {item['stock_status']}")
            print(f"  URL: {item['url'][:80]}...")
            print(f"  Has Image: {'Yes' if item['image_url'] else 'No'}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_scraper()
    sys.exit(0 if success else 1)
