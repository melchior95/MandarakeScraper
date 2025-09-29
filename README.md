# Mandarake Scraper

Toolkit for scraping Mandarake listings, enriching them with eBay pricing, and exporting results to CSV/Google Sheets.

## Prerequisites
- Python 3.10+
- Mandarake credentials are not required; the scraper mimics browser access.
- Google service-account JSON (if uploading to Sheets/Drive)
- eBay developer keys (optional, for price comparisons)

## Setup
```bash
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

## Configuration
Create JSON configs in `configs/`. Example:
```json
{
  "keyword": "Naruto",
  "category": "30",
  "shop": "nakano",
  "hide_sold_out": false,
  "recent_hours": 24,
  "max_pages": 5,
  "client_id": "YOUR_EBAY_CLIENT_ID",
  "client_secret": "YOUR_EBAY_CLIENT_SECRET",
  "mimic": false,
  "google_sheets": {
    "sheet_name": "Mandarake Results",
    "worksheet_name": "Sheet1"
  },
  "upload_sheets": true,
  "csv": "results/naruto_nakano.csv",
  "download_images": "images/naruto/",
  "upload_drive": true,
  "drive_folder": "YOUR_DRIVE_FOLDER_ID",
  "thumbnails": 400,
  "fast": false,
  "resume": true,
  "debug": false
}
```

### Key Options
- `keyword`: Mandarake search term (required).
- `category`: Code or list of codes; omit for all categories.
- `shop`: Store code/slug/list; see `MANDARAKE_CODES.md`.
- `hide_sold_out`: Adds `soldOut=1` to hide unavailable items.
- `recent_hours`: Only items uploaded in the last N hours (maps to `upToMinutes`).
- `max_pages`: Maximum pages to scrape per category/shop.
- `upload_sheets`: Toggle Google Sheets export.
- `upload_drive`: Upload downloaded images to Drive.
- `fast`: Skip eBay enrichment.
- `resume`: Persist checkpoints.
- `debug`: Verbose logging.

## Running from CLI
```bash
python mandarake_scraper.py --config configs/naruto.json
```
Schedule or interval runs:
```bash
python mandarake_scraper.py --config configs/naruto.json --schedule 14:00
python mandarake_scraper.py --config configs/naruto.json --interval 30
```
Direct Mandarake URL:
```bash
python mandarake_scraper.py --url "https://order.mandarake.co.jp/order/ListPage/list?keyword=pokemon&shop=1"
```

## GUI Configurator (`gui_config.py`)
Run `python gui_config.py` for a Tkinter-based workflow:
- Compose configs with dropdowns for shops, main & detailed categories, max pages, and recent-hours filters.
- Manage outputs: CSV/Drive, toggle Google Sheets upload, set thumbnail size.
- Live preview of the Mandarake search URL.
- Config browser (double-click to load) sourced from `configs/`.
- Auto-named configs (`keyword_category_shop.json`) saved to `configs/`; CSVs mirror the name in `results/`.
- Latest run results (title, price, shop, stock, category, clickable product link) shown in the Output tab.
- `Run Now`/`Schedule` auto-save the config before executing.

## Outputs
- CSV files in `results/` (auto-named from config).
- Optional Google Sheets (service account) and Drive image uploads.
- Logs per run (`mandarake_scraper_YYYYMMDD.log`).

## Troubleshooting
- **403 / Captcha**: slow the crawl, use VPN, or try off-peak hours.
- **Google quota errors**: verify credentials, folder permissions, and quotas.
- **eBay 403**: ensure Browse API scope is enabled; check credentials.
- **Empty results**: verify keyword/category/shop codes; use GUI preview to inspect URL.

## References
- `MANDARAKE_CODES.md`: Comprehensive store/category code tables.
- `result_limiter.py`: Utility to profile Mandarake pagination selectors.
- `enhanced_mandarake_scraper.py`: Browser-mimicking sampler with page/item limits.
