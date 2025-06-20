import csv
import json
import time
import random
import nest_asyncio; nest_asyncio.apply()
from playwright.sync_api import sync_playwright

url = "https://www.datacentermap.com/usa/indiana/"


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=50)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        java_script_enabled=True,
    )

    page = context.new_page()
    time.sleep(random.uniform(2, 5))
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
            time.sleep(random.uniform(3, 7))


            script_tag = city_page.query_selector('script#__NEXT_DATA__')
            json_text = script_tag.inner_text()
            parsed_json = json.loads(json_text)

            dcs = parsed_json["props"]["pageProps"]["mapdata"]["dcs"]

            for dc in dcs:
                props = dc["properties"]
                geometry = dc["geometry"]
                lat, lon = geometry["coordinates"][1], geometry["coordinates"][0]

                name = props.get("name")
                company_name = props.get("companyname") or ""
                address = props.get("address") or ""
                city_dc = props.get("city") or city
                postal = props.get("postal") or ""
                dc_url = f"https://www.datacentermap.com{props.get('url')}"

                full_address = f"{address}, {city_dc}, IN, {postal}, USA"



                results.append([
                    city,
                    full_url,
                    name,
                    company_name,
                    full_address,
                    dc_url,
                    lat,
                    lon
                ])

    city_page.close()

    unique_results = []
    seen_urls = set()
    for row in results:
        dc_url = row[5]
        if dc_url not in seen_urls:
            unique_results.append(row)
            seen_urls.add(dc_url)


    with open("in_data_centers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["City", "City URL", "Data Center Name", "Name", "Address", "Data Center URL", "Latitude", "Longitude"])
        writer.writerows(unique_results)

    print("Scraped", len(unique_results), "data centers.")
    browser.close()
