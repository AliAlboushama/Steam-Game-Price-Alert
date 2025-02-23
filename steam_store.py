import time
import requests
import json

# Constants
APP_ID = '2933130'  # Replace with your game's Steam App ID
COUNTRY_CODE = 'us'
LANGUAGE = 'en'
STEAM_API_URL = f'https://store.steampowered.com/api/appdetails?appids={APP_ID}&cc={COUNTRY_CODE}&l={LANGUAGE}'
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1270335499801985054/Ec2exxM5cBdLY9RV3zlsnoSj9JYKeWVDBHhBAcv0RspybymuIIto396NgrLlwSDw356E'  # Replace with your Discord webhook URL


# Store the last known price to avoid duplicate notifications
last_known_price = None

def get_game_details():
    """Fetch game details from the Steam API."""
    try:
        print("[DEBUG] Fetching game details from Steam API...")
        response = requests.get(STEAM_API_URL)
        response.raise_for_status()
        data = response.json()
        return data[APP_ID]['data']
    except Exception as e:
        print(f"[ERROR] Error fetching game details: {e}")
        return None

def send_discord_notification(game_name, current_price, discount_percent, image_url):
    """Send a Discord notification about the sale."""
    embed = {
        "title": game_name,
        "description": f"On sale: ${current_price:.2f} USD ({discount_percent}% off)",
        "url": f"https://store.steampowered.com/app/{APP_ID}/",
        "color": 16711680,  # Red color
        "image": {"url": image_url}  # Include the game image
    }
    payload = {
        "username": "Steam Sales",
        "avatar_url": "https://files.catbox.moe/nyk677.png",  # Optional: Set a custom avatar
        "embeds": [embed]
    }
    
    try:
        print("[DEBUG] Sending Discord notification...")
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("[DEBUG] Notification sent successfully.")
    except Exception as e:
        print(f"[ERROR] Error sending Discord notification: {e}")

def main():
    """Main loop to check for price changes every hour."""
    global last_known_price
    while True:
        game_data = get_game_details()
        if game_data and 'price_overview' in game_data:
            price_info = game_data['price_overview']
            current_price = price_info['final'] / 100  # Convert cents to dollars
            discount_percent = price_info['discount_percent']
            game_name = game_data['name']
            image_url = game_data['header_image']

            print(f"[DEBUG] Game: {game_name}")
            print(f"[DEBUG] Current Price: ${current_price:.2f} USD")
            print(f"[DEBUG] Discount: {discount_percent}%")

            if discount_percent > 0:
                print(f"[DEBUG] Sale detected! Last known price: {last_known_price}")
                if current_price != last_known_price:
                    send_discord_notification(game_name, current_price, discount_percent, image_url)
                    last_known_price = current_price
                else:
                    print("[DEBUG] Sale detected, but price has not changed. No notification sent.")
            else:
                print("[DEBUG] No sale detected.")

        else:
            print("[ERROR] Price information not available.")

        print("[DEBUG] Sleeping for 1 hour before checking again...\n")
        time.sleep(3600)  # Wait 1 hour before checking again

if __name__ == "__main__":
    main()