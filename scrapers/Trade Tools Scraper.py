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
csv_path = os.path.join(desktop, "scraped_products_tradetools.csv")

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

# Scrape TradeTools
for model_no in models:
    print(f"\n🔎 Searching for model: {model_no}")
    try:
        search_url = f"https://www.tradetools.com/search?query={model_no}"
        driver.get(search_url)

        # Explicitly wait for at least one product card to appear
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.images-3yd')))
        time.sleep(2)

        # Now scrape
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_cards = soup.select('a.images-3yd')

        product_link = None

        for card in product_cards:
            title_img = card.select_one('img.loaded-3iH')
            if title_img:
                title_text = title_img.get('alt', '').strip()
                if model_no.lower() in title_text.lower():
                    product_link = card.get('href')
                    break

        if not product_link:
            print(f"❌ No matching product found for {model_no}")
            continue

        if not product_link.startswith("http"):
            product_link = "https://www.tradetools.com" + product_link

        driver.get(product_link)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.productName-3vl')))
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Title
        title_element = soup.select_one('h1.productName-3vl')
        title = title_element.get_text(strip=True) if title_element else 'N/A'

        # Price
        price_whole = soup.select_one('div.price-2To span:nth-of-type(2)')
        price_cents = soup.select_one('div.price-2To span.cents-1T3')

        if price_whole and price_cents:
            price = f"{price_whole.text.strip()}.{price_cents.text.strip()}"
        else:
            price = 'N/A'

        # Images
        product_images = []
        image_elements = soup.select('div.slick-list div.slick-track img.loaded-3iH')

        for img in image_elements:
            img_url = img.get('src')
            if img_url and 'products' in img_url:
                if not img_url.startswith('http'):
                    img_url = 'https:' + img_url
                if img_url not in product_images:
                    product_images.append(img_url)

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