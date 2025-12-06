import requests
import logging

# Define color constants
RED = 16711680
GREEN = 32768

def construct_embed(game_name, current_price, discount_percent, image_url, app_id, is_historical_low=False, historical_low=None):
    """
    Construct a Discord embed based on the game details.
    """
    description_parts = []
    
    if discount_percent > 0:
        description_parts.append(f"On sale: ${current_price:.2f} USD ({discount_percent}% off)")
        color = RED
    else:
        description_parts.append(f"Price target met: ${current_price:.2f} USD")
        color = GREEN
    
    # Add historical low indicator
    if is_historical_low:
        description_parts.append("⭐ **LOWEST PRICE EVER!** ⭐")
    elif historical_low and historical_low < current_price:
        description_parts.append(f"Historical Low: ${historical_low:.2f}")

    embed = {
        "title": game_name,
        "description": "\n".join(description_parts),
        "url": f"https://store.steampowered.com/app/{app_id}/",
        "color": color,
        "image": {"url": image_url}
    }
    
    return embed

def send_discord_notification(
    game_name: str,
    current_price: float,
    discount_percent: float,
    image_url: str,
    webhook_url: str,
    bot_name: str,
    bot_avatar: str,
    app_id: int,
    is_historical_low: bool = False,
    historical_low: float = None
) -> None:
    """
    Send a Discord notification about the sale or price target met.
    """
    embed = construct_embed(game_name, current_price, discount_percent, image_url, app_id, is_historical_low, historical_low)
    payload = {
        "username": bot_name,
        "avatar_url": bot_avatar,
        "embeds": [embed]
    }

    try:
        logging.info("Sending Discord notification...")
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("Notification sent successfully.")
    except requests.Timeout:
        logging.error("Timeout while sending Discord notification")
    except requests.RequestException as e:
        logging.error(f"Error sending Discord notification: {e}")
    except Exception as e:
        logging.error(f"Unexpected error sending Discord notification: {e}")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")