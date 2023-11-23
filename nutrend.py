import time
import os
import pandas as pd
import requests

from urllib.parse import quote
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from typing import List


def get_driver() -> WebDriver:
    return webdriver.Chrome(service=Service(ChromeDriverManager(version='114.0.5735.90').install()))


def download_image(images_folder_path, image_counter, barcode, image_link):
    image_path = os.path.join(images_folder_path, str(barcode))

    with open(f'{image_path}_{image_counter}.jpg', 'wb') as f:
        f.write(requests.get(image_link).content)


def find_product_by_name(
        names: List[str],
        images_folder_path: str,
        output_excel_file_path: str,
        base_url="https://www.nutrend.eu/vyhledavani?q=",
        sleep=9,
        start_row_number=2,
) -> None:
    if not os.path.exists(images_folder_path):
        os.makedirs(images_folder_path)

    driver = get_driver()
    driver.maximize_window()

    for excel_row, name in enumerate(names):
        print("Excel row number:  %s" % (int(excel_row) + start_row_number))
        print("Crawling name *%s* ..." % name)
        driver.get(base_url + quote(name))
        time.sleep(sleep / 2)
        try:
            results = driver.find_element(By.CSS_SELECTOR, 'div.grow').find_elements(By.CSS_SELECTOR, 'div[data-price]')
        except NoSuchElementException:
            print("No results found for %s (SKIPPING...)" % name)
            continue

        # get the links of those articles
        product_links = [el.find_element(By.TAG_NAME, "a").get_attribute("href") for el in results]
        print("Found %s results..." % len(product_links))

        images_folder_paths = [images_folder_path]

        if len(product_links) > 1:
            images_folder_paths = []
            for i in range(len(product_links)):
                modified_images_folder_path = os.path.join(images_folder_path, str(name), str(i + 1))
                images_folder_paths.append(modified_images_folder_path)
                os.makedirs(modified_images_folder_path, exist_ok=True)

        # loop through each link (which each of them is a product)
        for index, product_link in enumerate(product_links):
            print("Crawling result %s/%s..." % (index + 1, len(product_links)))
            driver.get(product_link)  # go to product detail page
            time.sleep(sleep / 2)
            title = driver.find_element(By.CSS_SELECTOR, 'div.sticky.top-44 h1').text
            description = driver.find_element(By.XPATH, "/html/body/section[1]/div/div[4]/div[2]").find_element(
                By.TAG_NAME, "p").text
            images = driver.find_element(By.XPATH, "/html/body/section[1]/div/div[2]").find_elements(By.TAG_NAME, 'a')[
                     :-1]
            images_set = set()
            for a in images:
                images_set.add(
                    a.find_element(By.TAG_NAME, "img").get_attribute("src").replace("productPageThumb", "public"))
            image_counter = 1
            for img_link in images_set:
                download_image(images_folder_paths[index], image_counter, name, img_link)
                image_counter += 1

            cols = []
            rows = []
            try:
                driver.execute_script("window.scrollTo(0, 700)")
                ingredients_btn = driver.find_element(By.CSS_SELECTOR,
                                                      'body > section.container.mx-auto.my-8.px-4 > div > div:nth-child(4) > div:nth-child(4) > div.flex.flex-wrap.items-center.gap-4.border-b.border-b-silver-50 > button'
                                                      )
                x_offset = 100
                y_offset = 5

                actions = ActionChains(driver)
                actions.move_to_element_with_offset(ingredients_btn, x_offset, y_offset)
                actions.click()
                actions.perform()

                nutritive_table = driver.find_element(By.CSS_SELECTOR, 'figure.table > table > tbody')
                tr_elements = nutritive_table.find_elements(By.TAG_NAME, "tr")
                for i, tr in enumerate(tr_elements):
                    td_elements = tr.find_elements(By.TAG_NAME, "td")
                    each_row = []
                    for td in td_elements:
                        if i == 0:
                            cols.append(td.text)
                        else:
                            each_row.append(td.text)
                    if len(each_row) > 0:
                        rows.append(each_row)
            except NoSuchElementException:
                print("No nutritive table found, SKIPPING...")

            headers = ["TITLE", "DESCRIPTION", "LINK", "COLUMNS", "ROWS"]

            new_row = [
                title,
                description,
                product_link,
                cols,
                rows
            ]

            # saves data instantly
            if os.path.exists(output_excel_file_path.split('.')[0] + ".xlsx"):
                # Read the existing EXCEL file
                df_existing_data = pd.read_excel(output_excel_file_path.split('.')[0] + ".xlsx")
                df_existing_data = pd.concat([df_existing_data, pd.DataFrame([new_row, ], columns=headers)],
                                             ignore_index=True)
            else:
                # Create a new DataFrame if the file doesn't exist
                df_existing_data = pd.DataFrame([new_row, ], columns=headers)

            df_existing_data.to_excel(output_excel_file_path.split('.')[0] + ".xlsx", index=False)

            driver.execute_script("window.history.go(-1)")  # go back 1 level
        print("Crawling for name *%s* done!" % name)
    driver.quit()
