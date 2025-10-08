# Scrapy settings for ebay_spider project

BOT_NAME = 'ebay_spider'

SPIDER_MODULES = ['scrapy_ebay.spiders']
NEWSPIDER_MODULE = 'scrapy_ebay.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

## ========================================
## SCRAPEOPS PROXY CONFIGURATION
## ========================================
SCRAPEOPS_API_KEY = 'f3106dda-ac3c-4a67-badf-e95985d50a73'
SCRAPEOPS_PROXY_ENABLED = True

# Proxy settings
SCRAPEOPS_PROXY_SETTINGS = {
    'country': 'us',  # Use US proxies for eBay
}

# Adjust for free plan limits
CONCURRENT_REQUESTS = 1  # Free plan: 1 concurrent request
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 0  # Let ScrapeOps handle rate limiting

# User agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Enable autothrottling
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Configure middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': 725,
}

# Configure item pipelines
ITEM_PIPELINES = {
    'scrapy_ebay.pipelines.EbayImagePipeline': 300,
}

# Enable and configure the images pipeline
IMAGES_STORE = 'images'
IMAGES_EXPIRES = 90

# Configure logging
LOG_LEVEL = 'INFO'