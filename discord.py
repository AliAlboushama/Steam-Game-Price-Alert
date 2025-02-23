import requests

def send_discord_notification(game_name, current_price, discount_percent, image_url, webhook_url, bot_name, bot_avatar, app_id):
    """
    Send a Discord notification about the sale.
    
    Args:
        game_name (str): Name of the game.
        current_price (float): Current price of the game.
        discount_percent (int): Discount percentage.
        image_url (str): URL of the game's image.
        webhook_url (str): Discord webhook URL.
        bot_name (str): Name of the bot.
        bot_avatar (str): URL of the bot's avatar image.
        app_id (str): The Steam App ID of the game.
    """
    embed = {
        "title": game_name,
        "description": f"On sale: ${current_price:.2f} USD ({discount_percent}% off)",
        "url": f"https://store.steampowered.com/app/{app_id}/",  # Use the app_id to construct the URL
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