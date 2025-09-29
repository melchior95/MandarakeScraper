# Sold Listing Image Matcher

## Overview

The Sold Listing Image Matcher is an automated system that finds sold eBay listings, compares product images using computer vision, and provides market pricing analysis. It runs completely in the background using headless browser automation.

## Key Features

### 🔍 **Intelligent Search**
- Uses lazy search optimization for better eBay search results
- Automatically searches for "sold" listings only
- Handles Japanese product names and complex search terms

### 🤖 **Headless Automation**
- Runs completely invisible to the user
- Uses Playwright for robust browser automation
- Bypasses eBay's anti-bot detection measures
- Stealth browsing with realistic user agent and headers

### 🖼️ **Computer Vision Matching**
- Downloads images from sold listings automatically
- Uses ORB (Oriented FAST and Rotated BRIEF) feature detection
- Compares visual similarity between your product and sold items
- Fallback to histogram comparison for difficult images

### 💰 **Market Analysis**
- Calculates average sold prices
- Provides price ranges (min/max)
- Generates pricing recommendations
- Currency conversion estimates (JPY to USD)

### 📊 **Confidence Scoring**
- Multi-factor confidence rating
- Considers image similarity, sale recency, price reasonableness
- Reliability indicators for decision making

## Files Created

1. **`sold_listing_matcher.py`** - Core image matching engine
2. **`price_validation_service.py`** - Integration service for the main scraper
3. **`test_sold_matching.py`** - Test script and demonstration

## Usage Examples

### Direct Image Matching
```python
from sold_listing_matcher import match_product_with_sold_listings

result = await match_product_with_sold_listings(
    reference_image_path="product.jpg",
    search_term="Yura Kano photobook",
    headless=True,
    max_results=5
)

print(f"Found {result.matches_found} matches")
print(f"Average price: ${result.average_price:.2f}")
```

### Price Validation Service
```python
from price_validation_service import PriceValidationService

config = {
    'price_validation': {
        'enabled': True,
        'headless': True,
        'similarity_threshold': 0.7,
        'max_results': 5
    }
}

async with PriceValidationService(config) as validator:
    result = await validator.validate_product_price(product_data, image_path)
```

### Testing the System
```bash
# Test with your own image and search term
python test_sold_matching.py product.jpg "Yura Kano photobook"

# View system overview
python test_sold_matching.py
```

## Configuration Options

### Price Validation Settings
```json
{
  "price_validation": {
    "enabled": false,           // Enable/disable the service
    "headless": true,           // Run browser invisibly
    "similarity_threshold": 0.7, // Image match threshold (0-1)
    "max_results": 5,           // Max sold listings to analyze
    "days_back": 90,            // How far back to search (days)
    "batch_delay": 2.0          // Delay between requests (seconds)
  }
}
```

## How It Works

### 1. Search Optimization
- Takes your search term (e.g., "Yura Kano photobook")
- Uses the search optimizer to create better eBay search queries
- Adds "sold" to specifically target completed listings

### 2. Browser Automation
- Opens eBay in a headless Chrome browser (completely invisible)
- Navigates to sold listings search results
- Extracts listing data (title, price, image URL, sold date)

### 3. Image Processing
- Downloads images from sold listings
- Extracts visual features using OpenCV
- Compares your product image with each sold listing image
- Calculates similarity scores

### 4. Match Analysis
- Filters results above similarity threshold
- Ranks matches by image similarity and confidence factors
- Calculates market statistics and pricing recommendations

### 5. Results
- Returns structured data with matches, prices, and analysis
- Provides actionable pricing recommendations
- Includes confidence levels for decision making

## Integration with Main Scraper

The system integrates seamlessly with the existing Mandarake scraper:

```python
# Add to your scraper configuration
config = add_price_validation_to_config(config)

# Validate scraped products
validated_products = await validate_scraped_products(
    products=scraped_products,
    config=config,
    image_directory="./images"
)
```

## Technical Details

### Dependencies
- **Playwright**: Headless browser automation
- **OpenCV**: Computer vision and image processing
- **NumPy**: Numerical computing for image analysis
- **Pillow**: Image loading and manipulation
- **Requests**: HTTP client for image downloads

### Image Matching Algorithm
1. **Feature Extraction**: Uses ORB detector to find keypoints and descriptors
2. **Feature Matching**: Brute force matching with Hamming distance
3. **Similarity Calculation**: Ratio of good matches to total features
4. **Fallback Method**: Histogram comparison for images with few features

### Performance Optimizations
- Image caching to avoid re-downloading
- Standardized image sizes for consistent comparison
- Asynchronous processing for multiple listings
- Respectful delays between requests

## Security & Ethics

- **Rate Limiting**: Built-in delays to respect eBay's servers
- **Stealth Browsing**: Realistic headers and user agent strings
- **No Data Storage**: Only processes data, doesn't store personal information
- **Respectful Scraping**: Follows best practices for web scraping

## Results Interpretation

### Confidence Levels
- **High**: 3+ matches with good similarity scores
- **Medium**: 2 matches with decent similarity
- **Low**: 1 match or poor similarity scores

### Price Recommendations
- **Overpriced**: >20% above market average
- **Slightly Overpriced**: 10-20% above average
- **Fairly Priced**: Within ±10% of market average
- **Slightly Underpriced**: 10-20% below average
- **Underpriced**: >20% below market average

## Troubleshooting

### Common Issues
1. **No matches found**: Try lowering similarity threshold or broader search terms
2. **Browser errors**: Install Playwright browsers: `playwright install chromium`
3. **Image processing errors**: Ensure OpenCV is properly installed
4. **eBay blocking**: System includes anti-detection, but may need user agent updates

### Debug Mode
Set `headless=False` to watch the browser in action during development.

## Future Enhancements

- Support for multiple marketplaces (Yahoo Auctions, Mercari)
- Machine learning for better image matching
- Historical price tracking
- Automated alerts for price changes
- Integration with Google Sheets for reporting