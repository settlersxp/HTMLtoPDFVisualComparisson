import shutil

from pdfreader import SimplePDFViewer
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import argparse

product_images_not_found = []
images_too_tall = []
unknown_scenarios = []
multiple_images_per_html = []

PRODUCT_IMAGE_CSS_SELECTOR = ".product-image"
IMAGE_CONTAINER_CSS_SELECTOR = "div.dimensions-container"
IMAGES_FOLDER = os.path.join("images")
LOCATION_FOLDER = ""
# shutil.rmtree(IMAGES_FOLDER, ignore_errors=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)


def image_is_invalid(image_element):
    return image_element.get_attribute("src") == "" and image_element.get_property("offsetHeight") == 0


def get_path_of_order_images(file):
    return os.path.join(IMAGES_FOLDER, file)


def construct_image_path(file, image_number):
    return os.path.join(get_path_of_order_images(file), f"{image_number}.png")


def check_if_the_image_is_taller_than_the_container(driver, file):
    # get the CSS height of the container IMAGE_CONTAINER_CSS_SELECTOR
    containers = driver.find_elements(By.CSS_SELECTOR, IMAGE_CONTAINER_CSS_SELECTOR)
    number_of_fakes = containers.__len__()
    for container in containers:
        container_height = container.get_property("offsetHeight")
        if container_height > 0:
            container.screenshot("container.png")

        # get the CSS height of the image PRODUCT_IMAGE_CSS_SELECTOR
        image = container.find_element(By.CSS_SELECTOR, PRODUCT_IMAGE_CSS_SELECTOR)
        if image_is_invalid(image):
            number_of_fakes -= 1
            continue

        # if the image is taller than the container add the file name to the list of files called "images_too_tall"
        if image.get_property("offsetHeight") > container_height:
            images_too_tall.append(file)


def extract_all_the_images_found(driver, file):
    # append to the folder found in the IMAGES_FOLDER the name of the file
    order_images_folder = os.path.join(IMAGES_FOLDER, file)
    os.makedirs(order_images_folder, exist_ok=True)

    # get the CSS height of the container IMAGE_CONTAINER_CSS_SELECTOR
    containers = driver.find_elements(By.CSS_SELECTOR, IMAGE_CONTAINER_CSS_SELECTOR)
    image_number = 0
    for container in containers:
        # get the CSS height of the image PRODUCT_IMAGE_CSS_SELECTOR
        image = container.find_element(By.CSS_SELECTOR, PRODUCT_IMAGE_CSS_SELECTOR)
        if image_is_invalid(image):
            continue

        image_path = construct_image_path(file, image_number)
        image.screenshot(image_path)


def check_that_no_html_has_more_than_one_image(file):
    order_folder = get_path_of_order_images(file)
    images_found = os.walk(order_folder)
    if len(list(images_found)) > 1:
        multiple_images_per_html.append(file)


def check_that_the_order_image_exists_in_the_pdf(file):
    image_path = get_path_of_order_images(file)
    pdf_folder = os.path.join(image_path, 'pdf')
    os.makedirs(pdf_folder, exist_ok=True)

    fd = open(os.path.join(LOCATION_FOLDER, file + ".pdf"), "rb")
    viewer = SimplePDFViewer(fd)
    viewer.render()
    for canvas in viewer:
        for image_name, image_data in canvas.images.items():
            image_data.to_Pillow().save(os.path.join(pdf_folder, f'{image_name}.png'))

def main_program():
    # read all the files in the folder
    files = os.listdir(LOCATION_FOLDER)

    # the files in the folder represent pairs of files with the .html and .pdf extensions. Every time such a pair is found, the name of the file should be put in a list.
    files_to_analyze = extract_list_of_files_to_analyze(files)

    # Set up headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    chrome_service = webdriver.ChromeService()

    with webdriver.Chrome(service=chrome_service, options=chrome_options) as driver:
        for file in files_to_analyze:
            print(f"Analyzing file: {file}")
            # render the html file in a headless browser and identify if the element with the class "product_image" is present
            html_file_path = os.path.join(LOCATION_FOLDER, file + ".html")

            driver.get(f"file://{html_file_path}")

            try:
                if not check_if_it_has_image(driver, file):
                    continue

                check_if_the_image_is_taller_than_the_container(driver, file)

                extract_all_the_images_found(driver, file)

                check_that_no_html_has_more_than_one_image(file)

                # check_that_the_order_image_exists_in_the_pdf(file)

            except Exception as e:
                unknown_scenarios.append((file, e))

            print(f"Done with: {file}")
            # if the element is not present add the file name to the list of files called "product_images_not_found" and continue to the next file
            # if the element is present download the image and check if the same image exists in the .pdf file

    print("Orders without product images: ", product_images_not_found)
    print("Images too tall: ", images_too_tall)
    print("Multiple images per html: ", multiple_images_per_html)
    print("Unknown scenarios: ", unknown_scenarios)


def check_if_it_has_image(driver, file):
    # some images might be hidden/fake, so we need to check if the image is visible
    all_images = driver.find_elements(By.CSS_SELECTOR, PRODUCT_IMAGE_CSS_SELECTOR)
    if len(all_images) == 0:
        product_images_not_found.append(file)
        return False

    # check if the image has a src attribute equal to an empty string because the fake ones do
    maximum_number_of_fakes = all_images.__len__()
    for image in all_images:
        if image_is_invalid(image):
            maximum_number_of_fakes -= 1

    return maximum_number_of_fakes > 0


def extract_list_of_files_to_analyze(files):
    files_to_analyze = []
    for file in files:
        if file.endswith(".html"):
            file_name = file.split(".")[0]
            # this condition excludes the files that do not have a pair
            if file_name + ".pdf" in files:
                files_to_analyze.append(file_name)
    return files_to_analyze


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Files folder location")
    parser.add_argument("location_folder", type=str, help="Folder location")
    args = parser.parse_args()
    LOCATION_FOLDER = args.location_folder
    main_program()
