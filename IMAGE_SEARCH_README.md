# eBay Image Search for Sold Listings - User Guide

This implementation provides comprehensive image-based market analysis for finding sold listings on eBay. Upload an image of a product and get detailed pricing analysis, profit calculations, and market recommendations.

## 🎯 Overview

The system offers three main approaches to image-based market research:

1. **Direct eBay Image Search** - Upload image directly to eBay's image search, then analyze sold listings
2. **Google Lens + eBay Search** - Use Google Lens to identify product names, then search eBay sold listings by text
3. **Hybrid Analysis** - Combine multiple methods for comprehensive results

## 🚀 Quick Start

### Using the GUI

1. Open the Mandarake Scraper GUI
2. Go to the **"eBay Analysis"** tab
3. In the **"Image Search"** section:
   - Click **"Select Image..."** to upload your product image
   - Choose your search method (Direct eBay or Google Lens)
   - Select image enhancement level (light/medium/aggressive)
   - **Enable "Lazy Search"** for intelligent keyword optimization
   - **Enable "AI Search Confirmation"** for automated result validation
   - Click **"Search by Image"** for single method or **"AI Smart Search"** for comprehensive analysis
4. Review results in the analysis table with profit calculations

### Command Line Usage

#### Quick Analysis (Direct eBay search)
```bash
python image_analysis_engine.py "path/to/product_image.jpg"
```

#### Thorough Analysis (Multiple methods)
```bash
python image_analysis_engine.py "path/to/product_image.jpg" --thorough --save-report
```

#### Individual Module Testing
```bash
# Test direct eBay image search
python ebay_image_search.py "image.jpg" --sold

# Test Google Lens identification
python google_lens_search.py "image.jpg" --identify-only

# Test image preprocessing
python image_processor.py "image.jpg" --variants
```

## 📋 Features

### Image Processing & Enhancement
- **Automatic optimization** for better search results
- **Multiple enhancement levels**: Light, Medium, Aggressive
- **Smart cropping** to focus on main subject
- **Background removal** for cleaner searches
- **Text enhancement** for items with readable labels

### Search Methods

#### 1. Direct eBay Image Search
- Uses eBay's visual search technology
- Automatically filters for sold listings only
- Parses price data and sale information
- **Lazy Search**: Optimizes keywords if image search yields poor results
- Best for: Clear product photos, branded items

#### 2. Google Lens + eBay Text Search
- Identifies product names using Google's AI
- Searches eBay using identified text terms
- **Lazy Search**: Generates multiple keyword variations for better matching
- Better for complex or unusual items
- Best for: Unique items, collectibles, vintage products

#### 3. Hybrid Analysis
- Runs both methods and compares results
- Uses the method that finds more sold listings
- Provides comprehensive market coverage
- Best for: When you want maximum confidence

#### 4. AI Smart Search 🆕
- **Intelligent search optimization** with lazy keyword matching
- **AI confirmation** automatically selects best results from multiple attempts
- Tries multiple enhancement levels and search methods
- **Smart result scoring** based on price consistency, item count, and confidence
- Best for: Maximum accuracy and automated result validation

### Market Analysis

#### Profit Scenarios
The system generates three profit scenarios:

1. **Conservative (30% of eBay price)**
   - Low risk, higher profit margins
   - Suitable for guaranteed profits

2. **Moderate (50% of eBay price)**
   - Balanced risk/reward
   - Good for established markets

3. **Aggressive (70% of eBay price)**
   - Higher risk, lower margins
   - Suitable for high-volume trading

#### Price Analysis
- **Median price** - Most reliable price indicator
- **Average price** - Overall market average
- **Price range** - Shows market volatility
- **Sold count** - Indicates market demand

## 🔧 Configuration

### GUI Settings
- **Min sold items**: Minimum number of sold listings required (default: 3)
- **Search days back**: How far back to search (default: 90 days)
- **Min profit margin**: Minimum profit percentage to display (default: 20%)
- **USD/JPY rate**: Exchange rate for calculations (default: 150)

### Image Enhancement Levels

#### Light Enhancement
- Basic resize and sharpening
- Minimal processing time
- Good for clear, high-quality images

#### Medium Enhancement (Recommended)
- Color and contrast optimization
- Smart sharpening
- Brightness adjustment
- Best balance of quality and speed

#### Aggressive Enhancement
- Advanced noise reduction
- CLAHE contrast enhancement
- Background optimization
- Best for low-quality or difficult images

## 📊 Understanding Results

### GUI Results Table
| Column | Description |
|--------|-------------|
| Item Title | Product name or search term used |
| Mandarake (¥) | Estimated purchase price in Japanese Yen |
| Sold Count | Number of sold listings found |
| Median ($) | Median selling price in USD |
| Price Range ($) | Min-Max price range |
| Profit % | Estimated profit margin |
| Est. Profit ($) | Estimated profit in USD |

### Profit Calculation Formula
```
Net Proceeds = eBay Price - (eBay Fees + Shipping)
Profit Margin = ((Net Proceeds - Purchase Cost) / Purchase Cost) × 100
```

Where:
- eBay Fees = 13% (eBay + PayPal fees)
- Shipping = $5.00 (estimated)

## 🎯 Best Practices

