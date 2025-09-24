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
from openai import OpenAI


dotenv.load_dotenv()

# Pararius login credentials
PARARIUS_USERNAME = os.getenv("PARARIUS_USERNAME")
PARARIUS_PASSWORD = os.getenv("PARARIUS_PASSWORD")
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("OPENROUTER_API_KEY")
client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
    )
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
                logger.warning("Pararius credentials not found in .env file; please log in manually in the opened browser.")
                return driver
            
            # Navigate to login page
            driver.get("https://www.pararius.com/login-email")
            time.sleep(2)
            try:
                # Find and fill email field (wait for visibility)
                email_field = WebDriverWait(driver, 8).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
                )
                email_field.clear()
                email_field.send_keys(PARARIUS_USERNAME)

                # Password field may or may not be present (magic-link vs password login)
                pw_fields = driver.find_elements(By.CSS_SELECTOR, "input[name='password']")
                if pw_fields:
                    pw = pw_fields[0]
                    pw.clear()
                    pw.send_keys(PARARIUS_PASSWORD)

                # Click sign in/continue button
                submit_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                driver.execute_script("arguments[0].click();", submit_btn)
                time.sleep(3)

                # Verify login was successful (no login links present)
                login_check = driver.find_elements(By.XPATH, "//a[contains(@href, 'login') or contains(text(), 'Login') or contains(text(), 'login')]")
                if not login_check:
                    logger.info("Successfully logged in via Selenium")
                else:
                    logger.warning("Login may not have completed; continuing.")
            except Exception as e:
                logger.error("Error during login process: %s", e)
        else:
            logger.info("Already logged in")
            
    except Exception as e:
        logger.error("Error checking login status: %s", e)
    
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
    # Try to detect either the 'view reaction' (already contacted) or the 'contact agent' button.
    try:
        # 1) Check for 'view reaction' button (a or button, by class or by text)
        view_btns = []
        view_btns.extend(driver.find_elements(By.CSS_SELECTOR, "a.listing-reaction-button--view-reaction"))
        view_btns.extend(driver.find_elements(By.CSS_SELECTOR, "button.listing-reaction-button--view-reaction"))
        if not view_btns:
            view_btns.extend(driver.find_elements(By.XPATH, "//a[contains(., 'View your reaction') or contains(., 'View reaction')]"))
            view_btns.extend(driver.find_elements(By.XPATH, "//button[contains(., 'View your reaction') or contains(., 'View reaction')]"))
        if view_btns:
            logger.info("'View reaction' button present; skipping contact.")
            return False

        # 2) Otherwise wait until a 'contact' button is available and clickable.
        def find_clickable_contact(drv):
            candidates = []
            # By specific class
            candidates.extend(drv.find_elements(By.CSS_SELECTOR, "a.listing-reaction-button--contact-agent"))
            candidates.extend(drv.find_elements(By.CSS_SELECTOR, "button.listing-reaction-button--contact-agent"))
            # By text match (English/Dutch)
            candidates.extend(drv.find_elements(By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact')]"))
            candidates.extend(drv.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact')]"))
            for el in candidates:
                if el.is_displayed() and el.is_enabled():
                    return el
            return False

        contact_button = WebDriverWait(driver, 12).until(find_clickable_contact)
        try:
            logger.info("Contact button text: %s", contact_button.text)
        except Exception:
            pass
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", contact_button)
        driver.execute_script("arguments[0].click();", contact_button)
        logger.info("Clicked 'Contact the estate agent' button.")
        # If click causes a login redirect, just report False (avoid exception loops)
        time.sleep(1)
        try:
            if any(k in (driver.current_url or '') for k in ["/login", "/account/login", "/login-email"]):
                logger.info("Redirected to login after clicking contact; skipping this listing.")
                return False
        except Exception:
            pass
        return True
    except TimeoutException:
        logger.info("Contact button not found within timeout.")
        return False
    except Exception as e:
        logger.error("Error while trying to click contact/view button: %s", e)
        return False
    
def __send_response_to_agent(driver, wait):
        # Wait for and click the "Send" button on the next page
        try:
            send_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.form__button--submit"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", send_button)
            driver.execute_script("arguments[0].click();", send_button)
            logger.info("Clicked 'Send' button.")
            time.sleep(2)
            return True
        except TimeoutException:
            logger.info("Send button not found within timeout.")
            return False
        except Exception as e:
            logger.error("Error clicking send button: %s", e)
            return False
        
       


def send_response(driver, url, price, AI_EVALUATE):
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    reason = "No ai involvement"
    try:
        logger.info("AI EVALUATE is: " + str(AI_EVALUATE))
        if AI_EVALUATE:
            description = __get_description(wait)
            if description:
                # pass it to the ai
                ai_response, reason = get_ai_response(description, price, client)
                logger.info(f"AI response: {ai_response}, Reason: {reason}")
                if not ai_response:
                    return False, reason
        if __get_contact_agent(driver, wait):
            #between 1 and 10 seconds
            time.sleep(random.randint(1, 10))
            
            if __send_response_to_agent(driver, wait):
                logger.info("Response sent successfully")
                return True, reason
            return False, reason
        return False, reason
    except Exception as e:
        logger.error("Error occurred: %s", e)
        return False, reason
