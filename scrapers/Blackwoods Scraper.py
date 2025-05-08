import asyncio
import csv
import os
import re
import time
from playwright.async_api import async_playwright
import requests
import traceback

# ====== CONFIGURATION ======

base_folder = os.getcwd()
csv_path = os.path.join(base_folder, "blackwoods_scraped_products.csv")
error_log_path = os.path.join(base_folder, "error_log.txt")
api_response_log_path = os.path.join(base_folder, "api_responses.txt")

# ====== LOGIN CREDENTIALS ======

BLACKWOODS_EMAIL = "Itzkinitix@gmail.com"
BLACKWOODS_PASSWORD = "geSqE4Zhr5U/#4E"

# ====== FILE PREPARATION ======

# Prepare CSV with room for 10 images
with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['Title', 'Price'] + [f'Image {i}' for i in range(1, 11)]
    writer.writerow(header)

# ====== LOGGING FUNCTION ======

def log_error(error_message):
    with open(error_log_path, mode='a', encoding='utf-8') as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}\n")
    print(f"⚠️ Error logged to {error_log_path}")

# ====== LOGIN FUNCTION ======

async def login(page):
    print("\n🔐 Logging into Blackwoods...")
    await page.goto("https://www.blackwoods.com.au/", timeout=60000)
    await page.click("a.my-account-nav", timeout=10000)
    await page.fill("#j_username", BLACKWOODS_EMAIL)
    await page.fill("#j_password", BLACKWOODS_PASSWORD)
    await page.click("#wisLogin")
    print("🔄 Login button clicked. Waiting for login to complete...")
    await page.wait_for_timeout(5000)

    # Try to close delivery popup if it appears
    try:
        await page.click("#closebranchPopup", timeout=5000)
        print("✅ Delivery popup closed.")
    except Exception:
        print("✅ No delivery popup appeared.")

# ====== FETCH CREDENTIALS ======

async def fetch_credentials(page, first_model):
    print("\n🔑 Fetching API credentials after login...")
    api_key = None
    bearer_token = None

    async def capture_headers(response):
        nonlocal api_key, bearer_token
        if "search/v3" in response.url and response.request.method == "POST":
            headers = response.request.headers
            api_key = headers.get("x-api-key")
            auth_header = headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                bearer_token = auth_header.split("Bearer ")[1]

    page.on("response", capture_headers)

    search_url = f"https://www.blackwoods.com.au/searchpage#q={first_model}"
    print(f"🔎 Opening search URL: {search_url}")
    await page.goto(search_url, timeout=60000)
    await page.wait_for_timeout(5000)

    if not api_key or not bearer_token:
        raise Exception("❌ Failed to capture API key or Bearer token after login.")

    print("✅ Successfully captured logged-in API Key and Bearer Token.")
    return api_key, bearer_token

# ====== PRODUCT SCRAPING ======

def search_product(model_number, api_key, bearer_token):
    API_URL = "https://api2.blackwoods.com.au/sx/rest/search/v3?organizationId=130810-Anonymous-7091e14f-fc40-420e-8379-4c247053c887"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {bearer_token}",
        "content-type": "application/json",
        "x-api-key": api_key,
        "x-type": "User",
        "x-username": "Anonymous-7091e14f-fc40-420e-8379-4c247053c887",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
    }

    payload = {
        "locale": "en",
        "tab": "default",
        "fieldsToInclude": ["ec_name", "ec_price", "permanentid"],
        "firstResult": 0,
        "numberOfResults": 1,
        "q": model_number,
        "context": {
            "Warehouse": "NSGS",
            "Postcode": "2145",
            "ViewCode": "DEFAULT_CV_B2C_ANONYMOUS"
        }
    }

    response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()

async def scrape_product(page, model_number, api_key, bearer_token):
    print(f"\n🔎 Searching for model: {model_number}")
    try:
        data = search_product(model_number, api_key, bearer_token)

        # 🔥 Save API response to text file
        with open(api_response_log_path, mode='a', encoding='utf-8') as f:
            f.write(f"\n\n=== API RESPONSE FOR MODEL: {model_number} ===\n")
            f.write(f"{data}\n")

        results = data.get('results', [])
        if not results:
            print(f"❌ No results found for {model_number}")
            return

        raw_data = results[0].get('raw', {})
        title = raw_data.get('ec_name', 'N/A')
        permanent_id = raw_data.get('permanentid')

        if not permanent_id:
            print(f"❌ No permanent ID found for {model_number}")
            return

        # Build Product URL and visit page
        product_url = f"https://www.blackwoods.com.au/p/{permanent_id}"
        await page.goto(product_url, timeout=60000)

        # Scrape real price from frontend
        price_element = await page.query_selector("span.pdp-inc-gst span span")
        if price_element:
            correct_price = await price_element.inner_text()
            correct_price = correct_price.replace('$', '').strip()
        else:
            correct_price = "N/A"

        # Scrape all product images from gallery
        img_elements = await page.query_selector_all(".productGallery img")
        image_urls = []
        for img in img_elements:
            src = await img.get_attribute("src")
            if src:
                clean_src = src.split('?')[0]
                if clean_src.startswith("https://www.blackwoods.com.au/pim/images/"):
                    image_urls.append(clean_src)

        # Remove duplicates and limit to 10 images max
        image_urls = list(dict.fromkeys(image_urls))[:10]

        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            row = [title, correct_price] + image_urls
            writer.writerow(row)

        print(f"✅ Saved: {title} | {correct_price} | {len(image_urls)} images")

    except Exception as e:
        log_error(f"scrape_product({model_number}) failed: {str(e)}\n{traceback.format_exc()}")

# ====== MAIN WORKFLOW ======

async def main():
    models = []
    print("Paste Model Numbers one by one. Press Enter after each. Type 'done' to start scraping.\n")

    try:
        while True:
            model = input("Enter Model No (or 'done'): ").strip()
            if model.lower() == 'done':
                break
            if model:
                models.append(model)
    except Exception as e:
        log_error(f"Input reading failed: {str(e)}")
        return

    if not models:
        print("⚠️ No models entered. Exiting.")
        return

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            await login(page)
            api_key, bearer_token = await fetch_credentials(page, models[0])

            for model in models:
                await scrape_product(page, model, api_key, bearer_token)

            await browser.close()

    except Exception as e:
        print(f"❌ Something went wrong: {str(e)}")
        log_error(str(e))

    print(f"\n🎉 Done! CSV saved at: {csv_path}")
    print(f"📝 Full API responses saved in: {api_response_log_path}")

if __name__ == "__main__":
    asyncio.run(main())