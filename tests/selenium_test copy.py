# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options

# options = Options()
# # Replace with the path to your Chrome user data directory
# options.add_argument("user-data-dir=/home/brglt/.config/google-chrome")
# # Replace "Default" with the profile folder name if needed (e.g., "Profile 1")
# options.add_argument("--profile-directory=Profile 2")

# driver = webdriver.Chrome(options=options)
# driver.get("https://www.pararius.com")
# input("Press Enter to exit and close the browser...")


import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def launch_chrome_with_remote_debugging():
    """
    Launches Chrome with remote debugging on port 9222 using Profile 2.
    Returns the Popen object so we can manage the process if needed.
    """
    cmd = [
        "google-chrome",
        "--remote-debugging-port=9222",
        "--user-data-dir=/home/brglt/.config/google-chrome",
        "--profile-directory=Profile 2"
    ]
    return subprocess.Popen(cmd)

def attach_selenium_to_debugger():
    """
    Creates a Selenium driver that attaches to the already running
    Chrome instance on localhost:9222.
    """
    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    driver = webdriver.Chrome(options=options)
    return driver

if __name__ == "__main__":
    # 1. Launch Chrome in the background
    chrome_process = launch_chrome_with_remote_debugging()

    # 2. Give Chrome a moment to start up (or implement a more robust check)
    time.sleep(3)

    # 3. Attach Selenium to the running Chrome instance
    driver = attach_selenium_to_debugger()

    # 4. Do whatever you need with Selenium
    driver.get("https://www.pararius.com")
    print("Selenium is attached to the running Chrome session.")
    
    # Keep the script running so you can see what's happening
    # input("Press Enter to exit...")
    time.sleep(3)
    driver.quit()

    # 5. Optionally kill the Chrome process when you're done
    chrome_process.terminate()
    chrome_process.wait()

