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
options.add_argument("--start-maximized")
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

# Clean function
def clean_model(text):
    return text.lower().replace('-', '').replace(' ', '')

# Scrape each model
for model_no in models:
    print(f"\n🔎 Searching for model: {model_no}")
    driver.get('https://sydneytools.com.au/')
    
    try:
        # Wait for search box
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'search'))
        )
        search_box.clear()
        search_box.send_keys(model_no)
        search_box.send_keys(Keys.RETURN)

        # Wait for product results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.product-info h2 a'))
        )

        # Get all product links
        product_links = driver.find_elements(By.CSS_SELECTOR, '.product-info h2 a')
        clicked = False
        cleaned_model_no = clean_model(model_no)

        for link in product_links:
            title_attr = link.get_attribute('title')
            if not title_attr:
                continue

            # Check if cleaned model number appears anywhere in title (cleaned too)
            if cleaned_model_no in clean_model(title_attr):
                print(f"✅ Clicking matching product: {title_attr}")
                driver.execute_script("arguments[0].click();", link)
                clicked = True
                break

        # If no match, click the first product (fallback)
        if not clicked and product_links:
            print("⚡ No perfect title match, clicking first product as fallback.")
            driver.execute_script("arguments[0].click();", product_links[0])
            clicked = True

        if not clicked:
            print(f"❌ No matching product found for {model_no}. Skipping...")
            continue

        # Wait for product page
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.product-name'))
        )

        # Scrape product page
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        title_element = soup.find('h1', class_='product-name')
        title = title_element.get_text(strip=True) if title_element else 'N/A'

        price_element = soup.find('div', class_='price')
        price = price_element.get_text(strip=True) if price_element else 'N/A'

        product_images = []
        thumbnail_section = soup.find('div', id='image-thumbnails')

        if thumbnail_section:
            imgs = thumbnail_section.find_all('img')
            for img in imgs:
                src = img.get('src')
                if src and '/products/' in src and src.endswith('.jpeg'):
                    if not src.startswith('https'):
                        src = 'https://sydneytools.com.au' + src
                    src = src.replace('/512x512', '')  # Full-size
                    filename = src.split('/')[-1]
                    if filename not in [url.split('/')[-1] for url in product_images]:
                        product_images.append(src)

        # Write to CSV
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