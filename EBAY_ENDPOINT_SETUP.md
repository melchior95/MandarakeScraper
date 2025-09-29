# eBay Marketplace Account Deletion Endpoint Setup

This guide helps you set up the required eBay Marketplace Account Deletion notification endpoint to enable your production eBay API keys.

## Overview

eBay requires all developers to implement an endpoint that can:
1. Handle challenge code verification during setup
2. Receive account deletion notifications (if you store user data)

**Important**: Since this scraper only stores product data (not user data), the endpoint mainly serves to satisfy eBay's requirement for production API access.

## Quick Start

### Step 1: Configure the Endpoint

Run the interactive setup:
```bash
cd "C:\Python Projects\mandarake_scraper"
python ebay_endpoint_config.py setup
```

This will:
- Generate a secure 64-character verification token
- Prompt you for your HTTPS endpoint URL
- Create a `.env` file with the configuration
- Test the challenge response generation

### Step 2: Install Dependencies

```bash
pip install flask python-dotenv
```

### Step 3: Test Locally (Optional)

Test the endpoint locally first:
```bash
python ebay_deletion_endpoint.py
```

Visit `http://localhost:5000/health` to verify it's working.

### Step 4: Deploy to Production

You need to deploy this to an HTTPS server accessible from the internet. Options include:

#### Option A: Heroku (Recommended for simple deployment)
1. Create a Heroku account
2. Install Heroku CLI
3. Create a new Heroku app
4. Deploy the endpoint

#### Option B: Your Own Server
1. Upload `ebay_deletion_endpoint.py` to your server
2. Configure your web server (Apache/Nginx) to serve it via HTTPS
3. Ensure the endpoint URL is accessible from the internet

#### Option C: Cloud Platforms (AWS, Google Cloud, Azure)
1. Use serverless functions or container services
2. Configure HTTPS domain
3. Deploy the endpoint

### Step 5: Register with eBay

1. Go to your [eBay Developer Console](https://developer.ebay.com/my/keys)
2. Navigate to "Alerts and Notifications"
3. Enter your alert email address
4. Enter your HTTPS endpoint URL (e.g., `https://your-domain.com/ebay-deletion-endpoint`)
5. Enter your verification token (from the .env file)
6. Click "Save"

eBay will immediately send a challenge code to your endpoint to verify it's working.

## Configuration Details

### Environment Variables

Create a `.env` file with:
```env
EBAY_VERIFICATION_TOKEN=your-64-character-token-here
EBAY_ENDPOINT_URL=https://your-domain.com/ebay-deletion-endpoint
```

### Verification Token Requirements
- Length: 32-80 characters
- Allowed characters: alphanumeric, underscore (_), hyphen (-)
- Must be kept secret and consistent

## Testing

### Test Challenge Response Locally
```bash
python ebay_endpoint_config.py test-challenge "test123" "your-token" "https://your-domain.com/ebay-deletion-endpoint"
```

### Test Deployed Endpoint
```bash
curl "https://your-domain.com/ebay-deletion-endpoint?challenge_code=test123"
```

Should return:
```json
{
  "challengeResponse": "52161ff4651cb71888801b47bae62f44d7f6d0aab17e70d00f64fc84368ca38f"
}
```

### Health Check
```bash
curl "https://your-domain.com/health"
```

## Troubleshooting

### Common Issues

1. **"Marketplace account deletion endpoint validation failed"**
   - Verify your endpoint is accessible via HTTPS
   - Check that the verification token matches exactly
   - Ensure the challenge response is calculated correctly

2. **"Endpoint not responding"**
   - Test the /health endpoint
   - Check server logs for errors
   - Verify firewall/security group settings

3. **"Invalid challenge response"**
   - Verify the hash calculation order: challengeCode + verificationToken + endpointURL
   - Check for extra characters or encoding issues
   - Use the test command to verify locally

### Debug Mode

Add debug logging to see what's happening:
```bash
# Set environment variable for debug mode
export FLASK_DEBUG=1
python ebay_deletion_endpoint.py
```

### Validation Commands

```bash
# Validate current configuration
python ebay_endpoint_config.py validate

# Generate a new token
python ebay_endpoint_config.py generate-token

# Test challenge response calculation
python ebay_endpoint_config.py test-challenge <code> <token> <url>
```

## Security Considerations

1. **HTTPS Required**: eBay requires HTTPS for all endpoints
2. **Token Security**: Keep your verification token secret
3. **Input Validation**: The endpoint validates all incoming requests
4. **Logging**: All requests are logged for audit purposes

## Production Deployment Example (Heroku)

1. Create `Procfile`:
```
web: gunicorn ebay_deletion_endpoint:app
```

2. Create `requirements.txt`:
```
flask>=2.0.0
gunicorn>=20.0.0
python-dotenv>=0.19.0
```

3. Deploy:
```bash
heroku create your-app-name
heroku config:set EBAY_VERIFICATION_TOKEN=your-token
heroku config:set EBAY_ENDPOINT_URL=https://your-app-name.herokuapp.com/ebay-deletion-endpoint
git add .
git commit -m "Add eBay deletion endpoint"
git push heroku main
```

## After Successful Setup

Once eBay validates your endpoint:
1. Your production API keys will be enabled
2. You can use production eBay APIs in your scraper
3. The endpoint will continue to receive periodic health checks from eBay
4. You'll be notified if any eBay users request account deletion (though unlikely for a scraper)

## Support

If you encounter issues:
1. Check the eBay Developer Community forums
2. Review eBay's official documentation
3. Use the debug commands provided in this setup
4. Check server logs for detailed error messages

## Files Created

- `ebay_deletion_endpoint.py` - Main endpoint implementation
- `ebay_endpoint_config.py` - Configuration and testing utilities
- `EBAY_ENDPOINT_SETUP.md` - This setup guide
- `.env` - Configuration file (created during setup)