import requests
import logging

# Define color constants
RED = 16711680
GREEN = 32768

def construct_embed(game_name, current_price, discount_percent, image_url, app_id):
    """
    Construct a Discord embed based on the game details.
    """
    if discount_percent > 0:
        description = f"On sale: ${current_price:.2f} USD ({discount_percent}% off)"
        color = RED
    else:
        description = f"Price target met: ${current_price:.2f} USD"
        color = GREEN

    return {
        "title": game_name,
        "description": description,
        "url": f"https://store.steampowered.com/app/{app_id}/",
        "color": color,
        "image": {"url": image_url}
    }

def send_discord_notification(
    game_name: str,
    current_price: float,
    discount_percent: float,
    image_url: str,
    webhook_url: str,
    bot_name: str,
    bot_avatar: str,
    app_id: int
) -> None:
    """
    Send a Discord notification about the sale or price target met.
    """
    embed = construct_embed(game_name, current_price, discount_percent, image_url, app_id)
    payload = {
        "username": bot_name,
        "avatar_url": bot_avatar,
        "embeds": [embed]
    }

    try:
        logging.info("Sending Discord notification...")
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        logging.info("Notification sent successfully.")
    except requests.RequestException as e:
        logging.error(f"Error sending Discord notification: {e}")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")