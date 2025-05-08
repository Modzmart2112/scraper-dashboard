from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import os
from bs4 import BeautifulSoup

# Setup Chrome options
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

# Setup CSV
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
csv_path = os.path.join(desktop, "scraped_products_toolswarehouse.csv")

with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['Title', 'Price'] + [f'Image {i}' for i in range(1, 11)]
    writer.writerow(header)

# Get model numbers
print("Paste Model Numbers one by one. Press Enter after each. Type 'done' to start scraping.\n")
models = []

while True:
    model = input("Enter Model No (or 'done'): ").strip()
    if model.lower() == 'done':
        break
    if model:
        models.append(model)

# Scrape Tools Warehouse
for model_no in models:
    print(f"\n🔎 Searching for model: {model_no}")
    try:
        search_url = f"https://toolswarehouse.com.au/pages/search-results-page?q={model_no}"
        driver.get(search_url)

        # Explicitly wait for at least one product card to appear
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.snize-view-link')))
        time.sleep(2)

        # Now scrape
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_cards = soup.select('a.snize-view-link')

        product_link = None

        for card in product_cards:
            title_elem = card.select_one('.snize-title')
            if title_elem:
                title_text = title_elem.text.strip()
                if model_no.lower() in title_text.lower():
                    product_link = card.get('href')
                    break

        if not product_link:
            print(f"❌ No matching product found for {model_no}")
            continue

        if not product_link.startswith("http"):
            product_link = "https://toolswarehouse.com.au" + product_link

        driver.get(product_link)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.product-title')))
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Title
        title_element = soup.select_one('h1.product-title')
        title = title_element.get_text(strip=True) if title_element else 'N/A'

        # Price
        price_element = soup.select_one('div.product-pricing span.money[data-price]')
        price = price_element.get_text(strip=True).replace('$', '') if price_element else 'N/A'

        # Images
        product_images = []
        image_elements = soup.select('div.product-gallery--viewer img')

        for img in image_elements:
            img_url = img.get('src')
            if img_url and 'products' in img_url:
                # Make sure full URL and high-res version
                clean_url = img_url.replace("_700x700", "_1000x1000").replace("_592x592", "_1000x1000")
                if not clean_url.startswith('http'):
                    clean_url = 'https:' + clean_url
                if clean_url not in product_images:
                    product_images.append(clean_url)

        product_images = product_images[:10]  # limit to 10 images

        # Save to CSV
        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            row = [title, price] + product_images
            writer.writerow(row)

        print(f"✅ Saved: {title}")

    except Exception as e:
        print(f"❌ Error for {model_no}: {e}")
        continue

print("\n🎉 Done! CSV saved at:", csv_path)
driver.quit()