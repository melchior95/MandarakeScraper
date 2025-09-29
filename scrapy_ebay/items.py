import scrapy

class EbayItem(scrapy.Item):
    """eBay item definition"""
    title = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    shipping = scrapy.Field()
    condition = scrapy.Field()
    item_id = scrapy.Field()
    item_url = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
    seller = scrapy.Field()
    location = scrapy.Field()
    bids = scrapy.Field()
    time_left = scrapy.Field()
    sold_count = scrapy.Field()
    watchers = scrapy.Field()
    listing_type = scrapy.Field()

    # Image comparison fields
    image_features = scrapy.Field()
    similarity_score = scrapy.Field()
    comparison_result = scrapy.Field()