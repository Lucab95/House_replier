from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import subprocess
import os
from base_logger import logger
import random
from selenium.common.exceptions import TimeoutException
failed = False

def launch_chrome_with_remote_debugging():
    cmd = [
        "google-chrome",
        "--remote-debugging-port=9222",
        "--user-data-dir=/home/brglt/.config/google-chrome/AutomationProfile",
        "--profile-directory=Profile 2"
    ]
    # preexec_fn=os.setsid starts Chrome in a new process group.
    return subprocess.Popen(cmd, preexec_fn=os.setsid)

def attach_selenium_to_debugger():
    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    driver = webdriver.Chrome(options=options)
    return driver


def send_response(driver, url):

    driver.get(url)
    wait = WebDriverWait(driver, 15)
    try:
        # Adjust the CSS selector as needed based on the actual page structure
        description_elem = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-detail-description__additional"))
        )
        description = description_elem.text
        print("Description content:")
        print(description)

        # Wait for and click the "Contact the estate agent" button
        contact_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.listing-reaction-button--contact-agent"))
        )
        #check if contact button is there
        if contact_button is None:
            logger.error("Contact button not found, skipping")
            return False
        # time.sleep(10)
        driver.execute_script("arguments[0].scrollIntoView(true);", contact_button)
        driver.execute_script("arguments[0].click();", contact_button)
        logger.info("Clicked 'Contact the estate agent' button.")
        # driver.quit()
        
        #between 1 and 10 seconds
        time.sleep(random.randint(1, 10))

        # Wait for and click the "Send" button on the next page
        send_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.form__button--submit"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", send_button)
        driver.execute_script("arguments[0].click();", send_button)
        logger.info("Clicked 'Send' button.")
        
        #check for the listing-reactions-counter__details
        reactions_counter = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-reactions-counter__details"))
        )
        if reactions_counter is None:
            logger.error("Reactions counter not found")
            return False
        return True
    except Exception as e:
        logger.error("Error clicking 'Send' button:", e)
        return False
    finally:
        driver.get("https://www.google.com")
        # driver.quit()

