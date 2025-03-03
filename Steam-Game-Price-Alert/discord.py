import requests

def send_discord_notification(game_name, current_price, discount_percent, image_url, webhook_url, bot_name, bot_avatar, app_id):
    """
    Send a Discord notification about the sale or price target met.
    """
    # Determine message and color based on discount
    if discount_percent > 0:
        description = f"On sale: ${current_price:.2f} USD ({discount_percent}% off)"
        color = 16711680  # Red
    else:
        description = f"Price target met: ${current_price:.2f} USD"
        color = 32768  # Green

    embed = {
        "title": game_name,
        "description": description,
        "url": f"https://store.steampowered.com/app/{app_id}/",
        "color": color,
        "image": {"url": image_url}
    }
    payload = {
        "username": bot_name,
        "avatar_url": bot_avatar,
        "embeds": [embed]
    }
    
    try:
        print("Sending Discord notification...")
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("Notification sent successfully.")
    except Exception as e:
        print(f"[ERROR] Error sending Discord notification: {e}")