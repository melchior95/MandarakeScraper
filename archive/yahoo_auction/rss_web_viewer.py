"""
Mandarake RSS Web Viewer - Flask + Tailwind CSS
Modern web interface for browsing Mandarake RSS feeds
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scrapers.mandarake_rss_monitor import MandarakeRSSMonitor

app = Flask(__name__)
CORS(app)

# Initialize RSS monitor
monitor = MandarakeRSSMonitor(use_browser_mimic=True)

# Track seen items and item history
SEEN_FILE = Path(__file__).parent / 'mandarake_rss_seen.json'
HISTORY_FILE = Path(__file__).parent / 'mandarake_rss_history.json'
seen_items = set()
item_history = {}  # {shop_code: [items...]}
last_fetch_time = {}  # {shop_code: timestamp} - Track when each feed was last fetched

MAX_HISTORY_PER_STORE = 5000
CACHE_DURATION = 60  # Cache duration in seconds (1 minute)

def load_seen_items():
    """Load seen items from file"""
    global seen_items
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, 'r') as f:
                data = json.load(f)
                seen_items = set(data.get('seen_items', []))
        except:
            seen_items = set()

def save_seen_items():
    """Save seen items to file"""
    try:
        with open(SEEN_FILE, 'w') as f:
            json.dump({'seen_items': list(seen_items)}, f, indent=2)
    except Exception as e:
        print(f"Error saving seen items: {e}")

def load_history():
    """Load item history from file"""
    global item_history
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                item_history = json.load(f)
        except:
            item_history = {}

def save_history():
    """Save item history to file"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(item_history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")

def add_items_to_history(shop_code, new_items):
    """Add new items to history, maintaining max limit"""
    if shop_code not in item_history:
        item_history[shop_code] = []

    # Get existing item codes with their indices
    existing_items = {item['item_code']: item for item in item_history[shop_code]}

    # Merge new items with existing ones
    merged = {}

    # Add all new items first (these are the newest from RSS)
    for item in new_items:
        merged[item['item_code']] = item

    # Add existing items that aren't in new items
    for item_code, item in existing_items.items():
        if item_code not in merged:
            merged[item_code] = item

    # Convert back to list and sort by pub_date (newest first)
    item_history[shop_code] = sorted(
        merged.values(),
        key=lambda x: x.get('pub_date', ''),
        reverse=True
    )[:MAX_HISTORY_PER_STORE]

    save_history()

# Load data on startup
load_seen_items()
load_history()

# Item code prefix to store name mapping
STORE_PREFIXES = {
    '01': 'Nakano',
    '02': 'Shibuya',
    '03': 'Ikebukuro',
    '04': 'Nagoya',
    '05': 'Grandchaos',
    '06': 'Umeda',
    '07': 'Fukuoka',
    '08': 'Kokura',
    '09': 'Sapporo',
    '10': 'Kyoto',
    '11': 'Utsunomiya',
    '12': 'Complex',
    '13': 'Nakano',  # Alternative prefix
    '14': 'Nayuta',
    '15': 'CoCoo',
    '16': 'Sara',
}

def get_store_from_item_code(item_code):
    """Extract store name from item code prefix"""
    if not item_code or len(item_code) < 2:
        return ''
    prefix = item_code[:2]
    return STORE_PREFIXES.get(prefix, '')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/feeds')
def get_feeds():
    """Get list of available RSS feeds"""
    feeds = [
        {'code': 'all', 'name': 'All Stores', 'location': 'All Locations'},
        {'code': 'nkn', 'name': 'Nakano Store', 'location': 'Tokyo'},
        {'code': 'shr', 'name': 'Shibuya Store', 'location': 'Tokyo'},
        {'code': 'ikebukuro', 'name': 'Ikebukuro Store', 'location': 'Tokyo'},
        {'code': 'utsunomiya', 'name': 'Utsunomiya Store', 'location': 'Tochigi'},
        {'code': 'nagoya', 'name': 'Nagoya Store', 'location': 'Aichi'},
        {'code': 'umeda', 'name': 'Umeda Store', 'location': 'Osaka'},
        {'code': 'fukuoka', 'name': 'Fukuoka Store', 'location': 'Fukuoka'},
        {'code': 'kokura', 'name': 'Kokura Store', 'location': 'Fukuoka'},
        {'code': 'sapporo', 'name': 'Sapporo Store', 'location': 'Hokkaido'},
        {'code': 'kyoto', 'name': 'Kyoto Store', 'location': 'Kyoto'},
        {'code': 'grand-chaos', 'name': 'Grand Chaos', 'location': 'Tokyo'},
        {'code': 'complex', 'name': 'Complex', 'location': 'Tokyo'},
        {'code': 'nayuta', 'name': 'Nayuta', 'location': 'Tokyo'},
        {'code': 'cocoo', 'name': 'CoCoo', 'location': 'Tokyo'},
        {'code': 'sala', 'name': 'Sara', 'location': 'Tokyo'},
    ]
    return jsonify(feeds)

