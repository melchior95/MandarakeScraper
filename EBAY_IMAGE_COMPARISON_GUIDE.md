# eBay Image Comparison - User Guide

## How to Use the New eBay Image Comparison Feature

### 🚀 Quick Start

1. **Open the GUI**: Run `python gui_config.py`
2. **Go to eBay Analysis Tab**: Click on the "eBay Analysis" tab
3. **Upload an Image**: Click "Select Image..." and choose your product image
4. **Configure Settings** (optional): Adjust the "Image Match" percentage (50-90%)
5. **Start Comparison**: Click "eBay Image Comparison" button
6. **Enter Search Term**: Type in what to search for (e.g., "Yura Kano photobook")
7. **Wait for Results**: The system runs completely in the background

### 🎯 What It Does

The eBay Image Comparison feature:

- **Searches eBay** for sold listings matching your search term
- **Downloads images** from the top sold listings automatically
- **Compares your image** with sold listing images using computer vision
- **Finds visual matches** above your similarity threshold
- **Shows pricing data** from matched sold items
- **Runs completely headless** - you won't see any browser windows

### ⚙️ Configuration Options

#### Image Match Threshold
- **50%**: Very loose matching (finds more results, less accurate)
- **60%**: Loose matching (good for similar products)
- **70%**: Default balanced matching (recommended for most cases)
- **80%**: Strict matching (very similar images only)
- **90%**: Very strict matching (nearly identical images)

#### Other Settings
- **Days Back**: How far back to search for sold items (default: 90 days)
- **Lazy Search**: Optimizes search terms for better eBay results

### 📊 Understanding Results

The results table shows:

- **Title**: The sold listing title
- **Search**: Your search term
- **eBay Sold Count**: "1 (matched)" for each visual match
- **eBay Median Price**: The sold price from that listing
- **eBay Price Range**: Shows image similarity percentage
- **Profit Margin**: Shows when the item was sold
- **Estimated Profit**: Shows confidence score

#### Summary Row (when multiple matches found)
- **🎯 SUMMARY**: Overview of all matches
- **Average Price**: Average of all matched sold prices
- **Price Range**: Lowest to highest matched price
- **Confidence**: Overall confidence level (high/medium/low)
- **Best Match**: Highest similarity percentage found

### 💡 Tips for Best Results

#### Good Search Terms:
- ✅ "Yura Kano photobook"
- ✅ "Pokemon card Charizard"
- ✅ "Nintendo Switch console"
- ✅ "Sailor Moon figure"

#### Avoid These:
- ❌ Too generic: "book", "card", "game"
- ❌ Too specific: "Yura Kano Magical Girlfriend Limited Edition Photo Book Collection Vol 1"
- ❌ Japanese-only terms that don't exist on eBay

#### Image Quality:
- ✅ Clear, well-lit product photos
- ✅ Product fills most of the frame
- ✅ Minimal background distractions
- ❌ Blurry or dark images
- ❌ Multiple products in one image
- ❌ Heavy text overlays

### 🔍 Troubleshooting

#### "No visual matches found"
- Try lowering the Image Match threshold to 50-60%
- Use a broader search term
- Make sure your image shows the product clearly
- The product might not have been sold recently on eBay

#### "eBay image comparison failed"
- Check your internet connection
- Make sure the image file exists and isn't corrupted
- Try again - eBay sometimes blocks automated requests temporarily

#### Search takes a long time
- This is normal! The system needs to:
  1. Search eBay for sold listings
  2. Download images from each listing
  3. Analyze each image with computer vision
  4. Calculate similarity scores
- Usually takes 30-60 seconds for 5 listings

#### Browser detection/blocking
- The system runs headless to avoid detection
- If blocked repeatedly, wait a few minutes before trying again
- eBay has strong anti-automation measures

### 🎨 Example Workflow

1. **You have**: A photo of a Yura Kano photobook
2. **You search**: "Yura Kano photobook"
3. **System finds**: 3 sold listings on eBay
4. **Downloads images**: From those 3 listings
5. **Compares images**: Your photo vs. the 3 downloaded images
6. **Finds matches**: 2 out of 3 are visually similar (above threshold)
7. **Shows results**:
   - Summary: 2 matches, average $45, range $40-50
   - Match 1: 85% similar, sold for $47 last week
   - Match 2: 73% similar, sold for $43 two weeks ago

### 🚀 Advanced Usage

#### Integration with Other Features
- Use with **Lazy Search** enabled for better search optimization
- Combine with **Research & Optimize** to build keyword profiles
- Export results to CSV for price tracking

#### Batch Analysis
- Currently single-image only
- For multiple products, run each one separately
- Results can be exported and combined in spreadsheet

### 🔧 Technical Notes

- Uses OpenCV computer vision library
- ORB (Oriented FAST and Rotated BRIEF) feature detection
- Playwright for headless browser automation
- Searches eBay sold listings specifically (not active listings)
- Results are actual sold prices, not asking prices

This feature provides real market data by finding visually similar products that actually sold on eBay, giving you accurate pricing information based on what buyers actually paid!