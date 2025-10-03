"""
Yahoo Auction Viewer - Remove age gate completely and show original page
"""
import requests
import re
from pathlib import Path
import webbrowser
import sys
from bs4 import BeautifulSoup

def remove_age_gate(auction_url):
    """Fetch Yahoo Auction page and completely remove age gate"""
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
    print(f"Page size: {len(response.text)} chars")

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find and remove the age gate section
    # The age gate is in a section with specific text
    age_gate_sections = soup.find_all('section', class_='gv-Card--uDxEvPl4of_XKZDma4LM')
    removed_count = 0
    for section in age_gate_sections:
        text = section.get_text()
        if 'アダルトカテゴリに入ろうとしています' in text or '18歳未満' in text:
            section.decompose()  # Completely remove from DOM
            removed_count += 1
            print(f"Removed age gate section")

    # Also remove any divs with the age gate warning class
    age_divs = soup.find_all('div', class_='sc-3159d9f2-0')
    for div in age_divs:
        text = div.get_text()
        if 'アダルトカテゴリ' in text:
            div.decompose()
            removed_count += 1
            print(f"Removed age gate div")

    print(f"Total removed: {removed_count} age gate elements")

    # Remove all script tags to prevent age gate from being re-rendered by JavaScript
    for script in soup.find_all('script'):
        # Keep only the __NEXT_DATA__ script for reference
        if script.get('id') != '__NEXT_DATA__':
            script.decompose()

    print(f"Removed JavaScript to prevent age gate re-rendering")

    # Convert back to HTML
    html = str(soup)

    # Add a banner to indicate this is viewer mode
    banner_html = """
<style>
body::before {
    content: 'Yahoo Auction Viewer - Age Gate Removed (JavaScript Disabled)';
    display: block;
    background: #ff0033;
    color: white;
    padding: 10px;
    text-align: center;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 9999;
}
/* Hide any age gate overlays */
.sc-3159d9f2-0,
section[class*='gv-Card'] {
    display: none !important;
}
</style>
"""

    # Inject banner CSS
    html = html.replace('</head>', banner_html + '</head>')

    return html

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python yahoo_auction_viewer.py <auction_url>")
        print("\nExample:")
        print("  python yahoo_auction_viewer.py https://auctions.yahoo.co.jp/jp/auction/o1202015332")
        return

    auction_url = sys.argv[1]

    # Remove age gate
    print("\n" + "="*60)
    print("Yahoo Auction Viewer - Removing Age Gate")
    print("="*60 + "\n")

    html = remove_age_gate(auction_url)

    # Save to file
    output_file = Path("yahoo_auction_view.html")
    output_file.write_text(html, encoding='utf-8')

    print(f"\nSaved to: {output_file.absolute()}")
    print("\nOpening in browser...")

    # Open in browser
    webbrowser.open(output_file.absolute().as_uri())

    print("\n" + "="*60)
    print("Done! The original page should now be visible without the age gate.")
    print("="*60)

if __name__ == "__main__":
    main()
