# Pararius Scraper

This Python script scrapes apartment listings from Pararius, checks for new listings, and sends notifications via Telegram. It's designed to help you stay updated on the rental market in specific areas.

## Features

-   Scrapes apartment listings from Pararius based on predefined URLs.
-   Stores listing information in a SQLite database to track new entries.
-   Sends notifications via Telegram for new listings.
-   Includes error logging for easier debugging.
-   Uses Selenium to automatically send responses to new listings.

## Prerequisites

Before running the script, ensure you have the following:

-   Python 3.6+
-   Required Python packages:
    ```bash
    pip install requests beautifulsoup4 sqlite3 python-dotenv selenium
    ```
-   A Telegram bot token and chat ID (if you want to use Telegram notifications).
-   Google Chrome installed.
-   ChromeDriver installed and added to your system's PATH (if you want to use Selenium).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone [repository_url]
    cd [repository_directory]
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**

    -   Create a `.env` file in the project directory.
    -   Add your Telegram bot token and chat ID to the `.env` file:

        ```
        TELEGRAM_BOT_TOKEN=your_telegram_bot_token
        TELEGRAM_CHAT_ID=your_telegram_chat_id
        ```

## Configuration

You can configure the script by modifying the following variables in `pararius.py`:

-   `PARARIUS_URL`: A list of Pararius URLs to scrape.  Modify these to match your desired locations, price ranges, and number of bedrooms.
-   `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (set in `.env`).
-   `TELEGRAM_CHAT_ID`: Your Telegram chat ID (set in `.env`).
-   `COMMIT_DB`: A boolean to determine whether to commit the new listings to the database. Defaults to `True`.
-   `SEND_TELEGRAM`: A boolean to determine whether to send the new listings to Telegram. Defaults to `True`.
-   `AI_EVALUATE`: A boolean to determine whether to send a response to the listing using Selenium. Defaults to `True`.

## Usage

1.  **Run the script:**
    ```bash
    python pararius.py
    ```

The script will run continuously, scraping Pararius for new listings, checking against the database, and sending Telegram notifications for any new listings found.  It pauses for 25 seconds between each check.

## Database

The script uses a SQLite database named `listings.db` to store listing information. The database file will be created in the same directory as the script.

## Logging

The script uses a logger to record important events and errors. Logs are saved in the `logs` directory.

## Selenium Usage

The script uses Selenium to automatically send responses to new listings. To use this feature, you must have Google Chrome and ChromeDriver installed. The script will launch a Chrome instance with remote debugging enabled, and then attach Selenium to the debugger.

## Disclaimer

This script is intended for personal use only. Scraping Pararius may violate their terms of service. Use this script responsibly and at your own risk. The script's effectiveness may vary depending on changes to the Pararius website structure.