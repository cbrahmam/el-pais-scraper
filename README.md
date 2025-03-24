# El País Web Scraper

A Selenium-based web scraper that extracts articles from El País (Spanish news outlet), translates their titles to English, and performs text analysis.

## Requirements

- Python 3.6+
- Selenium WebDriver
- Chrome/Firefox browser 
- BrowserStack account (for cross-browser testing)

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create `.env` file with API keys:
   ```
   # For translation
   RAPID_API_KEY=your_api_key
   
   # For BrowserStack testing
   BROWSERSTACK_USERNAME=your_username
   BROWSERSTACK_ACCESS_KEY=your_access_key
   ```

## Usage

Run locally:
```
python webscraper.py
```

Run on BrowserStack:
```
python webscraper.py --browserstack
```

## Features

- Scrapes articles from El País Opinion section
- Downloads article images
- Translates article titles from Spanish to English
- Identifies repeated words in translated headers
- Cross-browser testing via BrowserStack

## Browser Configurations

Tests on 5 browser configurations:
- Windows 10 (Chrome, Firefox)
- macOS Big Sur (Safari)
- Mobile: Samsung Galaxy S21, iPhone 12
