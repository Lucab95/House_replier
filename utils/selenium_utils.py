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
import dotenv

dotenv.load_dotenv()

# Pararius login credentials
PARARIUS_USERNAME = os.getenv("PARARIUS_USERNAME")
PARARIUS_PASSWORD = os.getenv("PARARIUS_PASSWORD")

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
    
    # Check if login is needed
    try:
        driver.get("https://www.pararius.com")
        time.sleep(2)
        
        # Check for login indicator in the top navigation
        login_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'login') or contains(text(), 'Login') or contains(text(), 'Sign in')]")
        
        if login_elements:
            logger.info("Not logged in, attempting automatic login...")
            
            if not PARARIUS_USERNAME or not PARARIUS_PASSWORD:
                logger.error("Pararius credentials not found in .env file")
                return driver
            
            # Navigate to login page
            driver.get("https://www.pararius.com/login-email")
            time.sleep(3)
            
            try:
                # Find and fill email field
                email_field = driver.find_element(By.CSS_SELECTOR, "input[name='email']")
                email_field.clear()
                email_field.send_keys(PARARIUS_USERNAME)
                
                # Find and fill password field
                password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
                password_field.clear()
                password_field.send_keys(PARARIUS_PASSWORD)
                
                # Click sign in button
                sign_in_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                sign_in_button.click()
                
                time.sleep(5)  # Wait for login to complete
                
                # Verify login was successful
                login_check = driver.find_elements(By.XPATH, "//a[contains(@href, 'login') or contains(text(), 'Login') or contains(text(), 'Sign in')]")
                if not login_check:
                    logger.info("Successfully logged in via Selenium")
                else:
                    logger.error("Login appears to have failed")
                    
            except Exception as e:
                logger.error(f"Error during login process: {e}")
        else:
            logger.info("Already logged in")
            
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
    
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
        logger.error("Error getting description: %s", e)
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
        
       


def send_response(driver, url, price, AI_EVALUATE):
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    try:
        logger.info("AI EVALUATE is: " + str(AI_EVALUATE))
        if AI_EVALUATE:
            logger.info("AI EVALUATE is True")
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
            
            __send_response_to_agent(driver, wait)
            logger.info("Response sent successfully")
            
            return True
        else:
            return False
    except Exception as e:
        logger.error("Error occurred: %s", e)
        return False
