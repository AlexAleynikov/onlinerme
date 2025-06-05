from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
import pandas as pd
import os

# Selenium settings
driver_path = "C:/chromedriver/chromedriver.exe"
service = Service(driver_path)
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
driver = webdriver.Chrome(service=service, options=options)


# Function for random waiting
def random_sleep(min_time=2, max_time=5):
    time.sleep(random.uniform(min_time, max_time))


# Loading Parcel Number from CSV
csv_file = "clarke_parser/Retreat_lots-2.csv"
df = pd.read_csv(csv_file, header=None, dtype=str)

df["Parcel Number"] = df[0].str.split(",", n=1, expand=True)[0]
df = df.dropna(subset=["Parcel Number"])

# File to save the results
output_file = "clarke_parser/Balance.csv"
file_exists = os.path.isfile(output_file)

driver.get("https://tax.clarkecounty.gov/Account/Login")
random_sleep()

# Log in to the system
email_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "Email")))
email_field.send_keys("publicInquiry@clarkecounty.gov")
random_sleep(1, 3)

password_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "Password")))
password_field.send_keys("ClarkeCoTax3s!")
random_sleep(1, 3)

login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']")))
ActionChains(driver).move_to_element(login_button).perform()
random_sleep(1, 2)
login_button.click()
print("Successful entry!")


# Function to open the search page
def open_search_page():
    try:
        payment_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/PortalAccount/SearchForParcel?NextAction=PAYMENT']"))
        )
        ActionChains(driver).move_to_element(payment_link).perform()
        random_sleep(1, 3)
        payment_link.click()
        random_sleep(2, 4)
    except Exception as e:
        print(f"Error opening the search page: {e}")


# Processing of each Parcel Number
for index, row in df.iterrows():
    parcel_number = row["Parcel Number"].strip()
    if parcel_number == "":
        continue

    try:
        open_search_page()

        parcel_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ParcelNumber")))
        parcel_field.clear()
        parcel_field.send_keys(parcel_number)
        random_sleep(1, 3)

        search_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']")))
        ActionChains(driver).move_to_element(search_button).perform()
        random_sleep(1, 2)
        search_button.click()
        random_sleep()

        try:
            no_match = driver.find_element(By.XPATH, "//li[contains(text(), 'No matches found.')]")
            balance = "No matches found"
            print(f" Parcel Number: {parcel_number} | ❌ No matches found. Write down the balance sheet: {balance}")
        except:
            parcel_info = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "panel-body")))
            balance = parcel_info.find_element(By.XPATH, "//dt[text()='Current Balance:']/following-sibling::dd").text.strip()
            print(f"📍 Parcel Number: {parcel_number} | Balance: {balance}")

        balance_df = pd.DataFrame([[parcel_number, balance]], columns=["Parcel Number", "Balance"])
        balance_df.to_csv(output_file, mode='a', header=not file_exists, index=False)
        file_exists = True
    except Exception as e:
        print(f"Error for {parcel_number}: {e}")

driver.quit()


retreat_lots_df = pd.read_csv("clarke_parser/Retreat_lots-2.csv")
balance_df = pd.read_csv("clarke_parser/Balance.csv")

balance_df.rename(columns={"Parcel Number": "TAX_MAP"}, inplace=True)
merged_df = retreat_lots_df.merge(balance_df, on="TAX_MAP", how="left")
merged_df.to_csv("clarke_parser/Merged_Retreat_lots.csv", index=False)

print("'Merged_Retreat_lots.csv' successfully created")
