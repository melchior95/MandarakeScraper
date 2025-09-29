import os
import requests
import logging
from urllib.parse import urlparse
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem
from scrapy import Request

class EbayImagePipeline(ImagesPipeline):
    """Custom image pipeline for eBay items"""

    def get_media_requests(self, item, info):
        """Download images for the item"""
        if 'image_urls' in item and item['image_urls']:
            for image_url in item['image_urls'][:5]:  # Limit to 5 images
                if image_url:
                    yield Request(image_url, meta={'item': item})

    def item_completed(self, results, item, info):
        """Process completed image downloads"""
        image_paths = []

        for ok, x in results:
            if ok:
                image_paths.append(x['path'])
            else:
                logging.warning(f"Failed to download image: {x}")

        if image_paths:
            item['images'] = image_paths
        else:
            logging.warning(f"No images downloaded for item: {item.get('title', 'Unknown')}")

        return item

class EbayDataCleaningPipeline:
    """Clean and process eBay item data"""

    def process_item(self, item, spider):
        # Clean price
        if 'price' in item and item['price']:
            price = item['price'].strip()
            # Remove currency symbols and extract numbers
            import re
            price_match = re.search(r'[\d,]+\.?\d*', price)
            if price_match:
                item['price'] = price_match.group().replace(',', '')
            else:
                item['price'] = '0'

        # Clean title
        if 'title' in item and item['title']:
            item['title'] = ' '.join(item['title'].split())

        # Clean condition
        if 'condition' in item and item['condition']:
            item['condition'] = item['condition'].strip()

        return item