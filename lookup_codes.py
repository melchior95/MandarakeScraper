#!/usr/bin/env python3
"""
Mandarake Code Lookup Tool
Quickly find category and store codes for building URLs
"""

import argparse
from mandarake_codes import (
    MANDARAKE_STORES,
    MANDARAKE_ALL_CATEGORIES,
    MANDARAKE_MAIN_CATEGORIES,
    get_store_name,
    get_category_name
)

def search_categories(query: str = None, main_only: bool = False):
    """Search categories by name or code"""
    categories = MANDARAKE_MAIN_CATEGORIES if main_only else MANDARAKE_ALL_CATEGORIES

    print(f"{'='*60}")
    print(f"{'MANDARAKE CATEGORIES' if not main_only else 'MAIN CATEGORIES':^60}")
    print(f"{'='*60}")
    print(f"{'Code':<8} {'English Name':<30} {'Japanese Name'}")
    print(f"{'-'*60}")

    for code, names in categories.items():
        if query:
            if (query.lower() in names['en'].lower() or
                query.lower() in names['jp'].lower() or
                query.lower() in code.lower()):
                print(f"{code:<8} {names['en']:<30} {names['jp']}")
        else:
            print(f"{code:<8} {names['en']:<30} {names['jp']}")

def search_stores(query: str = None):
    """Search stores by name or code"""
    print(f"{'='*60}")
    print(f"{'MANDARAKE STORES':^60}")
    print(f"{'='*60}")
    print(f"{'Code':<8} {'English Name':<30} {'Japanese Name'}")
    print(f"{'-'*60}")

    for code, names in MANDARAKE_STORES.items():
        if query:
            if (query.lower() in names['en'].lower() or
                query.lower() in names['jp'].lower() or
                query.lower() in code.lower()):
                print(f"{code:<8} {names['en']:<30} {names['jp']}")
        else:
            print(f"{code:<8} {names['en']:<30} {names['jp']}")

def lookup_code(code: str):
    """Lookup a specific code"""
    print(f"Looking up code: {code}")
    print(f"{'='*40}")

    # Check if it's a store code
    if code in MANDARAKE_STORES:
        store = MANDARAKE_STORES[code]
        print(f"STORE: {code}")
        print(f"English: {store['en']}")
        print(f"Japanese: {store['jp']}")
        return

    # Check if it's a category code
    if code in MANDARAKE_ALL_CATEGORIES:
        category = MANDARAKE_ALL_CATEGORIES[code]
        print(f"CATEGORY: {code}")
        print(f"English: {category['en']}")
        print(f"Japanese: {category['jp']}")
        return

    print(f"Code '{code}' not found in stores or categories")

def build_url_example(category_code: str = None, store_code: str = None, keyword: str = None):
    """Build example Mandarake URL"""
    base_url = "https://order.mandarake.co.jp/order/listPage/list?"
    params = []

    if store_code:
        params.append(f"shop={store_code}")
        store_name = get_store_name(store_code)
        print(f"Store: {store_code} ({store_name})")

    if category_code:
        params.append(f"categoryCode={category_code}")
        category_name = get_category_name(category_code)
        print(f"Category: {category_code} ({category_name})")

    if keyword:
        # URL encode the keyword
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)
        params.append(f"keyword={encoded_keyword}")
        print(f"Keyword: {keyword}")

    url = base_url + "&".join(params)
    print(f"\nGenerated URL:")
    print(f"{url}")

    return url

def main():
    parser = argparse.ArgumentParser(description='Mandarake Code Lookup Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Categories command
    cat_parser = subparsers.add_parser('categories', help='List/search categories')
    cat_parser.add_argument('--search', help='Search categories by name')
    cat_parser.add_argument('--main-only', action='store_true', help='Show only main categories')

    # Stores command
    store_parser = subparsers.add_parser('stores', help='List/search stores')
    store_parser.add_argument('--search', help='Search stores by name')

    # Lookup command
    lookup_parser = subparsers.add_parser('lookup', help='Lookup specific code')
    lookup_parser.add_argument('code', help='Code to lookup')

    # Build URL command
    url_parser = subparsers.add_parser('build-url', help='Build Mandarake URL')
    url_parser.add_argument('--category', help='Category code')
    url_parser.add_argument('--store', help='Store code')
    url_parser.add_argument('--keyword', help='Search keyword')

    args = parser.parse_args()

    if args.command == 'categories':
        search_categories(args.search, args.main_only)
    elif args.command == 'stores':
        search_stores(args.search)
    elif args.command == 'lookup':
        lookup_code(args.code)
    elif args.command == 'build-url':
        build_url_example(args.category, args.store, args.keyword)
    else:
        print("Available commands:")
        print("  categories    List/search category codes")
        print("  stores        List/search store codes")
        print("  lookup        Lookup a specific code")
        print("  build-url     Build a Mandarake URL")
        print("\nExamples:")
        print("  python lookup_codes.py categories --main-only")
        print("  python lookup_codes.py categories --search comics")
        print("  python lookup_codes.py stores")
        print("  python lookup_codes.py lookup 050801")
        print("  python lookup_codes.py build-url --category 050801 --store 0 --keyword 'Haneda Ai'")

if __name__ == '__main__':
    main()