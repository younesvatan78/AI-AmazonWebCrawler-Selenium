import pandas as pd

from amazon import find_product_by_barcode as amazon_find_product_by_barcode, \
    find_product_by_link as amazon_find_product_by_link
from nutrend import find_product_by_name as nutrend_find_product_by_name

default_input_excel_file_path = "input.xlsx"
default_output_images_folder_path = "img"
default_output_excel_file_path = "results.xlsx"
default_sleep = 8
default_start_row_number = 2

if __name__ == '__main__':

    input_excel_file_path = input(
        "Specify the input excel file path: (default is `%s`) " % default_input_excel_file_path)
    if not input_excel_file_path:
        input_excel_file_path = default_input_excel_file_path

    input_data = pd.read_excel(input_excel_file_path.split('.')[0] + ".xlsx")

    images_folder_path = input(
        "Specify the image folder path: (default is `%s`) " % default_output_images_folder_path)
    if not images_folder_path:
        images_folder_path = default_output_images_folder_path

    output_excel_file_path = input(
        "Specify the output EXCEL file path: (default is `%s`) " % default_output_excel_file_path)
    if not output_excel_file_path:
        output_excel_file_path = default_output_excel_file_path

    sleep = input("Specify the sleep time (sec): (default is `%s`) " % default_sleep)
    if sleep == '':
        sleep = default_sleep
    else:
        sleep = int(sleep)

    start_row_number = input("Specify the start row number: (default: start from beginning) ")
    if start_row_number == '':
        start_row_number = default_start_row_number
    else:
        start_row_number = int(start_row_number)

    target_site = int(input("Select target website to crawl:\n1.Amazon (barcode)\n2.Nutrend\n3.Amazon (link)\n"))
    if target_site == 1:
        amazon_find_product_by_barcode(
            barcodes=input_data['BARCODE'].to_list()[start_row_number - 2:],
            sleep=sleep,
            images_folder_path=images_folder_path,
            output_excel_file_path=output_excel_file_path,
            start_row_number=start_row_number
        )
    elif target_site == 2:
        nutrend_find_product_by_name(
            names=input_data['NAMES'].to_list()[start_row_number - 2:],
            sleep=sleep,
            images_folder_path=images_folder_path,
            output_excel_file_path=output_excel_file_path,
            start_row_number=start_row_number
        )
    elif target_site == 3:
        amazon_find_product_by_link(
            links=input_data['LINKS'].to_list()[start_row_number - 2:],
            summarized_names=input_data['summarized_names'].to_list()[start_row_number - 2:],
            category_ids=input_data['category_id'].to_list()[start_row_number - 2:],
            primary_brands=input_data['primary_brand'].to_list()[start_row_number - 2:],
            images_folder_path=images_folder_path,
            output_excel_file_path=output_excel_file_path,
            sleep=sleep,
            start_row_number=start_row_number
        )
