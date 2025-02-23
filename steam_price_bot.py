import time
import requests
import json

def extract_app_id(game_link):
    """Extract the APP_ID from the Steam game link."""
    try:
        # Extract the APP_ID from the URL
        app_id = game_link.split('/app/')[1].split('/')[0]
        return app_id
    except Exception as e:
        print(f"[ERROR] Invalid game link. Please provide a valid Steam store link.")
        return None

def get_game_details(app_id, country_code, language):
    """Fetch game details from the Steam API."""
    steam_api_url = f'https://store.steampowered.com/api/appdetails?appids={app_id}&cc={country_code}&l={language}'
    try:
        print("Fetching game details from Steam API...")
        response = requests.get(steam_api_url)
        response.raise_for_status()
        data = response.json()
        return data[app_id]['data']
    except Exception as e:
        print(f"[ERROR] Error fetching game details: {e}")
        return None

def send_discord_notification(game_name, current_price, discount_percent, image_url, webhook_url, bot_name, bot_avatar):
    """Send a Discord notification about the sale."""
    embed = {
        "title": game_name,
        "description": f"On sale: ${current_price:.2f} USD ({discount_percent}% off)",
        "url": f"https://store.steampowered.com/app/{app_id}/",
        "color": 16711680,  # Red color
        "image": {"url": image_url}  # Include the game image
    }
    payload = {
        "username": bot_name,
        "avatar_url": bot_avatar,  # Set the bot's avatar
        "embeds": [embed]
    }
    
    try:
        print("Sending Discord notification...")
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("Notification sent successfully.")
    except Exception as e:
        print(f"[ERROR] Error sending Discord notification: {e}")

def main():
    """Main loop to check for price changes every hour."""
    global last_known_price

    # User inputs
    game_link = input("Enter the Steam game link (e.g., https://store.steampowered.com/app/534380/): ")
    app_id = extract_app_id(game_link)
    if not app_id:
        return

    country_code = input("Enter the country code (e.g., US, UK): ").upper()
    language = input("Enter the language code (e.g., en for English): ").lower()
    webhook_url = input("Enter your Discord webhook URL: ")
    bot_name = input("Enter the bot name: ")
    bot_avatar = input("Enter the bot avatar URL (e.g., a link to a PNG image): ")

    last_known_price = None

    while True:
        game_data = get_game_details(app_id, country_code, language)
        if game_data and 'price_overview' in game_data:
            price_info = game_data['price_overview']
            current_price = price_info['final'] / 100  # Convert cents to dollars
            discount_percent = price_info['discount_percent']
            game_name = game_data['name']
            image_url = game_data['header_image']

            print(f"Game: {game_name}")
            print(f"Current Price: ${current_price:.2f} USD")
            print(f"Discount: {discount_percent}%")

            if discount_percent > 0:
                print(f"Sale detected! Last known price: {last_known_price}")
                if current_price != last_known_price:
                    send_discord_notification(game_name, current_price, discount_percent, image_url, webhook_url, bot_name, bot_avatar)
                    last_known_price = current_price
                else:
                    print("Sale detected, but price has not changed. No notification sent.")
            else:
                print("No sale detected.")

        else:
            print("[ERROR] Price information not available.")

        print("Sleeping for 1 hour before checking again...\n")
        time.sleep(3600)  # Wait 1 hour before checking again

if __name__ == "__main__":
    main()