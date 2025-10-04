#!/usr/bin/env python3
"""Fix old config files: update paths and rename files to use category/shop names"""

import json
import logging
import shutil
from pathlib import Path

def slugify(text):
    """Convert text to filesystem-safe slug"""
    import unicodedata
    text = str(text)

    # For non-ASCII text, transliterate or use a safe representation
    if not text.isascii():
        # Try to normalize and convert to ASCII
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        # If nothing left, use 'unicode'
        if not text or text.strip() == '':
            text = 'unicode'

    text = text.lower()
    # Replace spaces and special chars with underscores
    text = text.replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_').replace('&', 'and')
    text = text.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_')
    text = text.replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    # Remove multiple underscores
    while '__' in text:
        text = text.replace('__', '_')
    return text.strip('_')

def get_category_name(code, language='en'):
    """Get category name from code"""
    try:
        from mandarake_codes import get_category_name as get_name
        return get_name(code, language)
    except ImportError:
        return code

def get_store_name(code, language='en'):
    """Get store name from code"""
    try:
        from mandarake_codes import get_store_name as get_name
        return get_name(code, language)
    except ImportError:
        return code

def fix_config(config_path):
    """Fix a single config file"""
    try:
        print(f"\nProcessing: {config_path.name}")
    except UnicodeEncodeError:
        print(f"\nProcessing: [Unicode filename]")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Get components
    keyword = config.get('keyword', 'search')
    category_code = config.get('category', 'all')
    shop_code = config.get('shop', '0')

    # Handle list categories
    if isinstance(category_code, list):
        category_code = category_code[0] if category_code else 'all'

    # Get names
    if category_code and category_code != 'all':
        category_name = get_category_name(category_code)
        config['category_name'] = category_name
    else:
        category_name = 'all'

    if shop_code and shop_code != '0':
        shop_name = get_store_name(shop_code)
        config['shop_name'] = shop_name
    else:
        shop_name = 'All Stores'

    # Generate new filename
    keyword_slug = slugify(keyword) if keyword else 'search'
    category_slug = slugify(category_name)
    shop_slug = slugify(shop_name)

    new_json_name = f"{keyword_slug}_{category_slug}_{shop_slug}.json"
    new_csv_name = f"{keyword_slug}_{category_slug}_{shop_slug}.csv"
    new_images_folder = f"images/{keyword_slug}_{category_slug}_{shop_slug}"

    # Update config
    config['csv'] = f"results\\{new_csv_name}"
    config['download_images'] = f"{new_images_folder}/"

    # Create images folder
    Path(new_images_folder).mkdir(parents=True, exist_ok=True)

    # Save updated config
    new_json_path = Path('configs') / new_json_name
    with open(new_json_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    try:
        print(f"  Updated config saved to: {new_json_name}")
    except UnicodeEncodeError:
        print(f"  Updated config saved")

    # Rename old CSV if it exists
    old_csv = Path(config.get('csv', ''))
    if old_csv.exists() and old_csv != Path('results') / new_csv_name:
        new_csv_path = Path('results') / new_csv_name
        if not new_csv_path.exists():
            shutil.move(str(old_csv), str(new_csv_path))
            print(f"  Renamed CSV: {old_csv.name} -> {new_csv_name}")
        else:
            print(f"  CSV already exists: {new_csv_name}")

    # Move images if old download_images path exists
    old_images_dir = config.get('download_images', '')
    if old_images_dir and old_images_dir != new_images_folder + '/':
        old_images_path = Path(old_images_dir.rstrip('/'))
        if old_images_path.exists() and old_images_path.is_dir():
            new_images_path = Path(new_images_folder)
            # Move all images
            moved_count = 0
            for img_file in old_images_path.glob('*'):
                if img_file.is_file():
                    dest = new_images_path / img_file.name
                    if not dest.exists():
                        shutil.move(str(img_file), str(dest))
                        moved_count += 1
            if moved_count > 0:
                print(f"  Moved {moved_count} images to: {new_images_folder}/")

    # Delete old config if it has a different name
    if config_path != new_json_path and config_path.exists():
        config_path.unlink()
        try:
            print(f"  Deleted old config: {config_path.name}")
        except UnicodeEncodeError:
            print(f"  Deleted old config")

    return new_json_name

def main():
    """Fix all config files"""
    print("=" * 60)
    print("FIXING OLD CONFIG FILES")
    print("=" * 60)

    configs_dir = Path('configs')
    config_files = list(configs_dir.glob('*.json'))

    print(f"\nFound {len(config_files)} config files to process")

    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)

    for config_file in config_files:
        try:
            fix_config(config_file)
        except Exception as e:
            try:
                print(f"  ERROR processing {config_file.name}: {e}")
            except UnicodeEncodeError:
                print(f"  ERROR processing file: {e}")

    print("\n" + "=" * 60)
    print("DONE! All configs have been updated.")
    print("=" * 60)

if __name__ == '__main__':
    main()
