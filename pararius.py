import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
import dotenv
import os
import json
import re
from urllib.parse import urlparse
from app_logger.base_logger import logger
from utils.selenium_utils import send_response, launch_chrome_with_remote_debugging, attach_selenium_to_debugger
import time
COMMIT_DB = True
SEND_TELEGRAM = True
AI_EVALUATE = False
USE_JSON_LD = True
dotenv.load_dotenv()
# URL to check
# "https://www.huurwoningen.com/in/rotterdam/stadsdeel/centrum/?price=0-1500&bedrooms=2"
PARARIUS_URL = ["https://www.pararius.com/apartments/rotterdam/studio/0-1600",
               "https://www.pararius.com/apartments/rotterdam/apartment/0-1600"]   

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
            date_added TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')
    # Ensure columns exist for older DBs
    try:
        c.execute("PRAGMA table_info(listings)")
        cols = {row[1] for row in c.fetchall()}
        if 'latitude' not in cols:
            c.execute("ALTER TABLE listings ADD COLUMN latitude REAL")
        if 'longitude' not in cols:
            c.execute("ALTER TABLE listings ADD COLUMN longitude REAL")
    except Exception:
        pass
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
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logger.error("Error fetching the page: %s\n%s", url, e)
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
        
        # NOTE: class name apostrophe in original selector caused misses
        location_elem = item.find("div", class_="listing-search-item__sub-title")
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


def _extract_itemlist_from_jsonld(data):
    """Traverse JSON-LD dict to find an ItemList node."""
    if not isinstance(data, (dict, list)):
        return None
    if isinstance(data, list):
        for node in data:
            found = _extract_itemlist_from_jsonld(node)
            if found:
                return found
        return None
    # dict case
    type_field = data.get("@type")
    if type_field == "ItemList" or (isinstance(type_field, list) and "ItemList" in type_field):
        return data
    main_entity = data.get("mainEntity")
    if isinstance(main_entity, dict):
        found = _extract_itemlist_from_jsonld(main_entity)
        if found:
            return found
    graph = data.get("@graph")
    if isinstance(graph, list):
        for node in graph:
            found = _extract_itemlist_from_jsonld(node)
            if found:
                return found
    return None


def _extract_id_from_url(abs_url: str) -> str:
    """Extract a stable listing id from a Pararius listing URL.

    Expected path formats like:
      /studio-for-rent/{city}/{id}/{slug}
      /apartment-for-rent/{city}/{id}/{slug}
    Falls back to full URL if pattern is unexpected.
    """
    try:
        parsed = urlparse(abs_url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 3:
            return parts[2]
    except Exception:
        pass
    return abs_url


def fetch_listings_jsonld(url):
    """Fetch listings using JSON-LD embedded on the search page (ItemList).

    Returns the same listing dict structure as fetch_listings().
    """
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/113.0.0.0 Safari/537.36')
    }
    if not url.startswith("http"):
        url = "https://" + url
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logger.error("Error fetching the page for JSON-LD: %s\n%s", url, e)
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    itemlist = None
    for s in scripts:
        try:
            # Some scripts may contain HTML-escaped content; use .string safely
            content = s.string or s.get_text()
            data = json.loads(content)
        except Exception:
            continue
        itemlist = _extract_itemlist_from_jsonld(data)
        if itemlist:
            break

    if not itemlist:
        logger.warning("No ItemList found in JSON-LD on page: %s", url)
        return []

    elements = itemlist.get("itemListElement") or []
    listings = []
    for elem in elements:
        item = (elem or {}).get("item") or {}
        abs_url = item.get("url") or item.get("@id") or ""
        if not abs_url:
            continue
        listing_id = _extract_id_from_url(abs_url)
        title = item.get("name") or "No Title"

        offers = item.get("offers") or {}
        price = offers.get("price")
        price_currency = offers.get("priceCurrency") or "EUR"
        if price is not None:
            try:
                price_val = int(float(price))
                price_str = f"€{price_val} per month" if price_currency == "EUR" else f"{price_currency} {price_val} per month"
            except Exception:
                price_str = str(price)
        else:
            price_str = "No Price"

        # Best-effort location: derive city from URL path (second segment)
        try:
            city_slug = urlparse(abs_url).path.strip("/").split("/")[1]
            location = city_slug.replace("-", " ").title()
        except Exception:
            location = "No Location"

        listings.append({
            "id": listing_id,
            "title": title,
            "price": price_str,
            "location": location,
            "url": abs_url,
            "real_estate": "None",
            "date_added": datetime.datetime.now().isoformat(),
        })

    return listings


