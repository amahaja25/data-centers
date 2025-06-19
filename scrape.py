import csv
from geopy.geocoders import Nominatim
import nest_asyncio; nest_asyncio.apply()
from playwright.sync_api import sync_playwright
from geopy.exc import GeocoderTimedOut
import time



url = "https://www.datacentermap.com/usa/michigan/"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1700, "height": 720})
    page = context.new_page()
    page.goto(url)

    rows = page.query_selector_all("table.table tbody tr")

    results = []
    for row in rows:
        city_elem = row.query_selector("td:nth-child(1) a")
        count_elem = row.query_selector("td:nth-child(2)")

        if city_elem and count_elem:
            city = city_elem.inner_text().strip()
            count = count_elem.inner_text().strip()
            city_link = city_elem.get_attribute("href")
            full_url = f"https://www.datacentermap.com{city_link}"
           

            city_page = context.new_page()
            city_page.goto(full_url)
            city_page.wait_for_selector("a.ui.card")

            data_centers = []
            cards = city_page.query_selector_all("a.ui.card")
            for card in cards:
                name_elem = card.query_selector(".header")
                desc_elem = card.query_selector(".description")
                href = card.get_attribute("href")

                if name_elem and desc_elem and href:
                        name = name_elem.inner_text().strip()
                        dc_url = f"https://www.datacentermap.com{href}"

                        full_desc = desc_elem.inner_text().strip().replace("\n", ", ")
                        # split into name and address
                        if "," in full_desc:
                            name_part, address_part = full_desc.split(",", 1)  # split on first comma only
                            name_part = name_part.strip()
                            address_part = address_part.strip()
                            address_with_state = f"{address_part}, MI, USA"


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
        data_center_url = row[5]
        if data_center_url not in seen_urls:
            unique_results.append(row)
            seen_urls.add(data_center_url)

    geolocator = Nominatim(user_agent="data_center")

    def geocoded_address(address):
        try:
            location = geolocator.geocode(address)
            if location:
                return location.latitude, location.longitude
            else:
                return None, None
        except GeocoderTimedOut:
            time.sleep(1)
            return geocoded_address(address)
        
    geocode_results = []
    for row in unique_results:
        address = row[3]  # address_part is at index 3
        lat, lon = geocoded_address(address)
        geocode_results.append(row + [lat, lon])
        time.sleep(1)
            
    with open("michigan_data_centers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["City", "City URL", "Data Center Name", "Name", "Address", "Data Center URL", "Latitude", "Longitude"])
        writer.writerows(geocode_results)

    print("Scraped", len(geocode_results), "data centers.")

    browser.close()