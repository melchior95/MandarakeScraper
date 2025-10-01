#!/usr/bin/env python3
"""
Test the ebay-scrapy-scraper-main project without proxy
to verify selectors and basic functionality
"""
import sys
import os

# Add the ebay-scrapy-scraper-main to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ebay-scrapy-scraper-main'))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Disable ScrapeOps proxy in settings
custom_settings = {
    'SCRAPEOPS_PROXY_ENABLED': False,
    'DOWNLOADER_MIDDLEWARES': {
        'ebay_scraper.middlewares.EbayScraperDownloaderMiddleware': 543,
        'ebay_scraper.middlewares.UserAgentRotationMiddleware': 400,
        'ebay_scraper.middlewares.EbayLocationMiddleware': 350,
        'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        # Disable ScrapeOps
        # 'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': None,
    },
    'FEEDS': {
        'test_ebay_results.json': {
            'format': 'json',
            'encoding': 'utf8',
            'indent': 2,
        }
    },
    'LOG_LEVEL': 'INFO',
}

def main():
    print("=" * 60)
    print("Testing eBay Scrapy Spider (WITHOUT ScrapeOps Proxy)")
    print("=" * 60)
    print("\nNOTE: This will likely be blocked by eBay's bot detection")
    print("But it will help us verify if the spider code works correctly\n")

    # Change to ebay-scrapy-scraper-main directory
    os.chdir('ebay-scrapy-scraper-main')

    # Get settings from the project
    settings = get_project_settings()

    # Override with custom settings
    settings.update(custom_settings)

    # Create and start crawler
    process = CrawlerProcess(settings)

    process.crawl(
        'ebay_search',
        query='pokemon card',
        max_results=3
    )

    try:
        process.start()
        print("\n" + "=" * 60)
        print("Spider completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()