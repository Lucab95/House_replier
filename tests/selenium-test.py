import subprocess
import time
import os
import signal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils import launch_chrome_with_remote_debugging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def attach_selenium_to_debugger():
    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    driver = webdriver.Chrome(options=options)
    print("Selenium attached to the running Chrome session.")
    return driver

if __name__ == "__main__":
    # 1. Launch Chrome with remote debugging in its own process group
    chrome_process = launch_chrome_with_remote_debugging()
    print("Chrome process launched.")
    # 2. Wait a bit for Chrome to start up
    time.sleep(3)
    print("Chrome started.")
    # 3. Attach Selenium to the running Chrome instance
    driver = attach_selenium_to_debugger()
    print("Selenium attached to the running Chrome session.")
    
    driver.get("https://www.pararius.com/apartment-for-rent/rotterdam/c3ddeafb/hoogstraat")

    #
    wait = WebDriverWait(driver, 10)
    # Wait for the button to be present
    try:
        button = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "button.listing-detail-description__button"))
        )
        button.click()
        print("Clicked the description button.")
    except Exception as e:
        print(f"Could not click the description button: {e}")

    try:
        description_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-detail-description__additional"))
            )
        print("Description content:")
        print(description_elem.text)
        #write to file
        with open("description.txt", "w") as f:
            f.write(description_elem.text)
    except Exception as e:
        print(f"Could not find the description content: {e}")

    # 4. Wait for user input before closing everything
    input("Press Enter to exit and close the browser...")

    # 5. Close Selenium's browser window
    driver.quit()

    # 6. Kill the entire Chrome process group
    chrome_process.terminate()
    chrome_process.wait()
    print("Chrome process terminated.")

