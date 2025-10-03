from bs4 import BeautifulSoup

with open('debug_ebay_response.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Check for .srp-river-results
river = soup.select_one('.srp-river-results')
if river:
    print("Found .srp-river-results container")
    lis = river.find_all('li', limit=10)
    print(f"Found {len(lis)} <li> tags inside .srp-river-results")
    print("\nFirst 10 <li> tags:")
    for i, li in enumerate(lis, 1):
        classes = li.get('class', [])
        item_id = li.get('id', '')
        data_view = li.get('data-view', '')
        print(f"  {i}. Classes: {classes}, ID: {item_id}, data-view: {data_view}")

        # Check for title
        title_elem = li.select_one('.s-item__title')
        if not title_elem:
            title_elem = li.select_one('[class*="title"]')
        if title_elem:
            print(f"     Title element class: {title_elem.get('class', [])}")
else:
    print("ERROR: .srp-river-results not found")

# Look for any divs with item-related classes
print("\n\nSearching for item containers...")
for selector in ['[class*="item"]', '[data-view]', '[class*="listing"]']:
    items = soup.select(selector)[:5]
    if items:
        print(f"\nFound {len(items)} elements with selector '{selector}'")
        for item in items[:3]:
            print(f"  Classes: {item.get('class', [])}, Tag: {item.name}")
