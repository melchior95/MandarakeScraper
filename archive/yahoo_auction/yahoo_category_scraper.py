"""
Yahoo Auction Category Scraper - Extract listings from adult category pages
"""
import requests
import json
import re
from pathlib import Path
import webbrowser
import sys
from bs4 import BeautifulSoup

def extract_category_listings(category_url, proxy=None):
    """Fetch Yahoo Auction category/search page and extract listings"""
    print(f"Fetching: {category_url}")
    if proxy:
        print(f"Using proxy: {proxy}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    }

    # Setup proxy if provided
    proxies = None
    if proxy:
        proxies = {
            'http': proxy,
            'https': proxy
        }

    response = requests.get(category_url, headers=headers, proxies=proxies, timeout=30)
    response.encoding = 'utf-8'

    print(f"Status: {response.status_code}")

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    items = []

    # First try: Look for JSON data in scripts
    scripts = soup.find_all('script')

    for script in scripts:
        if not script.string:
            continue

        # Look for searchResult variable
        if 'searchResult' in script.string or 'Result' in script.string:
            # Try to extract JSON from various variable patterns
            patterns = [
                r'var\s+searchResult\s*=\s*(\{.*?\});',
                r'var\s+\w+Result\s*=\s*(\{.*?\});',
                r'=\s*(\{[^{]*"Result"[^}]*\{.*?\}.*?\});',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, script.string, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match.group(1))

                        # Check for items in different locations
                        if 'Result' in data and 'items' in data['Result']:
                            items.extend(data['Result']['items'])
                            print(f"Found {len(data['Result']['items'])} items in Result.items")
                        elif 'items' in data:
                            items.extend(data['items'])
                            print(f"Found {len(data['items'])} items in items")
                    except json.JSONDecodeError:
                        continue

    # Second try: Parse HTML elements directly (for search results)
    if not items:
        print("No JSON data found, trying HTML parsing...")

        # Look for Product list items
        product_items = soup.find_all('li', class_=lambda x: x and 'Product' in x if x else False)

        for product in product_items:
            item = {}

            # Extract auction ID from link
            link = product.find('a', href=re.compile(r'/auction/'))
            if link:
                href = link.get('href', '')
                id_match = re.search(r'/auction/([a-z0-9]+)', href)
                if id_match:
                    item['AuctionID'] = id_match.group(1)

            # Extract title
            title_elem = product.find(['h3', 'div'], class_=lambda x: x and ('title' in x.lower() or 'Title' in x) if x else False)
            if title_elem:
                item['Title'] = title_elem.get_text(strip=True)

            # Extract price
            price_elem = product.find(['div', 'span'], class_=lambda x: x and ('price' in x.lower() or 'Price' in x) if x else False)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract numbers from price text
                price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
                if price_match:
                    item['Price'] = int(price_match.group().replace(',', ''))

            # Extract image
            img = product.find('img')
            if img:
                item['Img'] = {'Image': img.get('src', '')}

            # Extract bid count
            bids_elem = product.find(string=re.compile(r'入札|bid', re.I))
            if bids_elem:
                bid_match = re.search(r'(\d+)', bids_elem)
                if bid_match:
                    item['Bids'] = int(bid_match.group(1))
                else:
                    item['Bids'] = 0
            else:
                item['Bids'] = 0

            if item.get('AuctionID'):
                items.append(item)

        if items:
            print(f"Found {len(items)} items from HTML parsing")

    if not items:
        print("No items found - page may require login or age verification")

    return items

def render_category_html(items, category_url):
    """Render category listings as HTML"""

    html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yahoo Auction Category Listings</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .banner {
            background: #ff0033;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 0 20px;
        }

        .header {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }

        .items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }

        .item-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .item-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .item-image {
            width: 100%;
            height: 250px;
            object-fit: cover;
            background: #f0f0f0;
        }

        .item-info {
            padding: 15px;
        }

        .item-title {
            font-size: 14px;
            line-height: 1.4;
            margin-bottom: 10px;
            height: 40px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }

        .item-price {
            font-size: 20px;
            font-weight: bold;
            color: #ff0033;
            margin-bottom: 5px;
        }

        .item-bids {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
        }

        .item-link {
            display: block;
            text-align: center;
            padding: 8px;
            background: #ff0033;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
        }

        .item-link:hover {
            background: #cc0029;
        }

        .no-items {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 4px;
        }

        .stats {
            background: #e3f2fd;
            padding: 10px 20px;
            border-radius: 4px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="banner">Yahoo Auction Category Viewer - Age Gate Bypassed</div>

    <div class="container">
        <div class="header">
            <h1>Category Listings</h1>
"""

    if items:
        html += f'            <div class="stats">Found {len(items)} auctions</div>\n'
        html += f'            <p><a href="{category_url}" target="_blank">View original category page</a></p>\n'
        html += '        </div>\n\n        <div class="items-grid">\n'

        for item in items:
            auction_id = item.get('AuctionID', '')
            title = item.get('Title', 'No Title')
            price = item.get('Price', 0)
            bids = item.get('Bids', 0)
            img = item.get('Img', {}).get('Image', '')
            item_url = f"https://auctions.yahoo.co.jp/jp/auction/{auction_id}"

            html += f'''            <div class="item-card">
                <img src="{img}" class="item-image" alt="{title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22250%22 height=%22250%22%3E%3Crect fill=%22%23f0f0f0%22 width=%22250%22 height=%22250%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22%3ENo Image%3C/text%3E%3C/svg%3E'">
                <div class="item-info">
                    <div class="item-title">{title}</div>
                    <div class="item-price">¥{price:,}</div>
                    <div class="item-bids">{bids} bid(s)</div>
                    <a href="{item_url}" class="item-link" target="_blank">View Auction</a>
                </div>
            </div>
'''

        html += '        </div>\n'
    else:
        html += '''        </div>
        <div class="no-items">
            <h2>No Items Found</h2>
            <p>This category may require login or age verification to access listings.</p>
            <p>The data might be loaded dynamically via JavaScript after age verification.</p>
        </div>
'''

    html += '''    </div>
</body>
</html>
'''

    return html

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python yahoo_category_scraper.py <category_url> [proxy]")
        print("\nExamples:")
        print("  python yahoo_category_scraper.py https://auctions.yahoo.co.jp/category/list/26156/")
        print("  python yahoo_category_scraper.py <url> http://proxy.example.com:8080")
        print("  python yahoo_category_scraper.py <url> socks5://127.0.0.1:1080")
        print("\nProxy formats:")
        print("  - HTTP: http://host:port")
        print("  - HTTPS: https://host:port")
        print("  - SOCKS5: socks5://host:port")
        return

    category_url = sys.argv[1]
    proxy = sys.argv[2] if len(sys.argv) > 2 else None

    print("\n" + "="*80)
    print("Yahoo Auction Category Scraper")
    print("="*80 + "\n")

    # Extract listings
    items = extract_category_listings(category_url, proxy=proxy)

    # Render HTML
    html = render_category_html(items, category_url)

    # Save to file
    output_file = Path("yahoo_category_listings.html")
    output_file.write_text(html, encoding='utf-8')

    print(f"\nRendered HTML saved to: {output_file.absolute()}")
    print("Opening in browser...\n")

    # Open in browser
    webbrowser.open(output_file.absolute().as_uri())

    print("="*80)
    print(f"Done! Found {len(items)} auction listings.")
    print("="*80)

if __name__ == "__main__":
    main()