@app.route('/api/cache/<shop_code>')
def get_cache(shop_code):
    """Get cached items immediately (instant response)"""
    import time

    try:
        page = int(request.args.get('page', 1))
        items_per_page = 500

        # Check if we have cached items
        if shop_code not in item_history or len(item_history[shop_code]) == 0:
            return jsonify({
                'items': [],
                'count': 0,
                'total_items': 0,
                'total_pages': 0,
                'current_page': page,
                'new_count': 0,
                'has_cache': False
            })

        all_items = item_history[shop_code]

        # Calculate pagination
        total_items = len(all_items)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = all_items[start_idx:end_idx]

        time_since_fetch = None
        if shop_code in last_fetch_time:
            time_since_fetch = time.time() - last_fetch_time[shop_code]

        print(f"[CACHE] Returning cached {shop_code} data instantly")

        return jsonify({
            'items': page_items,
            'count': len(page_items),
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'new_count': sum(1 for item in page_items if item.get('is_new', False)),
            'has_cache': True,
            'cache_age': int(time_since_fetch) if time_since_fetch else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/items/<shop_code>')
def get_items(shop_code):
    """Get RSS items for a specific shop with pagination (always fetches fresh)"""
    import time

    try:
        page = int(request.args.get('page', 1))
        items_per_page = 500
        cache_only = request.args.get('cache_only', 'false').lower() == 'true'

        # If cache_only, just return cached items
        if cache_only:
            if shop_code in item_history and len(item_history[shop_code]) > 0:
                all_items = item_history[shop_code]
                total_items = len(all_items)
                total_pages = (total_items + items_per_page - 1) // items_per_page
                start_idx = (page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_items = all_items[start_idx:end_idx]

                time_since_fetch = None
                if shop_code in last_fetch_time:
                    time_since_fetch = time.time() - last_fetch_time[shop_code]

                return jsonify({
                    'items': page_items,
                    'count': len(page_items),
                    'total_items': total_items,
                    'total_pages': total_pages,
                    'current_page': page,
                    'new_count': sum(1 for item in page_items if item.get('is_new', False)),
                    'from_cache': True,
                    'cache_age': int(time_since_fetch) if time_since_fetch else 0
                })
            else:
                return jsonify({'items': [], 'count': 0, 'total_items': 0})

        # Fetch fresh items from RSS
        time_since_fetch = None
        if shop_code in last_fetch_time:
            time_since_fetch = time.time() - last_fetch_time[shop_code]

        cache_age_str = f"{time_since_fetch:.1f}s" if time_since_fetch else "never"
        print(f"[FETCH] Fetching fresh {shop_code} data (last fetch: {cache_age_str} ago)")
        fresh_items = monitor.fetch_feed(shop_code)

        # Update last fetch time
        last_fetch_time[shop_code] = time.time()

        if not fresh_items:
            return jsonify({'error': 'No items found'}), 404

        # Process fresh items
        processed_items = []
        for item in fresh_items:
            link = item.get('link', '')
            item_code = ''
            if 'itemCode=' in link:
                item_code = link.split('itemCode=')[1].split('&')[0]

            # Extract thumbnail from description
            description = item.get('description', '')
            thumbnail = ''
            if 'src="' in description:
                thumbnail = description.split('src="')[1].split('"')[0]

            # Check if new
            is_new = item_code not in seen_items if item_code else True

            # Get store name from item code
            store = get_store_from_item_code(item_code)

            processed_items.append({
                'title': item.get('title', 'No Title'),
                'link': link,
                'thumbnail': thumbnail,
                'pub_date': item.get('pub_date', ''),
                'item_code': item_code,
                'is_new': is_new,
                'store': store
            })

        # Add fresh items to history
        add_items_to_history(shop_code, processed_items)

        # Get all items from history (includes fresh + historical)
        all_items = item_history.get(shop_code, [])

        # Calculate pagination
        total_items = len(all_items)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = all_items[start_idx:end_idx]

        return jsonify({
            'items': page_items,
            'count': len(page_items),
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'new_count': sum(1 for item in page_items if item.get('is_new', False))
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_cache/<shop_code>', methods=['POST'])
def clear_cache(shop_code):
    """Clear cache for a specific store"""
    try:
        # Clear time-based cache
        if shop_code in last_fetch_time:
            del last_fetch_time[shop_code]

        # Clear item history
        if shop_code in item_history:
            del item_history[shop_code]
            save_history()

        print(f"[CACHE CLEARED] Cleared cache for {shop_code}")

        return jsonify({
            'success': True,
            'message': f'Cache cleared for {shop_code}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark_seen', methods=['POST'])
def mark_seen():
    """Mark item as seen"""
    data = request.get_json()
    item_code = data.get('item_code')

    if item_code:
        seen_items.add(item_code)
        save_seen_items()
        return jsonify({'success': True})

    return jsonify({'error': 'No item code provided'}), 400

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """Translate Japanese text to English"""
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        import requests
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'ja',
            'tl': 'en',
            'dt': 't',
            'q': text
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            result = response.json()
            translated = ''.join([item[0] for item in result[0]])
            return jsonify({'translated': translated})
        else:
            return jsonify({'error': 'Translation failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ebay_search', methods=['POST'])
def ebay_search():
    """Search eBay using translated title"""
    data = request.get_json()
    title = data.get('title', '')

    if not title:
        return jsonify({'error': 'No title provided'}), 400

    try:
        import requests

        # First translate the title
        translate_url = "https://translate.googleapis.com/translate_a/single"
        translate_params = {
            'client': 'gtx',
            'sl': 'ja',
            'tl': 'en',
            'dt': 't',
            'q': title
        }
        translate_response = requests.get(translate_url, params=translate_params, timeout=5)

        if translate_response.status_code != 200:
            return jsonify({'error': 'Translation failed'}), 500

        result = translate_response.json()
        translated_title = ''.join([item[0] for item in result[0]])

        # Create eBay search URL
        ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(translated_title)}&_sop=10&LH_Complete=1&LH_Sold=1"

        return jsonify({
            'translated_title': translated_title,
            'ebay_url': ebay_url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mandarake/search', methods=['POST'])
def mandarake_search():
    """
    Search Mandarake for a title and return price + stock status
    Lazy loading approach - one item at a time
    """
    data = request.get_json()
    title = data.get('title', '')

    if not title:
        return jsonify({'error': 'No title provided'}), 400

    try:
        # Search Mandarake live
        result = search_mandarake_live(title)

        if result:
            return jsonify({
                'found': True,
                'mandarake_price_jpy': result['price'],
                'mandarake_price_usd': result['price'] / 151.5,  # USD/JPY rate
                'in_stock': result['in_stock'],
                'store': result['store'],
                'link': result['link'],
                'title': result['title'],
                'item_code': result.get('item_code', '')
            })

        return jsonify({'found': False})

    except Exception as e:
        print(f"Error searching Mandarake: {e}")
        return jsonify({'error': str(e)}), 500

def search_mandarake_live(title):
    """Search Mandarake and check stock status"""
    from urllib.parse import quote
    from bs4 import BeautifulSoup
    import re
    import time

    # Add parent directory to path if not already there
    import sys
    from pathlib import Path
    parent_dir = str(Path(__file__).parent.parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from browser_mimic import BrowserMimic

    keyword = quote(title)
    url = f"https://order.mandarake.co.jp/order/listPage/list?keyword={keyword}&lang=en"

    print(f"Searching Mandarake for: {title}")
    print(f"URL: {url}")

    browser = BrowserMimic()
    try:
        # Make request with rate limiting
        time.sleep(2)  # Rate limit: 2 seconds between requests
        response = browser.get(url)

        if response.status_code != 200:
            print(f"Bad response: {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find first product listing
        first_item = soup.select_one('.thumlarge .block')
        if not first_item:
            print("No items found in search results")
            return None

        # Extract price
        price_elem = first_item.select_one('.price')
        if not price_elem:
            print("No price element found")
            return None

        price_text = price_elem.text.strip()
        print(f"Price text: {price_text}")

        # Parse price (handles both yen and JPY formats)
        price_match = re.search(r'([0-9,]+)\s*(?:yen|円)', price_text, re.IGNORECASE)
        if not price_match:
            print(f"Could not parse price from: {price_text}")
            return None

        price = int(price_match.group(1).replace(',', ''))

        # Extract stock status - KEY FEATURE
        stock_elem = first_item.select_one('.stock')
        stock_text = stock_elem.text.strip() if stock_elem else ''
        print(f"Stock text: {stock_text}")

        # Check for "In stock" in either English or Japanese
        in_stock = ('in stock' in stock_text.lower() or
                    '在庫あります' in stock_text or
                    'in warehouse' in stock_text.lower())

        # Also check if it says "sold out"
        if 'sold out' in stock_text.lower() or '売切' in stock_text:
            in_stock = False

        # Extract store
        shop_elem = first_item.select_one('.shop')
        store = shop_elem.text.strip() if shop_elem else 'Unknown'

        # Extract item code and link
        link_elem = first_item.select_one('a')
        if not link_elem:
            print("No link element found")
            return None

        link = link_elem.get('href', '')
        item_code = None
        if 'itemCode=' in link:
            item_code = link.split('itemCode=')[1].split('&')[0]

        # Make absolute URL
        if link.startswith('/'):
            link = f"https://order.mandarake.co.jp{link}"

        # Extract title
        title_elem = first_item.select_one('.title')
        item_title = title_elem.text.strip() if title_elem else title

        print(f"Found: {item_title} - ¥{price} - Stock: {in_stock} @ {store}")

        return {
            'price': price,
            'in_stock': in_stock,
            'store': store,
            'link': link,
            'item_code': item_code,
            'title': item_title
        }

    except Exception as e:
        print(f"Exception in search_mandarake_live: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        browser.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Mandarake RSS Web Viewer")
    print("="*60)
    print("\nStarting server at http://localhost:5000")
    print("Press Ctrl+C to stop\n")

    app.run(debug=True, port=5000, host='127.0.0.1')