def fetch_listing_coordinates(detail_url):
    """Fetch latitude/longitude from a listing detail page.

    Looks for the <wc-detail-map> component and reads data-latitude/data-longitude.
    Returns a tuple (lat, lon) as floats when found, otherwise (None, None).
    """
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/113.0.0.0 Safari/537.36')
    }
    try:
        resp = requests.get(detail_url, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Error fetching detail page for coordinates: %s\n%s", detail_url, e)
        return None, None

    soup = BeautifulSoup(resp.content, "html.parser")
    el = soup.find("wc-detail-map")
    if not el:
        # Some pages might use a different tag naming or render client-side only
        # Try a broader search just in case
        el = soup.find(attrs={"data-latitude": True, "data-longitude": True})
    if not el:
        return None, None
    try:
        lat = float(el.get("data-latitude"))
        lon = float(el.get("data-longitude"))
        return lat, lon
    except Exception:
        return None, None

def check_new_listings(conn, listings):
    """Compares fetched listings with the local database and returns new listings."""
    c = conn.cursor()
    new_listings = []
    for listing in listings:
        c.execute("SELECT id FROM listings WHERE id = ?", (listing["id"],))
        result = c.fetchone()
        if result is None:
                # Enrich with coordinates if not present
                lat = listing.get("latitude")
                lon = listing.get("longitude")
                if (lat is None or lon is None) and listing.get("url"):
                    lat, lon = fetch_listing_coordinates(listing["url"])
                listing["latitude"], listing["longitude"] = lat, lon

                new_listings.append(listing)
                if COMMIT_DB:
                    c.execute(
                        "INSERT INTO listings (id, title, price, location, url, date_added, real_estate, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            listing["id"],
                            listing["title"],
                            listing["price"],
                            listing["location"],
                            listing["url"],
                            listing["date_added"],
                            listing["real_estate"],
                            listing["latitude"],
                            listing["longitude"],
                        )
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
        logger.error("Error sending Telegram message: %s", e) 

def main():
    while True:
        conn = create_database()
        total_new_listings = []
        for pararius_url in PARARIUS_URL:
            if USE_JSON_LD:
                listings = fetch_listings_jsonld(pararius_url)
                if not listings:
                    # Fallback to HTML if JSON-LD missing

                    listings = fetch_listings(pararius_url)
            else:
                listings = fetch_listings(pararius_url)
            if not listings:
                logger.error("No listings found or error fetching the page.")
            new_listings = check_new_listings(conn, listings)
            if new_listings:
                # add log to a file
                
                total_new_listings += new_listings
        print(json.dumps(total_new_listings, indent=4)) #print(total_new_listings.)
        if total_new_listings:
            chrome_process = launch_chrome_with_remote_debugging()
            driver = attach_selenium_to_debugger()
            for listing in total_new_listings:
                # Add to a log file, open in append mode (create if doesn't exist)
                log_file = "new_listings.log"
                with open(log_file, "a", encoding="utf-8") as f:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    line = f"Time found: {timestamp}, Title: {listing.get('title')}, Price: {listing.get('price')}, Location: {listing.get('location')}, Real Estate: {listing.get('real_estate')}, URL: {listing.get('url')}, Latitude: {listing.get('latitude')}, Longitude: {listing.get('longitude')}\n"
                    f.write(line)
                if "pararius" in listing["url"]:
                    send_message = send_response(driver, listing["url"], listing["price"], AI_EVALUATE)
                    driver.get("https://www.google.com")

                message = f"*New Listing Found!* *Title:* {listing['title']}, *Price:* {listing['price']}, *Location:* {listing['location']}, *Real Estate:* {listing['real_estate']}, [View Listing]({listing['url']}), *Date Added:* {listing['date_added']}, *Sent reply:* {send_message}"
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
        time.sleep(15)

if __name__ == "__main__":
    main()
