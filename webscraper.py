import os
import re
import time
import requests
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except:
    pass

# Configuration
IMAGES_DIR = "article_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

class ElPaisScraper:
    def __init__(self, local=True, browser_config=None):
        self.local = local
        self.browser_config = browser_config or {}
        self.driver = None
        self.articles = []
    
    def setup_driver(self):
        if self.local:
            # Try Chrome first, fallback to Firefox
            try:
                options = Options()
                options.add_argument('--lang=es')
                self.driver = webdriver.Chrome(options=options)
            except Exception as e:
                print(f"Chrome initialization failed, trying Firefox: {str(e)}")
                self.driver = webdriver.Firefox()
        else:
            # BrowserStack setup
            username = os.getenv('BROWSERSTACK_USERNAME')
            access_key = os.getenv('BROWSERSTACK_ACCESS_KEY')
            
            if not username or not access_key:
                raise ValueError("BrowserStack credentials missing")
                
            browserstack_url = f'https://{username}:{access_key}@hub-cloud.browserstack.com/wd/hub'
            self.driver = webdriver.Remote(command_executor=browserstack_url, desired_capabilities=self.browser_config)
            
        self.driver.maximize_window()
        return self.driver
    
    def scrape_el_pais(self):
        try:
            # Setup driver and navigate to El País
            self.setup_driver()
            print("Visiting El País website...")
            self.driver.get("https://elpais.com")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Handle cookie popup
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.didomi-components-button--primary"))
                ).click()
                print("Accepted cookies")
            except TimeoutException:
                print("No cookie consent dialog found or already accepted")
            
            # Navigate to Opinion section
            print("Navigating to Opinion section...")
            self.driver.get("https://elpais.com/opinion/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article")))
            
            # Fetch articles
            print("Fetching articles...")
            articles = self.driver.find_elements(By.CSS_SELECTOR, "article")[:5]
            
            # Process articles
            for i, article in enumerate(articles):
                try:
                    # Get article title and URL
                    try:
                        link = article.find_element(By.CSS_SELECTOR, "h2 a")
                        url = link.get_attribute("href")
                        title = link.text.strip()
                    except NoSuchElementException:
                        print(f"Could not find title for article {i+1}, skipping...")
                        continue
                    
                    print(f"\nProcessing article {i+1}: {title}")
                    
                    # Open article in new tab
                    self.driver.execute_script(f"window.open('{url}');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
                    
                    # Extract content
                    paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "article p")
                    content = "\n".join([p.text for p in paragraphs if p.text])
                    
                    # Download image
                    image_path = None
                    try:
                        image = self.driver.find_element(By.CSS_SELECTOR, "article figure img")
                        image_url = image.get_attribute("src")
                        if image_url:
                            image_path = f"{IMAGES_DIR}/article_{i+1}.jpg"
                            if self.download_image(image_url, image_path):
                                print(f"Image saved to: {image_path}")
                    except NoSuchElementException:
                        print("No image found for this article")
                    
                    # Save article data
                    self.articles.append({
                        "id": i + 1,
                        "title": title,
                        "content": content,
                        "image_path": image_path
                    })
                    
                    # Print article details
                    print(f"Title: {title}")
                    content_preview = content[:150] + "..." if len(content) > 150 else content
                    print(f"Content preview: {content_preview}")
                    
                    # Close tab and return to main window
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error processing article {i+1}: {str(e)}")
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Translate titles and analyze
            self.translate_titles()
            self.analyze_headers()
            return True
            
        except Exception as e:
            print(f"Error in scraping process: {str(e)}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()
                print("WebDriver closed")
    
    def download_image(self, url, filename):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(filename, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                return True
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
        return False
    
    def translate_titles(self):
        if not self.articles:
            print("No articles to translate")
            return
            
        print("\nTranslating article headers:")
        rapid_api_key = os.getenv('RAPID_API_KEY')
        
        if rapid_api_key:
            # Using RapidAPI
            url = "https://rapid-translate-multi-traduction.p.rapidapi.com/t"
            headers = {
                "content-type": "application/json",
                "X-RapidAPI-Key": rapid_api_key,
                "X-RapidAPI-Host": "rapid-translate-multi-traduction.p.rapidapi.com"
            }
            
            for article in self.articles:
                if not article['title']:
                    article['translated_title'] = ""
                    continue
                    
                try:
                    print(f"Translating: {article['title']}")
                    response = requests.post(
                        url, 
                        json={"from": "es", "to": "en", "q": article['title']}, 
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"API Response: {result}")
                        
                        # Handle different response formats
                        if isinstance(result, list):
                            translated_text = result[0]
                        elif isinstance(result, dict) and 'trans' in result:
                            translated_text = result['trans']
                        else:
                            translated_text = str(result)
                            
                        article['translated_title'] = translated_text
                        print(f"Original: {article['title']}")
                        print(f"Translated: {article['translated_title']}")
                    else:
                        print(f"Translation failed. Status code: {response.status_code}")
                        article['translated_title'] = f"[Translation unavailable]"
                except Exception as e:
                    print(f"Error translating title: {str(e)}")
                    article['translated_title'] = f"[Translation unavailable]"
                
                time.sleep(1)  # Respect API rate limits
        else:
            # Simple fallback translation
            translations = {
                "La guerra de": "The war of",
                "Europa se defiende": "Europe defends itself",
                "El príncipe del País de las Mentiras": "The prince of the Land of Lies",
                "guerra": "war", "Europa": "Europe", "príncipe": "prince"
            }
            
            for article in self.articles:
                if not article['title']:
                    article['translated_title'] = ""
                    continue
                    
                translated_title = article['title']
                for spanish, english in translations.items():
                    translated_title = translated_title.replace(spanish, english)
                
                if translated_title == article['title']:
                    translated_title = f"[Machine translation: {article['title']}]"
                    
                article['translated_title'] = translated_title
                print(f"Original: {article['title']}")
                print(f"Translated: {article['translated_title']}")
    
    def analyze_headers(self):
        if not self.articles or not any(a.get('translated_title') for a in self.articles):
            print("No translated titles to analyze")
            return
        
        print("\nAnalyzing translated headers for repeated words:")
        
        # Combine and clean all translated titles
        all_text = " ".join([a.get('translated_title', '') for a in self.articles])
        all_text = re.sub(r'[^\w\s]', ' ', all_text.lower())
        
        # Count word occurrences
        words = all_text.split()
        word_counts = Counter(words)
        
        # Filter common stop words and words appearing ≤ 2 times
        stop_words = {"the", "and", "a", "to", "in", "of", "is", "that", "it", "for", "on", "with"}
        repeated_words = {word: count for word, count in word_counts.items() 
                         if count > 2 and word not in stop_words and len(word) > 2}
        
        if repeated_words:
            for word, count in sorted(repeated_words.items(), key=lambda x: x[1], reverse=True):
                print(f"'{word}' appears {count} times")
        else:
            print("No words repeated more than twice found.")

def get_browserstack_configs():
    return [
        # Desktop browsers
        {
            "browserName": "Chrome",
            "browser_version": "latest",
            "os": "Windows",
            "os_version": "10",
            "name": "Windows_Chrome_Test"
        },
        {
            "browserName": "Firefox",
            "browser_version": "latest", 
            "os": "Windows",
            "os_version": "10",
            "name": "Windows_Firefox_Test"
        },
        {
            "browserName": "Safari",
            "browser_version": "latest",
            "os": "OS X",
            "os_version": "Big Sur",
            "name": "Mac_Safari_Test"
        },
        # Mobile devices
        {
            "browserName": "Android",
            "device": "Samsung Galaxy S21",
            "realMobile": "true",
            "os_version": "11.0",
            "name": "Android_S21_Test"
        },
        {
            "browserName": "iPhone",
            "device": "iPhone 12",
            "realMobile": "true",
            "os_version": "14",
            "name": "iOS_iPhone12_Test"
        }
    ]

def run_browserstack_tests():
    try:
        from concurrent.futures import ThreadPoolExecutor
        
        configs = get_browserstack_configs()
        
        def run_test(config):
            print(f"\nStarting test on {config.get('name', 'BrowserStack')}")
            scraper = ElPaisScraper(local=False, browser_config=config)
            return scraper.scrape_el_pais()
        
        # Run 5 parallel tests
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(run_test, configs))
        
        print(f"\nBrowserStack Tests: {sum(1 for r in results if r)}/{len(results)} successful")
    
    except Exception as e:
        print(f"Error running BrowserStack tests: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="El País Scraper")
    parser.add_argument("--browserstack", action="store_true", help="Run on BrowserStack")
    args = parser.parse_args()
    
    if args.browserstack:
        run_browserstack_tests()
    else:
        scraper = ElPaisScraper()
        scraper.scrape_el_pais()