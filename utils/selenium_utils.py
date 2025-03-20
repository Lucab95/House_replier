from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import subprocess
import os
from app_logger.base_logger import logger
import random
from selenium.common.exceptions import TimeoutException
from utils.GPT import get_ai_response

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

def __get_description(wait):
    try:
        button = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "button.listing-detail-description__button"))
        )
        button.click()
        logger.info("Clicked the description button.")

        description_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-detail-description__additional"))
            )
        logger.info(f"Description content:\n\n{description_elem.text}")
    except Exception as e:
        logger.error("Error getting description:", e)
        return None
    return description_elem.text

def __get_contact_agent(driver, wait):
    # Wait for and click the "Contact the estate agent" button
    #check if it exists
    try:
        contact_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.listing-reaction-button--contact-agent"))
        )
    except:
        logger.info("Contact button not found")
        return False
    # time.sleep(10)
    driver.execute_script("arguments[0].scrollIntoView(true);", contact_button)
    driver.execute_script("arguments[0].click();", contact_button)
    logger.info("Clicked 'Contact the estate agent' button.")
    return True
    
def __send_response_to_agent(driver, wait):
        # Wait for and click the "Send" button on the next page
        send_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.form__button--submit"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", send_button)
        driver.execute_script("arguments[0].click();", send_button)
        logger.info("Clicked 'Send' button.")
        time.sleep(2)
        
        # #check for the listing-reactions-counter__details
        # reactions_counter = wait.until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-reactions-counter__details"))
        # )
        # if reactions_counter is None:
        #     logger.error("Reactions counter not found")


def send_response(driver, url, price, AI_EVALUATE):
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    try:
        if AI_EVALUATE:
            description = __get_description(wait)
            if description:
                # pass it to the ai
                ai_response, reason = get_ai_response(description, price)
                logger.info(f"AI response: {ai_response},Reason: {reason}")
                if not ai_response:
                    return False
        if __get_contact_agent(driver, wait):
            #between 1 and 10 seconds
            time.sleep(random.randint(1, 10))
            
            # __send_response_to_agent(driver, wait)
            logger.info("Response sent successfully")
            return True
        else:
            return False
    except Exception as e:
        logger.error("Error occurred:", e)
        return False
