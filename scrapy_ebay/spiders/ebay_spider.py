import scrapy
import re
import logging
from urllib.parse import urljoin, quote
from scrapy_ebay.items import EbayItem

class EbaySpider(scrapy.Spider):
    name = 'ebay'
    allowed_domains = ['ebay.com']

    def __init__(self, query=None, max_results=5, *args, **kwargs):
        super(EbaySpider, self).__init__(*args, **kwargs)
        self.query = query or 'pokemon card'
        self.max_results = int(max_results)
        self.items_scraped = 0

        # eBay search URL
        self.search_url = 'https://www.ebay.com/sch/i.html'

    def start_requests(self):
        """Generate initial search requests"""
        if not self.query:
            self.logger.error("No search query provided")
            return

        # Build search parameters
        params = {
            '_nkw': self.query,
            '_sacat': '0',  # All categories
            'rt': 'nc',     # No category restrictions
            '_sop': '12',   # Sort by best match
            '_dmd': '1',    # Desktop mode
            'LH_ItemCondition': '3',  # Used items (often have more images)
        }

        # Construct URL
        search_url = f"{self.search_url}?{'&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])}"

        self.logger.info(f"Starting eBay search for: {self.query}")
        self.logger.info(f"Search URL: {search_url}")

        yield scrapy.Request(
            url=search_url,
            callback=self.parse_search_results,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

    def parse_search_results(self, response):
        """Parse eBay search results page"""
        self.logger.info(f"Parsing search results, status: {response.status}")

        if response.status != 200:
            self.logger.error(f"Non-200 response: {response.status}")
            return

        # Try multiple selectors for eBay items
        item_selectors = [
            '.s-item',
            '.sresult',
            '[data-testid="item"]',
            '.x-item',
            '.srp-results .s-item'
        ]

        items_found = []
        for selector in item_selectors:
            items = response.css(selector)
            if items:
                self.logger.info(f"Found {len(items)} items with selector: {selector}")
                items_found = items
                break

        if not items_found:
            self.logger.warning("No items found with any selector")
            # Try to extract any links that might be products
            all_links = response.css('a[href*="/itm/"]::attr(href)').getall()
            self.logger.info(f"Found {len(all_links)} potential product links")

            # Process first few links directly
            for link in all_links[:self.max_results]:
                if self.items_scraped >= self.max_results:
                    break
                full_url = urljoin(response.url, link)
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_item_page,
                    headers=self.get_headers()
                )
                self.items_scraped += 1
            return

        # Process found items
        for item in items_found:
            if self.items_scraped >= self.max_results:
                self.logger.info(f"Reached max results limit: {self.max_results}")
                break

            # Extract item URL
            item_url = None
            url_selectors = [
                '.s-item__link::attr(href)',
                '.vip::attr(href)',
                'a[href*="/itm/"]::attr(href)',
                'a::attr(href)'
            ]

            for url_selector in url_selectors:
                url = item.css(url_selector).get()
                if url and '/itm/' in url:
                    item_url = urljoin(response.url, url)
                    break

            if not item_url:
                continue

            # Extract basic item info from search results
            item_data = self.extract_search_item_data(item)
            item_data['item_url'] = item_url

            self.logger.info(f"Processing item: {item_data.get('title', 'No title')}")

            # Follow to item page for more details and images
            yield scrapy.Request(
                url=item_url,
                callback=self.parse_item_page,
                headers=self.get_headers(),
                meta={'item_data': item_data}
            )

            self.items_scraped += 1

    def extract_search_item_data(self, item_selector):
        """Extract basic item data from search results"""
        data = {}

        # Title
        title_selectors = [
            '.s-item__title::text',
            '.it-ttl::text',
            'h3::text',
            '.s-item__title span::text'
        ]
        for selector in title_selectors:
            title = item_selector.css(selector).get()
            if title and title.strip():
                data['title'] = title.strip()
                break

        # Price
        price_selectors = [
            '.s-item__price .notranslate::text',
            '.s-item__price::text',
            '.prc::text',
            '.u-flL::text'
        ]
        for selector in price_selectors:
            price = item_selector.css(selector).get()
            if price and '$' in price:
                data['price'] = price.strip()
                break

        # Condition
        condition_selectors = [
            '.s-item__subtitle::text',
            '.cond::text'
        ]
        for selector in condition_selectors:
            condition = item_selector.css(selector).get()
            if condition:
                data['condition'] = condition.strip()
                break

        return data

    def parse_item_page(self, response):
        """Parse individual eBay item page"""
        self.logger.info(f"Parsing item page: {response.url}")

        if response.status != 200:
            self.logger.error(f"Non-200 response for item page: {response.status}")
            return

        # Get existing item data from search results
        item_data = response.meta.get('item_data', {})

        # Create Scrapy item
        item = EbayItem()

        # Update with search results data
        for key, value in item_data.items():
            item[key] = value

        # Extract additional data from item page

        # Title (if not already extracted)
        if not item.get('title'):
            title_selectors = [
                '#x-title-label-lbl::text',
                '.x-item-title-value::text',
                'h1[id*="title"]::text',
                '.it-ttl::text'
            ]
            for selector in title_selectors:
                title = response.css(selector).get()
                if title:
                    item['title'] = title.strip()
                    break

        # Price (if not already extracted)
        if not item.get('price'):
            price_selectors = [
                '.u-flL.condText .notranslate::text',
                '.u-flL .notranslate::text',
                '#prcIsum::text',
                '.u-flL::text'
            ]
            for selector in price_selectors:
                price = response.css(selector).get()
                if price and any(c in price for c in ['$', '£', '€']):
                    item['price'] = price.strip()
                    break

        # Extract item ID from URL
        item_id_match = re.search(r'/itm/([^/\?]+)', response.url)
        if item_id_match:
            item['item_id'] = item_id_match.group(1)

        # Images - try multiple selectors
        image_urls = []
        image_selectors = [
            '#icImg::attr(src)',
            '#icImg::attr(data-src)',
            '.ux-image-carousel-item img::attr(src)',
            '.ux-image-carousel-item img::attr(data-src)',
            '#vi_main_img_fs img::attr(src)',
            '.img img::attr(src)',
            'img[id*="img"]::attr(src)',
            '.vi-image img::attr(src)'
        ]

        for selector in image_selectors:
            urls = response.css(selector).getall()
            for url in urls:
                if url and ('ebayimg.com' in url or 'i.ebayimg.com' in url):
                    # Convert to larger image size
                    if '$_' in url:
                        url = re.sub(r'\$_\d+\.JPG', '$_400.JPG', url)
                    elif url.endswith('.jpg') or url.endswith('.JPG'):
                        url = url.replace('.jpg', '$_400.JPG').replace('.JPG', '$_400.JPG')

                    if url not in image_urls:
                        image_urls.append(url)

        # Also check for thumbnail galleries
        thumbnail_selectors = [
            '.ux-image-carousel-item img::attr(src)',
            '.vi-thumbnail img::attr(src)',
            '.tdThumb img::attr(src)'
        ]

        for selector in thumbnail_selectors:
            urls = response.css(selector).getall()
            for url in urls:
                if url and ('ebayimg.com' in url or 'i.ebayimg.com' in url):
                    # Convert thumbnail to larger size
                    if '$_' in url:
                        url = re.sub(r'\$_\d+\.JPG', '$_400.JPG', url)
                    if url not in image_urls:
                        image_urls.append(url)

        # Limit to requested number of images
        if image_urls:
            item['image_urls'] = image_urls[:self.max_results]
            self.logger.info(f"Found {len(item['image_urls'])} images for item: {item.get('title', 'Unknown')}")
        else:
            self.logger.warning(f"No images found for item: {item.get('title', 'Unknown')}")
            item['image_urls'] = []

        # Additional fields
        item['item_url'] = response.url

        # Seller info
        seller_selectors = [
            '.mbg-nw::text',
            '.si-content span::text'
        ]
        for selector in seller_selectors:
            seller = response.css(selector).get()
            if seller:
                item['seller'] = seller.strip()
                break

        # Condition (if not already extracted)
        if not item.get('condition'):
            condition_selectors = [
                '#vi-condition-val::text',
                '.u-flL.condText::text'
            ]
            for selector in condition_selectors:
                condition = response.css(selector).get()
                if condition:
                    item['condition'] = condition.strip()
                    break

        # Listing type
        if response.css('.notranslate:contains("Buy It Now")').get():
            item['listing_type'] = 'Buy It Now'
        elif response.css('.notranslate:contains("Auction")').get():
            item['listing_type'] = 'Auction'
        else:
            item['listing_type'] = 'Unknown'

        yield item

    def get_headers(self):
        """Get request headers to avoid blocking"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }