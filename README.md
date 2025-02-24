# Steam Game Sale Alert Bot

This Python script monitors Steam game sales and sends Discord notifications when a game goes on sale. It saves user preferences, game details, and sale information to avoid spamming notifications for the same sale.

---

## **Features**
- **Sale Monitoring**: Fetches game prices from the Steam API every hour to detect sales.
- **Discord Notifications**: Sends notifications to a Discord channel when a sale is detected.
- **User Preferences**: Saves user preferences (e.g., country code, language, Discord webhook) for future use.
- **Game Database**: Stores game links and names in a SQLite database.
- **Sale Tracking**: Tracks active sales in `saved_sale.json` to avoid duplicate notifications.

---

## **How It Works**
1. The script fetches game details from the Steam API using the game's `app_id`.
2. It checks if the game is on sale by comparing the current price with the last known price.
3. If a sale is detected, it sends a Discord notification with the game's name, price, discount, and image.
4. The sale details are saved in `saved_sale.json` to avoid spamming notifications for the same sale.
5. If the sale ends, the game is removed from `saved_sale.json`.

---

## **Requirements**
- Python 3.x
- Install the required Python package:
  ```bash
  pip install requests
