"""
Yahoo Auction HTML Renderer - Fetch JSON data and render as clean HTML
"""
import requests
import json
import re
from pathlib import Path
import webbrowser
import sys
from bs4 import BeautifulSoup

def extract_auction_data(auction_url, proxy=None):
    """Fetch Yahoo Auction page and extract JSON data"""
    print(f"Fetching: {auction_url}")
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

    response = requests.get(auction_url, headers=headers, proxies=proxies, timeout=30)
    response.encoding = 'utf-8'

    print(f"Status: {response.status_code}")

    # Extract __NEXT_DATA__ JSON
    soup = BeautifulSoup(response.text, 'html.parser')
    next_data_script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})

    if next_data_script:
        next_data = json.loads(next_data_script.string)
        print("Found auction data")
        return next_data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('item', {}).get('detail', {}).get('item', {})

    return None

def render_auction_html(item_data, auction_url):
    """Render auction data as HTML"""

    title = item_data.get('title', 'No Title')
    price = item_data.get('price', 0)
    bids = item_data.get('bids', 0)
    condition = item_data.get('conditionName', 'N/A')
    end_time = item_data.get('formattedEndTime', 'N/A')
    description_html = item_data.get('descriptionHtml', '')

    # Seller info
    seller = item_data.get('seller', {})
    seller_name = seller.get('displayName', 'Unknown')
    seller_rating = seller.get('rating', {}).get('goodRating', 'N/A')
    seller_location = seller.get('location', {}).get('prefecture', 'N/A')

    # Images
    images = item_data.get('img', [])

    # Category
    category = item_data.get('category', {})
    category_path = category.get('path', [])
    category_str = ' > '.join([c['name'] for c in category_path])

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}

        .banner {{
            background: #ff0033;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .container {{
            max-width: 1200px;
            margin: 20px auto;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}

        .header {{
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .title {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .category {{
            color: #666;
            font-size: 14px;
        }}

        .content {{
            display: flex;
            gap: 20px;
            padding: 20px;
        }}

        .images {{
            flex: 1;
        }}

        .main-image {{
            width: 100%;
            border: 1px solid #e0e0e0;
            margin-bottom: 10px;
        }}

        .thumbnails {{
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }}

        .thumbnail {{
            width: 80px;
            height: 80px;
            object-fit: cover;
            border: 1px solid #e0e0e0;
            cursor: pointer;
        }}

        .thumbnail:hover {{
            border-color: #ff0033;
        }}

        .info {{
            flex: 1;
            max-width: 400px;
        }}

        .price-box {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            padding: 15px;
            margin-bottom: 20px;
        }}

        .price {{
            font-size: 32px;
            font-weight: bold;
            color: #ff0033;
        }}

        .info-item {{
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
        }}

        .info-label {{
            font-weight: bold;
            color: #666;
            font-size: 14px;
        }}

        .info-value {{
            margin-top: 5px;
        }}

        .seller-box {{
            background: #f8f9fa;
            padding: 15px;
            margin-top: 20px;
        }}

        .description {{
            padding: 20px;
            border-top: 1px solid #e0e0e0;
        }}

        .description h3 {{
            margin-bottom: 15px;
        }}

        .btn {{
            display: inline-block;
            padding: 12px 24px;
            background: #ff0033;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 10px;
        }}

        .btn:hover {{
            background: #cc0029;
        }}
    </style>
</head>
<body>
    <div class="banner">Yahoo Auction Viewer - Rendered from JSON Data (No Age Gate)</div>

    <div class="container">
        <div class="header">
            <div class="title">{title}</div>
            <div class="category">{category_str}</div>
        </div>

        <div class="content">
            <div class="images">
                <img src="{images[0]['image'] if images else ''}" class="main-image" id="mainImage" alt="Product Image">
                <div class="thumbnails">
"""

    # Add thumbnail images
    for img in images:
        html += f'                    <img src="{img["thumbnail"]}" class="thumbnail" onclick="document.getElementById(\'mainImage\').src=\'{img["image"]}\'" alt="Thumbnail">\n'

    html += f"""                </div>
            </div>

            <div class="info">
                <div class="price-box">
                    <div class="info-label">Current Price</div>
                    <div class="price">¥{price:,}</div>
                    <div style="margin-top: 10px;">Bids: {bids}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">Condition</div>
                    <div class="info-value">{condition}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">Auction Ends</div>
                    <div class="info-value">{end_time}</div>
                </div>

                <div class="seller-box">
                    <div class="info-label">Seller</div>
                    <div class="info-value">{seller_name}</div>
                    <div style="margin-top: 5px;">Rating: {seller_rating}</div>
                    <div>Location: {seller_location}</div>
                </div>

                <a href="{auction_url}" class="btn" target="_blank">View Original Auction</a>
            </div>
        </div>

        <div class="description">
            <h3>Description</h3>
            {description_html}
        </div>
    </div>
</body>
</html>
"""

    return html

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python yahoo_auction_render.py <auction_url> [proxy]")
        print("\nExamples:")
        print("  python yahoo_auction_render.py https://auctions.yahoo.co.jp/jp/auction/o1202015332")
        print("  python yahoo_auction_render.py <url> http://proxy.example.com:8080")
        print("  python yahoo_auction_render.py <url> socks5://127.0.0.1:1080")
        return

    auction_url = sys.argv[1]
    proxy = sys.argv[2] if len(sys.argv) > 2 else None

    print("\n" + "="*80)
    print("Yahoo Auction HTML Renderer")
    print("="*80 + "\n")

    # Extract data
    item_data = extract_auction_data(auction_url, proxy=proxy)

    if not item_data:
        print("ERROR: Could not extract auction data")
        return

    # Render HTML
    html = render_auction_html(item_data, auction_url)

    # Save to file
    output_file = Path("yahoo_auction_rendered.html")
    output_file.write_text(html, encoding='utf-8')

    print(f"\nRendered HTML saved to: {output_file.absolute()}")
    print("Opening in browser...\n")

    # Open in browser
    webbrowser.open(output_file.absolute().as_uri())

    print("="*80)
    print("Done! The auction is now displayed with all content visible.")
    print("="*80)

if __name__ == "__main__":
    main()