### Image Quality Tips
1. **Use high-resolution images** (but will be auto-resized)
2. **Ensure good lighting** and clear product visibility
3. **Include product packaging** when relevant
4. **Avoid cluttered backgrounds** when possible
5. **Show any text/labels** clearly

### Search Strategy
1. **Start with medium enhancement** for most images
2. **Try both search methods** for important items
3. **Use aggressive enhancement** for blurry/old photos
4. **Check multiple crop variants** for complex images

### Market Research Tips
1. **Require minimum 5 sold listings** for confidence
2. **Look for stable price ranges** (low variation)
3. **Consider seasonality** in your analysis
4. **Factor in item condition** differences
5. **Account for authentication costs** on high-value items

## 🔍 Troubleshooting

### Common Issues

#### "No sold listings found"
- Try different enhancement levels
- Use Google Lens method instead of direct search
- Check if item is too new/rare for sold data
- Verify image shows the product clearly

#### "Image analysis failed"
- Ensure image file is not corrupted
- Check internet connection for online searches
- Try with a smaller/simpler image
- Check if Playwright is properly installed

#### Poor search results
- Use aggressive enhancement for low-quality images
- Try cropping to focus on the main product
- Remove backgrounds that might confuse search
- Use multiple search methods for comparison

### Error Messages

| Error | Solution |
|-------|----------|
| "Please select an image file first" | Use "Select Image..." button to choose a file |
| "eBay API not configured" | Check eBay credentials in Advanced tab |
| "Image processing failed" | Try with a different image format |
| "No product identification results" | Image may not contain identifiable products |

## 📁 File Structure

```
mandarake_scraper/
├── ebay_image_search.py          # Direct eBay image search
├── google_lens_search.py         # Google Lens product identification
├── image_processor.py            # Image enhancement and optimization
├── image_analysis_engine.py      # Comprehensive analysis engine
├── gui_config.py                 # GUI integration (eBay Analysis tab)
└── analysis_reports/             # Generated analysis reports
    ├── analysis_YYYYMMDD_HHMMSS.json
    └── profit_scenarios_YYYYMMDD_HHMMSS.csv
```

## 🛠️ Dependencies

Required Python packages (automatically installed):
- `playwright` - Web automation for eBay search
- `beautifulsoup4` - HTML parsing
- `pillow` - Image processing
- `opencv-python` - Advanced image enhancement
- `numpy` - Image array processing

## 📈 Advanced Usage

### Batch Analysis
```python
from image_analysis_engine import ImageAnalysisEngine

engine = ImageAnalysisEngine({'usd_jpy_rate': 145})
images = ['image1.jpg', 'image2.jpg', 'image3.jpg']

for image_path in images:
    result = engine.analyze_image_comprehensive(image_path)
    summary = engine.get_analysis_summary(result)
    print(summary)
    engine.save_analysis_report(result)
```

### Custom Configuration
```python
config = {
    'usd_jpy_rate': 140,
    'min_profit_margin': 25,
    'ebay_fees_percent': 0.13,
    'shipping_cost': 7.0
}

engine = ImageAnalysisEngine(config)
result = engine.analyze_image_comprehensive('product.jpg')
```

## 🧠 Lazy Search Technology

### What is Lazy Search?
Lazy Search is an intelligent search optimization system that improves eBay matching by:

1. **Keyword Extraction**: Identifies the most important terms from product descriptions
2. **Text Simplification**: Removes unnecessary words that might confuse search algorithms
3. **Romanization Variants**: Handles different spellings of Japanese names (e.g., "Yura Kano" vs "Yuraka no")
4. **Progressive Search Strategy**: Tries multiple search term combinations, from specific to general
5. **Automatic Fallback**: Switches to optimized text search if image search yields poor results

### When Lazy Search Activates
- **Poor Image Results**: When direct image search finds fewer than 3 sold items
- **Google Lens Mode**: Automatically optimizes identified product names
- **AI Smart Search**: Uses lazy search for all methods to ensure comprehensive coverage

### Search Term Optimization Examples
| Original Term | Lazy Search Variations |
|---------------|----------------------|
| "Yura Kano Photo Book Collection Majikano Japanese Gravure Model" | "Yura Kano", "photo book", "Yura Kano photo", "gravure model" |
| "Premium Nude POSE BOOK Act Yura Kano Posing Art Book Photo Japan JAV" | "Yura Kano", "pose book", "art book", "japan photo" |
| "Visual Nude Pose Book act Yura Kano How to Draw Posing Art Japan Import" | "Yura Kano", "pose book", "visual nude", "art japan" |

## 🎯 Tips for Success

1. **Start with clear product photos** from Mandarake listings
2. **Use AI Smart Search** for the most accurate results
3. **Enable both Lazy Search and AI Confirmation** for optimal matching
4. **Try different enhancement levels** if results are poor
5. **Cross-reference with multiple images** of the same product
6. **Consider item condition differences** between markets
7. **Factor in authentication needs** for expensive collectibles
8. **Use analysis reports** to track successful strategies

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the console output for detailed error messages
3. Test with different images to isolate problems
4. Verify all dependencies are properly installed

---

**Note**: This tool is for research purposes. Always verify market prices independently and consider all costs (including time, packaging, insurance) when making purchasing decisions.