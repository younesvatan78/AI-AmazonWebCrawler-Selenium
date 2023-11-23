import time
import requests
import os
import pandas as pd

from selenium import webdriver
from selenium.common import ElementNotInteractableException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List


def get_driver() -> WebDriver:
    return webdriver.Chrome(service=Service(executable_path='drivers/win64/chromedriver.exe'))


def parse_table(table: WebElement) -> List:
    cells = []
    for row in table.find_elements(By.CSS_SELECTOR, 'tr'):
        for cell in row.find_elements(By.TAG_NAME, 'td'):
            cells.append(cell.text)
    return cells


def parse_ul_list(ul: WebElement) -> List:
    values = []
    for li in ul.find_elements(By.TAG_NAME, "li"):
        for span in li.find_elements(By.TAG_NAME, "span"):
            values.append(span.text)
    return values


def download_image(images_folder_path, image_counter, filename, image_link):
    image_path = os.path.join(images_folder_path, str(filename))

    with open(f'{image_path}_{image_counter}.jpg', 'wb') as f:
        f.write(requests.get(image_link).content)


def find_product_by_barcode(
        barcodes: List[str],
        images_folder_path: str,
        output_excel_file_path: str,
        top_search_box_id="twotabsearchtextbox",
        base_url="https://amazon.ae/",
        sleep=9,
        start_row_number=2,
        search_icon_xpath="/html/body/div[1]/header/div/div[1]/div[2]/div/form/div[3]/div/span/input"
) -> None:
    if not os.path.exists(images_folder_path):
        os.makedirs(images_folder_path)

    driver = get_driver()
    driver.get(base_url)
    driver.maximize_window()

    for row_num, barcode in enumerate(barcodes):
        print("Excel row number:  %s" % (int(row_num) + start_row_number))
        print("Crawling barcode *%s* ..." % barcode)
        time.sleep(sleep / 2)
        # top search box
        top_search_box = driver.find_element(By.ID, top_search_box_id)
        top_search_box.clear()
        top_search_box.send_keys(barcode)
        # click on search icon to submit my search term
        driver.find_element(By.XPATH, search_icon_xpath).click()
        # select all divs that has a data-asin with a value
        results = driver.find_elements(By.CSS_SELECTOR,
                                       'div[data-asin]:not([data-asin=""])')  # MUST be in single quotes
        # get the links of those divs
        product_links = [el.find_element(By.CLASS_NAME, "a-link-normal").get_attribute("href") for el in results]
        print("Found %s results..." % len(product_links))

        images_folder_paths = [images_folder_path]

        if len(product_links) > 1:
            images_folder_paths = []
            for i in range(len(product_links)):
                modified_images_folder_path = os.path.join(images_folder_path, str(barcode), str(i + 1))
                images_folder_paths.append(modified_images_folder_path)
                os.makedirs(modified_images_folder_path, exist_ok=True)

        # loop through each link (which each of them is a product
        for index, product_link in enumerate(product_links):
            print("Crawling result %s/%s..." % (index + 1, len(product_links)))
            driver.get(product_link)  # go to product detail page
            time.sleep(sleep / 2)
            title = driver.find_element(By.ID, "productTitle").text
            if driver.find_element(By.ID, "bylineInfo").text:
                brand_name = driver.find_element(By.ID, "bylineInfo").text[7:]  # trim `Brand: `
            else:
                brand_name = ''
            # aue_price_whole = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole")
            # aue_price_fraction = driver.find_element(By.CSS_SELECTOR, "span.a-price-fraction")
            # price = aue_price_whole.text + "." + aue_price_fraction.text

            try:  # because description may not be available for every product
                product_description_el = driver.find_element(By.ID, "productDescription").find_element(By.TAG_NAME,
                                                                                                       "span")
            except NoSuchElementException:
                product_description_el = None
                print("product has no description!")
            if product_description_el:
                description = product_description_el.text
            else:
                description = ''
            try:  # because about_item may not be available for every product
                about_item_el = driver.find_element(By.CSS_SELECTOR, ".a-unordered-list.a-vertical.a-spacing-mini")
            except NoSuchElementException:
                about_item_el = None
                print("product has no about_item!")
            if about_item_el:
                about_item = '; '.join(parse_ul_list(about_item_el))
            else:
                about_item = ''
            # details = driver.find_element(By.CSS_SELECTOR,
            #                              ".a-unordered-list.a-nostyle.a-vertical.a-spacing-none.detail-bullet-list")
            # technical_details = driver.find_element(By.ID, 'productDetails_techSpec_section_1')
            # specifications = driver.find_element(By.CSS_SELECTOR, '#productOverview_feature_div > div > table')

            headers = ["BARCODE", "web_name", "web_description", "web_description2", "brand", "link"]

            new_row = [
                barcode,
                title,
                about_item,
                description,
                brand_name,
                product_link
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

            # getting image links
            try:
                image_counter = 1
                driver.find_element(By.ID, "imgTagWrapperId").click()
                time.sleep(sleep)  # wait for first image to load
                try:
                    # getting first image
                    first_image = driver.find_element(By.CSS_SELECTOR, 'div#ivLargeImage') \
                        .find_element(By.TAG_NAME, 'img').get_attribute("src")
                    download_image(images_folder_paths[index], image_counter, barcode, first_image)
                    image_counter += 1
                except NoSuchElementException:
                    # image is not clickable in Amazon!
                    left_thumbs = driver.find_elements(By.CSS_SELECTOR, 'div#altImages > ul > li.item')
                    for li in left_thumbs:
                        li.click()
                        time.sleep(sleep / 2)
                        image_link = driver.find_element(By.CSS_SELECTOR, 'li.image.item.selected img').get_attribute(
                            'src')
                        download_image(images_folder_paths[index], image_counter, barcode, image_link)
                        image_counter += 1
                image_rows = driver.find_element(By.ID, "ivThumbs").find_elements(By.CSS_SELECTOR, 'div.ivRow')
                time.sleep(sleep)
                # loop through rest of the images
                skipped_first = False
                for row in image_rows:
                    for div in row.find_elements(By.CSS_SELECTOR, 'div.ivThumb'):
                        if not skipped_first and image_counter == 2:  # skip first image of first row
                            skipped_first = True
                            continue
                        time.sleep(sleep / 2)  # wait for image to load
                        div.click()
                        time.sleep(sleep)  # wait for image to load
                        image_link = driver.find_element(By.ID, "ivImagesTab").find_element(By.TAG_NAME,
                                                                                            "img").get_attribute("src")
                        # save images
                        download_image(images_folder_paths[index], image_counter, barcode, image_link)
                        image_counter += 1

            except ElementNotInteractableException:
                print("THERE ARE NO MORE IMAGES OR FAILED TO LOAD IMAGE LINK!")

            driver.execute_script("window.history.go(-1)")  # go back 1 level
        print("Crawling for barcode *%s* done!" % barcode)
    driver.quit()


def find_product_by_link(
        links: List[str],
        summarized_names: List[str],
        category_ids: list[int],
        primary_brands: list[str],
        images_folder_path: str,
        output_excel_file_path: str,
        sleep=9,
        start_row_number=2,
) -> None:
    if not os.path.exists(images_folder_path):
        os.makedirs(images_folder_path)

    driver = get_driver()
    driver.maximize_window()

    for row_num, (summarized_name, link, category_id, primary_brand) in enumerate(
            zip(summarized_names, links, category_ids, primary_brands)):
        print("Excel row number:  %s" % (int(row_num) + start_row_number))
        time.sleep(sleep / 2)

        print("Crawling link %s ..." % link)
        driver.get(link)  # go to product detail page
        time.sleep(sleep / 2)

        title = driver.find_element(By.ID, "productTitle").text
        if driver.find_element(By.ID, "bylineInfo").text:
            brand_name = driver.find_element(By.ID, "bylineInfo").text[7:]  # trim `Brand: `
        else:
            brand_name = ''
        try:
            aue_price_whole = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole")
            aue_price_fraction = driver.find_element(By.CSS_SELECTOR, "span.a-price-fraction")
            price = aue_price_whole.text + "." + aue_price_fraction.text
        except:
            print("%s has no price!!!" % summarized_name)
            continue

        try:
            features_table = driver.find_element(By.CSS_SELECTOR,
                                                 'div.a-section.a-spacing-small.a-spacing-top-small > table')
            # find all the rows in the table

            ft_rows = features_table.find_elements(By.TAG_NAME, 'tr')
        except Exception:
            ft_rows = []

        # create an empty dictionary to store the data
        features = {}

        # iterate over the rows and extract the key-value pairs
        for ft_row in ft_rows:
            key_element = ft_row.find_element(By.TAG_NAME, "td").find_element(By.TAG_NAME, "span")
            key = key_element.text.strip()
            value_element = ft_row.find_element(By.CLASS_NAME, "a-span9").find_element(By.TAG_NAME, "span")
            value = value_element.text.strip()
            features[key] = value

        try:  # because description may not be available for every product
            product_description_el = driver.find_element(By.ID, "productDescription").find_element(By.TAG_NAME,
                                                                                                   "span")
        except NoSuchElementException:
            product_description_el = None
            print("product has no description!")
        if product_description_el:
            description = product_description_el.text
        else:
            description = ''
        try:  # because about_item may not be available for every product
            about_item_el = driver.find_element(By.CSS_SELECTOR, ".a-unordered-list.a-vertical.a-spacing-mini")
        except NoSuchElementException:
            about_item_el = None
            print("product has no about_item!")
        if about_item_el:
            about_item = '; '.join(parse_ul_list(about_item_el))
        else:
            about_item = ''

        headers = ["LINK", "web_name", "price", "web_description", "web_description2", "brand", "features",
                   "summarized_names", "category_id", "primary_brand"]

        new_row = [
            link,
            title,
            price,
            about_item,
            description,
            brand_name,
            features,
            summarized_name,
            category_id,
            primary_brand
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

        print("Downloading images ...")
        # getting image links
        try:
            image_counter = 1
            driver.find_element(By.ID, "imgTagWrapperId").click()
            time.sleep(sleep)  # wait for first image to load
            try:
                # getting first image
                first_image = driver.find_element(By.CSS_SELECTOR, 'div#ivLargeImage') \
                    .find_element(By.TAG_NAME, 'img').get_attribute("src")
                download_image(images_folder_path, image_counter, summarized_name, first_image)
                image_counter += 1
            except NoSuchElementException:
                # image is not clickable in Amazon!
                left_thumbs = driver.find_elements(By.CSS_SELECTOR, 'div#altImages > ul > li.item')
                for li in left_thumbs[:6]:
                    li.click()
                    time.sleep(sleep / 2)
                    image_link = driver.find_element(By.CSS_SELECTOR, 'li.image.item.selected img').get_attribute('src')
                    download_image(images_folder_path, image_counter, summarized_name, image_link)
                    image_counter += 1
            image_rows = driver.find_element(By.ID, "ivThumbs").find_elements(By.CSS_SELECTOR, 'div.ivRow')
            time.sleep(sleep)
            # loop through rest of the images
            skipped_first = False
            for row in image_rows:
                for div in row.find_elements(By.CSS_SELECTOR, 'div.ivThumb'):
                    if not skipped_first and image_counter == 2:  # skip first image of first row
                        skipped_first = True
                        continue
                    if image_counter > 6:
                        break
                    time.sleep(sleep / 2)  # wait for image to load
                    div.click()
                    time.sleep(sleep)  # wait for image to load
                    image_link = driver.find_element(By.ID, "ivImagesTab").find_element(By.TAG_NAME,
                                                                                        "img").get_attribute("src")
                    # save images
                    download_image(images_folder_path, image_counter, summarized_name, image_link)
                    image_counter += 1

        except ElementNotInteractableException:
            print("THERE ARE NO MORE IMAGES OR FAILED TO LOAD IMAGE LINK!")

        print("Crawling for link %s done!" % link)
    driver.quit()
