import csv
import nest_asyncio; nest_asyncio.apply()
from playwright.sync_api import sync_playwright


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
                        description = desc_elem.inner_text().strip().replace("\n", ", ")
                        dc_url = f"https://www.datacentermap.com{href}"

                        results.append([
                            city,
                            full_url,
                            name,
                            description,
                            dc_url
                        ])

        city_page.close()

    unique_results = []
    seen_urls = set()
    for row in results:
        data_center_url = row[4]
        if data_center_url not in seen_urls:
            unique_results.append(row)
            seen_urls.add(data_center_url)
            
    with open("michigan_data_centers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["City", "City URL", "Data Center Name", "Description", "Data Center URL"])
        writer.writerows(unique_results)

    print("Scraped", len(unique_results), "cities.")

    browser.close()