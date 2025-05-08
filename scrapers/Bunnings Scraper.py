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
wait = WebDriverWait(driver, 10)

# Setup CSV
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
csv_path = os.path.join(desktop, "scraped_products_bunnings.csv")

with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['Title', 'Price'] + [f'Image {i}' for i in range(1, 6)]
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

# Scrape Bunnings
for model_no in models:
    print(f"\n🔎 Searching for model: {model_no}")
    try:
        search_url = f"https://www.bunnings.com.au/search/products?page=1&q={model_no}&sort=BoostOrder"
        driver.get(search_url)

        # Wait for product cards
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-locator^="image-rating"]')))

        # Find matching product link
        products = driver.find_elements(By.CSS_SELECTOR, 'a[data-locator^="image-rating"]')
        product_link = None

        for product in products:
            title = product.get_attribute('title')
            if model_no.lower() in title.lower():
                product_link = product.get_attribute('href')
                break

        if not product_link:
            print(f"❌ No matching product found for {model_no}")
            continue

        driver.get(product_link)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-locator="product-title"]')))
        time.sleep(2)  # Give page some breathing time

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Title
        title_element = soup.select_one('h1[data-locator="product-title"]')
        title = title_element.get_text(strip=True) if title_element else 'N/A'

        # Price
        price_element = soup.select_one('p[data-locator="product-price"]')
        price = price_element.get_text(strip=True).replace('$', '') if price_element else 'N/A'

        # Images
        product_images = []
        image_elements = soup.select('div.slick-slide img')

        for img in image_elements:
            src = img.get('src') or img.get('data-src')
            if src and 'media.bunnings.com.au' in src:
                clean_src = src.split('?')[0]
                if clean_src not in product_images:
                    product_images.append(clean_src)

        product_images = product_images[:5]

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