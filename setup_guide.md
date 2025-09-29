# Mandarake Scraper Setup Guide

## Installation

1. **Create Virtual Environment**:
```bash
python -m venv venv
venv/Scripts/activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

## Configuration

### Basic Setup
Configure your scraping parameters in JSON files under the `configs/` directory.

### eBay API Setup (Optional)
1. Register at [eBay Developers Program](https://developer.ebay.com/)
2. Create an application to get:
   - Client ID
   - Client Secret
3. Update your config file with these credentials

### Google Services Setup (Optional)

#### Google Sheets Integration
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Create service account credentials
5. Download the JSON credentials file as `credentials.json` in the project root
6. Share your Google Sheet with the service account email

#### Google Drive Integration
1. Enable Google Drive API in the same project
2. Create a folder in Google Drive for image uploads
3. Get the folder ID from the URL (e.g., `https://drive.google.com/drive/folders/FOLDER_ID`)
4. Add folder ID to your config

## Usage

### Basic Scraping
```bash
python mandarake_scraper.py --config configs/naruto.json
```

### Scheduled Scraping
```bash
# Daily at 2:00 PM
python mandarake_scraper.py --config configs/naruto.json --schedule 14:00

# Every 30 minutes
python mandarake_scraper.py --config configs/naruto.json --interval 30
```

## Configuration Options

```json
{
  "keyword": "Search term",
  "category": "Category code (optional)",
  "shop": "Shop name (optional)",
  "client_id": "eBay client ID",
  "client_secret": "eBay client secret",
  "sheet": "Google Sheets name",
  "csv": "output.csv",
  "download_images": "images/",
  "upload_drive": true,
  "drive_folder": "Google Drive folder ID",
  "thumbnails": 400,
  "fast": false,
  "resume": true,
  "debug": false
}
```

## Features

- ✅ **Auto-pagination**: Scrapes all result pages automatically
- ✅ **Resume support**: Continues from last checkpoint if interrupted
- ✅ **Rate limiting**: Built-in delays to avoid being blocked
- ✅ **Error handling**: Robust error handling with retries
- ✅ **Multiple outputs**: CSV and Google Sheets support
- ✅ **Image processing**: Download and thumbnail creation
- ✅ **eBay integration**: Price comparison with eBay listings
- ✅ **Scheduling**: Run on schedule or intervals
- ✅ **Logging**: Comprehensive logging with daily log files

## Anti-Detection Features

- Rotating User-Agent headers
- Random delays between requests
- Session management
- Retry logic with exponential backoff
- Captcha detection and handling

## Troubleshooting

### 403 Forbidden Errors
- The site may be blocking requests. Try:
  - Increasing delays between requests
  - Using a VPN
  - Running during off-peak hours

### Google API Errors
- Ensure credentials file is properly configured
- Check API quotas and limits
- Verify service account permissions

### Memory Issues
- Large scraping jobs may use significant memory
- Consider using the `fast` mode to skip eBay lookups
- Process smaller batches if needed

## Output Format

Results are saved with the following fields:
- `title`: Product title
- `price`: Numeric price value
- `price_text`: Original price text
- `image_url`: Product image URL
- `product_url`: Link to product page
- `scraped_at`: Timestamp
- `ebay_avg_price`: Average eBay price (if enabled)
- `ebay_sold_count`: Number of sold eBay listings
- `ebay_listings`: Total eBay listings found
- `local_image`: Local image file path (if downloaded)
- `drive_image`: Google Drive image URL (if uploaded)