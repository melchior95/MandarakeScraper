"""
Yahoo Auction JSON Data Viewer - Extract and display auction data from embedded JSON
"""
import requests
import json
import re
from pathlib import Path
import sys
from bs4 import BeautifulSoup

def extract_auction_data(auction_url):
    """Fetch Yahoo Auction page and extract JSON data"""
    print(f"Fetching: {auction_url}")

    # Fetch the page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    }

    response = requests.get(auction_url, headers=headers)
    response.encoding = 'utf-8'

    print(f"Status: {response.status_code}")

    # Extract pageData JSON
    page_data = None
    page_data_match = re.search(r'var pageData = ({.*?});', response.text)
    if page_data_match:
        page_data = json.loads(page_data_match.group(1))
        print("Found pageData JSON")

    # Extract __NEXT_DATA__ JSON
    next_data = None
    soup = BeautifulSoup(response.text, 'html.parser')
    next_data_script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
    if next_data_script:
        next_data = json.loads(next_data_script.string)
        print("Found __NEXT_DATA__ JSON")

    return {
        'pageData': page_data,
        'nextData': next_data
    }

def display_auction_info(data):
    """Display auction information from JSON data"""
    import sys
    # Set UTF-8 encoding for console output
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n" + "="*80)
    print("YAHOO AUCTION DATA")
    print("="*80)

    # Extract from __NEXT_DATA__
    if data['nextData']:
        item_data = data['nextData'].get('props', {}).get('pageProps', {}).get('initialState', {}).get('item', {}).get('detail', {}).get('item', {})

        if item_data:
            print(f"\nTitle: {item_data.get('title', 'N/A')}")
            print(f"Auction ID: {item_data.get('auctionId', 'N/A')}")
            print(f"Current Price: ¥{item_data.get('price', 'N/A')}")
            print(f"Bids: {item_data.get('bids', 0)}")
            print(f"Quantity: {item_data.get('quantity', 1)}")
            print(f"Condition: {item_data.get('conditionName', 'N/A')}")
            print(f"End Time: {item_data.get('formattedEndTime', 'N/A')}")

            # Seller info
            seller = item_data.get('seller', {})
            print(f"\nSeller: {seller.get('displayName', 'N/A')}")
            print(f"Rating: {seller.get('rating', {}).get('goodRating', 'N/A')}")
            print(f"Location: {seller.get('location', {}).get('prefecture', 'N/A')}")

            # Images
            images = item_data.get('img', [])
            if images:
                print(f"\nImages ({len(images)} total):")
                for i, img in enumerate(images[:3], 1):
                    print(f"  {i}. {img.get('image', 'N/A')}")
                if len(images) > 3:
                    print(f"  ... and {len(images) - 3} more")

            # Description
            description = item_data.get('description', [])
            if description:
                print(f"\nDescription:")
                print(f"  {description[0][:200]}...")

            # Category
            category = item_data.get('category', {})
            category_path = category.get('path', [])
            if category_path:
                print(f"\nCategory: {' > '.join([c['name'] for c in category_path])}")

            print(f"\nIs Adult: {category.get('isAdult', False)}")

    # Extract from pageData
    if data['pageData']:
        items = data['pageData'].get('items', {})
        print(f"\n--- PageData Info ---")
        print(f"Product ID: {items.get('productID', 'N/A')}")
        print(f"Product Name: {items.get('productName', 'N/A')}")
        print(f"Price: ¥{items.get('price', 'N/A')}")
        print(f"Bids: {items.get('bids', 'N/A')}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python yahoo_auction_json_viewer.py <auction_url>")
        print("\nExample:")
        print("  python yahoo_auction_json_viewer.py https://auctions.yahoo.co.jp/jp/auction/o1202015332")
        return

    auction_url = sys.argv[1]

    # Extract data
    print("\n" + "="*80)
    print("Yahoo Auction JSON Data Viewer")
    print("="*80 + "\n")

    data = extract_auction_data(auction_url)

    # Display info
    display_auction_info(data)

    # Save JSON to file
    output_file = Path("yahoo_auction_data.json")
    output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"\n" + "="*80)
    print(f"Full JSON data saved to: {output_file.absolute()}")
    print("="*80)

if __name__ == "__main__":
    main()
