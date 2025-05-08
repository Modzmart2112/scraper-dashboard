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
options.add_argument("--headless=new")  # headless mode
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

# Setup CSV
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
csv_path = os.path.join(desktop, "scraped_products.csv")

# Create CSV with headers
with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['Title', 'Price'] + [f'Image {i}' for i in range(1, 21)]
    writer.writerow(header)

# Ask for model numbers
print("Paste Model Numbers one by one. Press Enter after each. Type 'done' to start scraping.\n")
models = []

while True:
    model = input("Enter Model No (or 'done'): ").strip()
    if model.lower() == 'done':
        break
    if model:
        models.append(model)

# Scrape each model
for model_no in models:
    print(f"\n🔎 Searching for model: {model_no}")
    driver.get('https://sydneytools.com.au/')
    
    try:
        # Search for product
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'search'))
        )
        search_box.clear()
        search_box.send_keys(model_no)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)

        # Wait for search results
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.product-info'))
        )

        time.sleep(1)

        products = driver.find_elements(By.CSS_SELECTOR, '.product-info')

        matching_product = None

        for product in products:
            outer_html = product.get_attribute('outerHTML').lower()
            if model_no.lower() in outer_html:
                matching_link = product.find_element(By.CSS_SELECTOR, 'a.black-href')
                matching_product = matching_link
                break

        if matching_product:
            href = matching_product.get_attribute('href')
            if not href.startswith("http"):
                href = "https://sydneytools.com.au" + href
            driver.get(href)
        else:
            print(f"❌ No matching product found for {model_no}")
            continue

        # Wait for product page
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        title_element = soup.find('h1')
        title = title_element.get_text(strip=True) if title_element else 'N/A'
        title = title.replace('\n', ' ').strip()

        price_element = soup.find('div', class_='price')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = price_text.replace('$', '').strip()
        else:
            price = 'N/A'

        product_images = []
        thumbnail_section = soup.find('div', id='image-thumbnails')

        if thumbnail_section:
            imgs = thumbnail_section.find_all('img')
            for img in imgs:
                src = img.get('src')
                if src and '/products/' in src and src.endswith('.jpeg'):
                    if not src.startswith('https'):
                        src = 'https://sydneytools.com.au' + src
                    src = src.replace('/512x512', '')
                    filename = src.split('/')[-1]
                    if filename not in [url.split('/')[-1] for url in product_images]:
                        product_images.append(src)

        # Save to CSV
        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            row = [title, price] + product_images[:20]
            writer.writerow(row)

        print(f"✅ Saved: {title}")

    except Exception as e:
        print(f"❌ Error for {model_no}: {e}")
        continue

print("\n🎉 Done! CSV saved at:", csv_path)
driver.quit()