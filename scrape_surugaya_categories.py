"""
Scrape Suruga-ya book categories from the website
"""
import requests
from bs4 import BeautifulSoup
import json

url = "https://www.suruga-ya.jp/search?category1=7"

print(f"Fetching {url}...")
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Save HTML for inspection
with open('surugaya_books_debug.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

# Find category links/selects
categories = {}

# Look for category dropdowns or links
category_selects = soup.find_all('select', {'name': 'category2'})
if category_selects:
    for select in category_selects:
        options = select.find_all('option')
        for option in options:
            value = option.get('value', '')
            text = option.get_text(strip=True)
            if value and text:
                categories[value] = text
                print(f"Found: {value} = {text}")

# Look for category links in the page
category_links = soup.find_all('a', href=lambda x: x and 'category2=' in str(x))
for link in category_links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    # Extract category2 value from URL
    if 'category2=' in href:
        import re
        match = re.search(r'category2=([^&]+)', href)
        if match:
            value = match.group(1)
            if value and text:
                categories[value] = text
                print(f"Found link: {value} = {text}")

# Save to JSON
output = {
    "7": {  # Books main category
        "name": "本・雑誌・コミック",
        "subcategories": categories
    }
}

with open('surugaya_book_categories.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nFound {len(categories)} book subcategories")
print(f"Saved to surugaya_book_categories.json")
