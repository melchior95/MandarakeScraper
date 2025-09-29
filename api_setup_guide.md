# Google & eBay API Setup Guide

## Google APIs Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" or select existing project
3. Give your project a name (e.g., "Mandarake Scraper")
4. Click "Create"

### Step 2: Enable Required APIs

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for and enable these APIs:
   - **Google Sheets API**
   - **Google Drive API**

### Step 3: Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in details:
   - Service account name: `mandarake-scraper`
   - Service account ID: (auto-generated)
   - Description: `Service account for Mandarake scraper`
4. Click "Create and Continue"
5. Skip roles for now, click "Continue"
6. Click "Done"

### Step 4: Generate Credentials File

1. In the Credentials page, find your service account
2. Click on the service account email
3. Go to the "Keys" tab
4. Click "Add Key" > "Create new key"
5. Select "JSON" format
6. Click "Create"
7. Download the JSON file
8. **Rename it to `credentials.json`** and place it in your project root directory

### Step 5: Setup Google Sheets

1. Create a new Google Sheet or use existing one
2. Get the service account email from your `credentials.json` file (looks like: `mandarake-scraper@your-project.iam.gserviceaccount.com`)
3. Share your Google Sheet with this email address:
   - Click "Share" in Google Sheets
   - Add the service account email
   - Give it "Editor" permissions
   - Uncheck "Notify people"
4. Note the sheet name for your config file

### Step 6: Setup Google Drive (Optional)

1. Create a folder in Google Drive for images
2. Share the folder with your service account email (same as above)
3. Get the folder ID from the URL:
   - Open the folder in Google Drive
   - Copy the folder ID from URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. Use this folder ID in your config file

## eBay API Setup

### Step 1: Create eBay Developer Account

1. Go to [eBay Developers Program](https://developer.ebay.com/)
2. Sign in with your eBay account (create one if needed)
3. Click "Get Started" or "Create Account"

### Step 2: Create Application

1. Go to [My Account](https://developer.ebay.com/my/keys) in eBay Developers
2. Click "Create an App"
3. Fill in application details:
   - **Application Title**: `Mandarake Price Checker`
   - **Application Type**: Choose your preference
   - **Application Purpose**: `Price comparison and market research`
   - **Platform**: `Web`
4. Accept terms and click "Create"

### Step 3: Get API Credentials

1. After creating the app, you'll see your credentials:
   - **App ID (Client ID)**: Copy this
   - **Dev ID**: Not needed for this project
   - **Cert ID (Client Secret)**: Copy this
2. **Important**: These are your sandbox credentials for testing

### Step 4: Production Credentials (Optional)

For production use:
1. Go through eBay's verification process
2. Submit your application for production approval
3. Once approved, you'll get production credentials

## Configuration Setup

### Update your config file (e.g., `configs/naruto.json`):

```json
{
  "keyword": "Naruto",
  "category": "30",
  "shop": "nakano",
  "client_id": "YOUR_EBAY_CLIENT_ID_HERE",
  "client_secret": "YOUR_EBAY_CLIENT_SECRET_HERE",
  "sheet": "Mandarake Results",
  "csv": "naruto_results.csv",
  "download_images": "images/",
  "upload_drive": true,
  "drive_folder": "YOUR_DRIVE_FOLDER_ID_HERE",
  "thumbnails": 400,
  "fast": false,
  "resume": true
}
```

### File Structure After Setup:

```
mandarake_scraper/
├── credentials.json          # Google service account credentials
├── configs/
│   └── naruto.json          # Updated with your API credentials
├── mandarake_scraper.py
├── requirements.txt
└── ...
```

## Testing Your Setup

### Test Google Sheets Integration:

```bash
python -c "
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Try to open a sheet (replace with your sheet name)
sheet = client.open('Mandarake Results').sheet1
print('Google Sheets connection successful!')
"
```

### Test eBay API:

```bash
python -c "
import requests
import base64

client_id = 'YOUR_CLIENT_ID'
client_secret = 'YOUR_CLIENT_SECRET'

# Test authentication
credentials = f'{client_id}:{client_secret}'
encoded = base64.b64encode(credentials.encode()).decode()

response = requests.post(
    'https://api.sandbox.ebay.com/identity/v1/oauth2/token',
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded}'
    },
    data={
        'grant_type': 'client_credentials',
        'scope': 'https://api.ebayapis.com/oauth/api_scope'
    }
)

if response.status_code == 200:
    print('eBay API connection successful!')
else:
    print(f'eBay API error: {response.status_code}')
"
```

## Troubleshooting

### Google API Issues:

**Error: "Service account not found"**
- Ensure `credentials.json` is in the project root
- Check the service account email is correct
- Make sure you shared the sheet with the service account

**Error: "Insufficient permissions"**
- Share your Google Sheet with the service account email
- Give "Editor" permissions
- Enable required APIs in Google Cloud Console

**Error: "Quota exceeded"**
- Check your API usage in Google Cloud Console
- Consider upgrading your quota if needed

### eBay API Issues:

**Error: "Invalid client credentials"**
- Double-check your Client ID and Client Secret
- Ensure you're using the correct environment (sandbox vs production)
- Verify your application is active

**Error: "Scope not authorized"**
- Check your application permissions in eBay Developer Console
- Ensure you're requesting the correct scope

## Security Notes

1. **Never commit credentials to git**:
   ```bash
   echo "credentials.json" >> .gitignore
   ```

2. **Keep credentials secure**:
   - Don't share your credentials files
   - Use environment variables for production
   - Rotate credentials periodically

3. **API Rate Limits**:
   - eBay: Varies by application type and tier
   - Google: 100 requests per 100 seconds per user (default)

## Environment Variables (Alternative Setup)

Instead of hardcoding credentials, you can use environment variables:

```bash
# Windows
set EBAY_CLIENT_ID=your_client_id
set EBAY_CLIENT_SECRET=your_client_secret
set GOOGLE_CREDENTIALS_PATH=path/to/credentials.json

# Linux/Mac
export EBAY_CLIENT_ID=your_client_id
export EBAY_CLIENT_SECRET=your_client_secret
export GOOGLE_CREDENTIALS_PATH=path/to/credentials.json
```

Then modify your config to use environment variables or update the code to read from them.