import csv
import re
import json
import os 
from geopy.geocoders import Nominatim
import nest_asyncio; nest_asyncio.apply()
from playwright.sync_api import sync_playwright
from geopy.exc import GeocoderTimedOut
import time

url = "https://www.datacentermap.com/usa/michigan/"

def reorder_address(addr):
    parts = [p.strip() for p in addr.split(",")]
    if len(parts) < 2:
        return addr
    street = parts[0]
    rest = ",".join(parts[1:])
    zip_match = re.search(r"\b(\d{5})\b", rest)
    if not zip_match:
        return addr
    zip_code = zip_match.group(1)
    city = rest.replace(zip_code, "").strip()
    reordered = f"{street}, {city}, MI {zip_code}"
    return reordered

def abbreviate_address(address):
    replacements = {
        r'\bRoad\b': 'Rd',
        r'\bDrive\b': 'Dr',
    }
    for pattern, replacement in replacements.items():
        address = re.sub(pattern, replacement, address, flags=re.IGNORECASE)
    return address

geolocator = Nominatim(user_agent="data_center")
geocode_cache = {}
if os.path.exists("geocode_cache.json"):
    with open("geocode_cache.json", "r", encoding="utf-8") as f:
        geocode_cache = json.load(f)
else:
    geocode_cache = {}

def geocoded_address(address, retries=3, delay=1):
    for attempt in range(retries):
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                coords = (location.latitude, location.longitude)
                geocode_cache[address] = coords
                return coords
            else:
                geocode_cache[address] = (None, None)
                return None, None
        except GeocoderTimedOut:
            time.sleep(delay)
    


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context()

    # Block images, fonts, scripts
    context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "script"] else route.continue_())

    page = context.new_page()
    page.goto(url)

    rows = page.query_selector_all("table.table tbody tr")
    results = []

    city_page = context.new_page()

    for row in rows:
        city_elem = row.query_selector("td:nth-child(1) a")
        count_elem = row.query_selector("td:nth-child(2)")

        if city_elem and count_elem:
            city = city_elem.inner_text().strip()
            city_link = city_elem.get_attribute("href")
            full_url = f"https://www.datacentermap.com{city_link}"

            city_page.goto(full_url)
            city_page.wait_for_selector("a.ui.card")

            cards = city_page.query_selector_all("a.ui.card")
            for card in cards:
                name_elem = card.query_selector(".header")
                desc_elem = card.query_selector(".description")
                href = card.get_attribute("href")

                if name_elem and desc_elem and href:
                    name = name_elem.inner_text().strip()
                    dc_url = f"https://www.datacentermap.com{href}"
                    full_desc = desc_elem.inner_text().strip().replace("\n", ", ")

                    if "," in full_desc:
                        name_part, address_part = full_desc.split(",", 1)
                        name_part = name_part.strip()
                        address_part = re.sub(r'\b(?:Inc\.?|LLC|L\.L\.C\.?)[,]?\b', '', address_part, flags=re.IGNORECASE)
                        address_part = re.sub(r'\s*,\s*', ', ', address_part)  
                        address_part = re.sub(r'\s+', ' ', address_part).strip()
                        address_part = re.sub(r'^[\s,\.]+', '', address_part)
                        address_part = abbreviate_address(address_part)

                        

                        reordered_address = reorder_address(address_part)
                        address_with_state = reordered_address

                        results.append([
                            city,
                            full_url,
                            name,
                            name_part,
                            address_with_state,
                            dc_url
                        ])

    city_page.close()

    unique_results = []
    seen_urls = set()
    for row in results:
        dc_url = row[5]
        if dc_url not in seen_urls:
            unique_results.append(row)
            seen_urls.add(dc_url)

    
    geocode_results = []
    
    for idx, row in enumerate(unique_results):
        address = row[4]
        lat, lon = geocoded_address(address)
        geocode_results.append(row + [lat, lon])

        if idx % 10 == 0:
            print(f"Geocoded {idx + 1}/{len(unique_results)}")

        time.sleep(2.5)

    with open("michigan_data_centers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["City", "City URL", "Data Center Name", "Name", "Address", "Data Center URL", "Latitude", "Longitude"])
        writer.writerows(geocode_results)

    print("Scraped", len(geocode_results), "data centers.")
    browser.close()
