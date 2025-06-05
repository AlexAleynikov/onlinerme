import json
import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

TAX_ID_FILE = 'onlinerme/tax_id.json'
DOWNLOAD_DIR = "D:/Python/pdf_folder"
OUTPUT_FILE = "output.json"
DOWNLOAD_TIMEOUT = 30

chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": False
})

service = Service(executable_path="C:\\chromedriver\\chromedriver.exe")
driver = webdriver.Chrome(service=service, options=chrome_options)


def load_existing_data():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


data = load_existing_data()


def write_to_json(tax_id, description, time, filename):
    existing_entry = next((item for item in data if item["tax_id"] == tax_id), None)
    new_value = {"description": description, "time": time, "filename": filename}

    if existing_entry:
        if new_value not in existing_entry["value"]:
            existing_entry["value"].append(new_value)
    else:
        data.append({"tax_id": tax_id, "value": [new_value]})

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def wait_for_download(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    elapsed_time = 0
    while elapsed_time < DOWNLOAD_TIMEOUT:
        if os.path.exists(file_path) and not file_path.endswith(".crdownload"):
            return True
        time.sleep(1)
        elapsed_time += 1
    return False


def download_files(tax_id):
    index = 0
    while True:
        try:
            rows = driver.find_elements(By.XPATH, '//table[@class="BlackStandard"]//tr')[1:]
            if index >= len(rows):
                break

            try:
                view_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f'//a[contains(@href, "viewRow${index}")]'))
                )
                view_button.click()
                time.sleep(5)

                page_source = driver.page_source
                match = re.search(r"window\\.open\\('([^']+\\.pdf\\?[^']+)'\)", page_source)
                if match:
                    pdf_url = match.group(1)
                    filename = pdf_url.split('/')[-1].split('?')[0]
                    response = requests.get(pdf_url, stream=True)

                    if response.status_code == 200:
                        file_path = os.path.join(DOWNLOAD_DIR, filename)
                        with open(file_path, 'wb') as file:
                            for chunk in response.iter_content(1024):
                                file.write(chunk)

                        if wait_for_download(filename):
                            write_to_json(tax_id, "PDF Document", "", filename)
                        else:
                            print(f"Download failed for {filename}")
                            write_to_json(tax_id, "PDF Document", "", " ")
                    else:
                        write_to_json(tax_id, "PDF Document", "", " ")

                driver.refresh()
                time.sleep(5)
                index += 1
            except NoSuchElementException:
                index += 1
                continue
        except StaleElementReferenceException:
            print("DOM updated, retrying...")
            time.sleep(2)


def process_tax_ids():
    try:
        with open(TAX_ID_FILE, 'r') as f:
            tax_ids = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print("Error: Invalid or missing tax_id.json file")
        return

    for tax_id in tax_ids:
        print(f"Processing {tax_id}...")
        driver.get('https://www.onlinerme.com/contractorsearchproperty.aspx?countyID=3204&stateID=46&countryID=1')
        time.sleep(3)

        try:
            driver.find_element(By.ID, 'drpCountry').send_keys('United States')
            driver.find_element(By.ID, 'drpState').send_keys('Virginia')
            driver.find_element(By.ID, 'drpCounty').send_keys('Clarke County')
            driver.find_element(By.ID, 'cboSearchBy').send_keys('Tax ID')
            driver.find_element(By.ID, 'txtSearch').send_keys(tax_id)
            driver.find_element(By.ID, 'btnSearch').click()
        except NoSuchElementException:
            print(f"Error: Form element not found for {tax_id}")
            write_to_json(tax_id, "", "", "")
            continue

        time.sleep(3)

        try:
            uploads_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//div[text()="Uploads"]'))
            )
            uploads_button.click()
        except Exception:
            write_to_json(tax_id, "", "", "")
            continue

        time.sleep(3)
        download_files(tax_id)

        try:
            rows = driver.find_elements(By.XPATH, '//table[@class="BlackStandard"]//tr')[1:]
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 3:
                    description = cells[0].text
                    uploaded_on = cells[2].text
                    write_to_json(tax_id, description, uploaded_on, " ")
        except NoSuchElementException:
            write_to_json(tax_id, "", "", "")


try:
    process_tax_ids()
finally:
    driver.quit()


with open("parcels_retread_result.json", "r", encoding="utf-8") as f:
    parcels_data = json.load(f)


with open("output.json", "r", encoding="utf-8") as f:
    output_data = json.load(f)


tax_records = {entry["tax_id"]: entry["value"] for entry in output_data}


for feature in parcels_data["features"]:
    tax_map = feature["properties"].get("TAX_MAP")

    if tax_map in tax_records:
        for i, record in enumerate(tax_records[tax_map], start=1):
            feature["properties"][f"description_{i}"] = record["description"]
            feature["properties"][f"time_{i}"] = record["time"]
            feature["properties"][f"filename_{i}"] = record["filename"]


with open("updated_parcels.json", "w", encoding="utf-8") as f:
    json.dump(parcels_data, f, ensure_ascii=False, indent=2)
