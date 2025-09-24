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
HUURWONINGEN_USERNAME = os.getenv("HUURWONINGEN_USERNAME")
HUURWONINGEN_PASSWORD = os.getenv("HUURWONINGEN_PASSWORD")
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

def attach_selenium_to_debugger(auto_login=True):
    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    driver = webdriver.Chrome(options=options)
    if auto_login:
        ensure_pararius_login(driver)
    return driver


def ensure_pararius_login(driver):
    """Ensure the active session is authenticated on Pararius."""
    try:
        driver.get("https://www.pararius.com")
        time.sleep(2)

        login_elements = driver.find_elements(
            By.XPATH,
            "//a[contains(@href, 'login') or contains(text(), 'Login') or contains(text(), 'Sign in')]",
        )

        if not login_elements:
            logger.info("Already logged in on Pararius")
            return

        logger.info("Not logged in on Pararius, attempting automatic login...")
        if not PARARIUS_USERNAME or not PARARIUS_PASSWORD:
            logger.warning(
                "Pararius credentials not found in environment; please log in manually in the opened browser."
            )
            return

        driver.get("https://www.pararius.com/login-email")
        time.sleep(2)
        try:
            email_field = WebDriverWait(driver, 8).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
            )
            email_field.clear()
            email_field.send_keys(PARARIUS_USERNAME)

            pw_fields = driver.find_elements(By.CSS_SELECTOR, "input[name='password']")
            if pw_fields:
                pw = pw_fields[0]
                pw.clear()
                pw.send_keys(PARARIUS_PASSWORD)

            submit_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(3)

            login_check = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, 'login') or contains(text(), 'Login') or contains(text(), 'login')]",
            )
            if not login_check:
                logger.info("Successfully logged in to Pararius")
            else:
                logger.warning("Pararius login may not have completed; continuing.")
        except Exception as exc:
            logger.error("Error during Pararius login process: %s", exc)
    except Exception as exc:
        logger.error("Error checking Pararius login status: %s", exc)


def ensure_huurwoningen_login(driver):
    """Ensure the active session is authenticated on Huurwoningen."""
    try:
        driver.get("https://www.huurwoningen.com/inloggen")
        time.sleep(3)

        if "inloggen" not in (driver.current_url or "").lower():
            logger.info("Already logged in on Huurwoningen")
            return

        if not HUURWONINGEN_USERNAME or not HUURWONINGEN_PASSWORD:
            logger.warning(
                "Huurwoningen credentials not found in environment; please log in manually in the opened browser."
            )
            return
        driver.get("https://www.huurwoningen.com/account/inloggen-email/?_target_path=/")
        def _first_visible(locator_list):
            for by, value in locator_list:
                elems = driver.find_elements(by, value)
                for elem in elems:
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
            return None

        email_field = _first_visible(
            [
                (By.CSS_SELECTOR, "input[name='email']"),
                (By.CSS_SELECTOR, "input[id*='email']"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.XPATH, "//input[contains(translate(@name, 'EMAIL', 'email'), 'email')]")
            ]
        )
        password_field = _first_visible(
            [
                (By.CSS_SELECTOR, "input[name='password']"),
                (By.CSS_SELECTOR, "input[id*='password']"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[contains(translate(@name, 'PASSWORD', 'password'), 'pass')]")
            ]
        )

        if not email_field or not password_field:
            logger.warning("Could not locate Huurwoningen login form automatically; manual login required.")
            return

        email_field.clear()
        email_field.send_keys(HUURWONINGEN_USERNAME)
        password_field.clear()
        password_field.send_keys(HUURWONINGEN_PASSWORD)

        login_button = _first_visible(
            [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "button[data-testid*='login']"),
                (By.XPATH, "//button[contains(., 'Inloggen') or contains(., 'Log in')]")
            ]
        )
        if not login_button:
            logger.warning("Could not locate Huurwoningen login button; manual login required.")
            return

        driver.execute_script("arguments[0].click();", login_button)
        WebDriverWait(driver, 10).until(lambda d: "inloggen" not in (d.current_url or "").lower())
        logger.info("Successfully logged in to Huurwoningen")
    except TimeoutException:
        logger.warning("Huurwoningen login did not complete before timeout; please verify manually.")
    except Exception as exc:
        logger.error("Error during Huurwoningen login process: %s", exc)

def __get_description(wait,domain):
    try:
        button = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "button.listing-detail-description__button"))
            )
        time.sleep(5)
        button.click()
        logger.info("Clicked the description button.")
        
        if "huurwoningen.com" in domain:
            description_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-detail-description__truncated"))
            )
            logger.info(f"Description content:\n\n{description_elem.text}")
            return description_elem.text
        elif "pararius" in domain:
            
            description_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-detail-description__additional"))
                )
        logger.info(f"Description content:\n\n{description_elem.text}")
    except Exception as e:
        logger.error("Error getting description: %s", e)
        return None
    return description_elem.text

def __get_contact_agent(driver, wait, domain):
    # Try to detect either the 'view reaction' (already contacted) or the 'contact agent' button.
    try:
        domain = (domain or "").lower()

        if "huurwoningen.com" in domain:
            def find_clickable_contact(drv):
                candidates = []
                selectors = [
                    "a.listing-contact-info__button--contact-request",
                    "button.listing-contact-info__button--contact-request",
                    "a.listing-contact-info__button",
                    "button.listing-contact-info__button",
                ]
                for selector in selectors:
                    candidates.extend(drv.find_elements(By.CSS_SELECTOR, selector))

                text_queries = [
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'respond')]",
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'respond')]",
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reageer')]",
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reageer')]",
                ]
                for xpath in text_queries:
                    candidates.extend(drv.find_elements(By.XPATH, xpath))

                for el in candidates:
                    if el.is_displayed() and el.is_enabled():
                        return el
                return False

            contact_button = WebDriverWait(driver, 12).until(find_clickable_contact)
        else:
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
    
def __send_response_to_agent(driver, wait, domain):
        # Wait for and click the "Send" button on the next page
        try:
            #check this
            if "pararius" in domain:
                send_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.form__button--submit"))
                )
            elif "huurwoningen" in domain:
                send_button = None
                selectors = [
                    "button.button--secondary[type='submit']",
                    "button.button--primary[type='submit']",
                    "button[type='submit']",
                ]
                for selector in selectors:
                    try:
                        send_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if send_button:
                            break
                    except TimeoutException:
                        continue
                if not send_button:
                    text_xpaths = [
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send message')]",
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verzend')]",
                    ]
                    for xpath in text_xpaths:
                        try:
                            send_button = wait.until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            if send_button:
                                break
                        except TimeoutException:
                            continue
                if not send_button:
                    raise TimeoutException("Unable to locate Huurwoningen send button")
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
        
       


def send_response(driver, url, price, AI_EVALUATE, domain):
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    reason = "No ai involvement"
    try:
        logger.info("AI EVALUATE is: " + str(AI_EVALUATE))
        if AI_EVALUATE:
            description = __get_description(wait, domain)
            if description:
                # pass it to the ai
                ai_response, reason = get_ai_response(description, price, client)
                logger.info(f"AI response: {ai_response}, Reason: {reason}")
                if not ai_response:
                    return False, reason
        if __get_contact_agent(driver, wait, domain):
            #between 1 and 10 seconds
            time.sleep(random.randint(1, 10))
            
            if __send_response_to_agent(driver, wait, domain):
                logger.info("Response sent successfully")
                return True, reason
            return False, reason
        return False, reason
    except Exception as e:
        logger.error("Error occurred: %s", e)
        return False, reason
