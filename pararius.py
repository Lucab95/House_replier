import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
import dotenv
import os
from app_logger.base_logger import logger
from utils.selenium_utils import send_response, launch_chrome_with_remote_debugging, attach_selenium_to_debugger
import time
COMMIT_DB = True
SEND_TELEGRAM = True
AI_EVALUATE = True
dotenv.load_dotenv()
# URL to check
# "https://www.huurwoningen.com/in/rotterdam/stadsdeel/centrum/?price=0-1500&bedrooms=2"
PARARIUS_URL = ["https://www.pararius.com/apartments/rotterdam/city-area-noord/0-1500/2-bedrooms",
               "https://www.pararius.com/apartments/rotterdam/city-area-west/0-1500/2-bedrooms",
               "https://www.pararius.com/apartments/rotterdam/city-area-centrum/0-1500/2-bedrooms",
               "https://www.pararius.com/apartments/rotterdam/city-area-noord/0-2000/3-bedrooms",
               "https://www.pararius.com/apartments/rotterdam/city-area-west/0-2000/3-bedrooms",
               "https://www.pararius.com/apartments/rotterdam/city-area-centrum/0-2000/3-bedrooms"]   

# Telegram settings (replace with your actual token and chat ID)    
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def create_database(db_name="listings.db"):
    """Creates/connects to a SQLite database and creates the listings table if it doesn't exist."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            title TEXT,
            price TEXT,
            location TEXT,
            url TEXT,
            real_estate TEXT,
            date_added TEXT
        )
    ''')
    conn.commit()
    return conn

def fetch_listings(url):
    """Fetches the Pararius page and returns a list of listings with their details."""
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/90.0.4430.93 Safari/537.36')
    }
    if not url.startswith("http"):
        url = "https://" + url
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        logger.error("Error fetching the page:", url,"\n", e)
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    
    listings = []
    for item in soup.find_all("section", class_="listing-search-item"):
        # Try to get a unique id for the listing.
        listing_id = item.get("data-id")
        if not listing_id:
            link = item.find("a", href=True)
            listing_id = link["href"] if link else None
        if not listing_id:
            continue  # Skip if no identifier is found

        # Extract other details (update selectors if needed)
        title_elem = item.find("h2", class_="listing-search-item__title")
        title = title_elem.get_text(strip=True) if title_elem else "No Title"
        
        price_elem = item.find("div", class_="listing-search-item__price")
        price = price_elem.get_text(strip=True) if price_elem else "No Price"
        
        location_elem = item.find("div", class_="listing-search-item__sub-title'")
        location = location_elem.get_text(strip=True) if location_elem else "No Location"

        real_estate_elem = item.find("div", class_="listing-search-item__info")
        if real_estate_elem:
            link_elem = real_estate_elem.find("a", class_="listing-search-item__link")
            if link_elem:
                real_estate = link_elem.get_text(strip=True)
            else:
                real_estate = "None"
        else:
            real_estate = "None"
        
        link_elem = item.find("a", href=True)
        # Ensure the URL is absolute
        # extract the base url from the url
        base_url = url.split("/")[2] 
        base_url = "https://" + base_url
        detail_url = (base_url + link_elem["href"]) if link_elem and link_elem["href"].startswith("/") else (link_elem["href"] if link_elem else "")
        
        listings.append({
            "id": listing_id,
            "title": title,
            "price": price,
            "location": location,
            "url": detail_url,
            "real_estate": real_estate,
            "date_added": datetime.datetime.now().isoformat(),
        })
    return listings

def check_new_listings(conn, listings):
    """Compares fetched listings with the local database and returns new listings."""
    c = conn.cursor()
    new_listings = []
    for listing in listings:
        c.execute("SELECT id FROM listings WHERE id = ?", (listing["id"],))
        result = c.fetchone()
        if result is None:
                new_listings.append(listing)
                if COMMIT_DB:
                    c.execute(
                        "INSERT INTO listings (id, title, price, location, url, date_added, real_estate) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (listing["id"], listing["title"], listing["price"], listing["location"], listing["url"], listing["date_added"], listing["real_estate"])
                    )
                    conn.commit()
    return new_listings

def send_telegram_message(token, chat_id, message):
    """Sends a message to a Telegram chat using a bot."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Error sending Telegram message:", e) 

def main():
    while True:
        conn = create_database()
        total_new_listings = []
        for pararius_url in PARARIUS_URL:
            listings = fetch_listings(pararius_url)
            if not listings:
                logger.error("No listings found or error fetching the page.")
            new_listings = check_new_listings(conn, listings)
            if new_listings:
                total_new_listings += new_listings
        if total_new_listings:
            chrome_process = launch_chrome_with_remote_debugging()
            driver = attach_selenium_to_debugger()
            for listing in total_new_listings:
                print("\n\n")
                if "pararius" in listing["url"]:
                    send_message = send_response(driver, listing["url"], listing["price"], AI_EVALUATE)
                    driver.get("https://www.google.com")

                message = (
                    f"*New Listing Found!*\n"
                    f"*Title:* {listing['title']}\n"
                    f"*Price:* {listing['price']}\n"
                    f"*Location:* {listing['location']}\n"
                    f"*Real Estate:* {listing['real_estate']}\n"
                    f"[View Listing]({listing['url']})\n"
                    f"*Date Added:* {listing['date_added']}\n"
                    f"*Sent reply:* {send_message}"

                )
                title = str(listing["title"])
                price = str(listing["price"])
                real_estate = str(listing["real_estate"])
                url = str(listing["url"])
                printer = f"sent:{send_message} -- {title} -- {price} -- {real_estate} -- {url}"
                
                logger.info(printer)
            
                if SEND_TELEGRAM:
                    send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
                print("\n\n")
            driver.quit()
            chrome_process.terminate()
            chrome_process.wait()
            logger.info(f"{len(total_new_listings)} new listings sent to Telegram")
        else:
            logger.info(f"No new listings found")
        conn.close()
        time.sleep(25)

if __name__ == "__main__":
    main()
