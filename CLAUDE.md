# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Mandarake scraper that extracts product listings from order.mandarake.co.jp, compares them with eBay prices via API, and exports results to Google Sheets with image integration via Google Drive.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Running the Scraper
```bash
python mandarake_scraper.py --config configs/naruto.json
```

## Architecture

### Core Components
- **mandarake_scraper.py**: Main scraper logic (currently placeholder - needs full implementation)
- **configs/**: JSON configuration files for different scraping scenarios
- **Google Services Integration**: Uses gspread + Google Drive API for data export
- **eBay API Integration**: Price comparison functionality

### Configuration System
The scraper uses JSON config files in the `configs/` directory. Each config defines:
- Search parameters (keyword, category, shop)
- eBay API credentials (client_id, client_secret)
- Output settings (Google Sheets, CSV, image handling)
- Scraping behavior (resume, fast mode, thumbnails)

### Key Features (Planned/In Development)
- Auto-pagination across all result pages
- Resume support with state files for interrupted scrapes
- Scheduler for interval or daily execution
- Checkpointing after each page
- Image download and Google Drive upload
- eBay price comparison integration

## Dependencies

Core libraries:
- **requests**: HTTP client for web scraping
- **beautifulsoup4**: HTML parsing
- **gspread**: Google Sheets API integration
- **google-api-python-client**: Google Drive integration
- **pillow**: Image processing
- **tqdm**: Progress bars
- **schedule**: Task scheduling

## Configuration Notes

- eBay API credentials must be configured in config files
- Google Drive folder IDs need to be set for image uploads
- The scraper supports both Google Sheets and CSV output formats
- Resume functionality allows interrupted scrapes to continue from last checkpoint

## Testing Commands

### Basic Testing
```bash
python mandarake_scraper.py --help
python mandarake_scraper.py --config configs/naruto.json
```

### Dependencies Installation
```bash
pip install -r requirements.txt
```

## Current Status

The scraper is fully implemented with all planned features:
- ✅ Complete scraper implementation with anti-detection measures
- ✅ Auto-pagination and resume functionality
- ✅ eBay API integration for price comparison
- ✅ Google Sheets and Drive integration
- ✅ Image download and processing
- ✅ Scheduler for automated runs
- ✅ Comprehensive logging and error handling
- ✅ Command-line interface with config support

**Note**: The scraper may encounter 403 errors due to Mandarake's anti-bot protection. The implementation includes retry logic and rate limiting to handle this.

## Known Issues

- Mandarake implements bot detection that may block requests
- CSS selectors may need adjustment based on actual HTML structure
- Google API credentials required for Sheets/Drive functionality