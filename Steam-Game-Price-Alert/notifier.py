import time
import requests
import logging

# Define color constants
RED = 16711680
GREEN = 32768
GOLD = 16766720

def construct_embed(game_name, price_info, app_id, reason="sale", threshold=None,
                    is_historical_low=False, historical_low=None, test=False):
    """
    Construct a Discord embed based on the game details.
    reason is "sale" (any discount) or "target" (price fell to the user's threshold).
    """
    description_parts = []
    final = price_info.get('final_formatted') or "?"
    discount_percent = price_info.get('discount_percent', 0)

    if reason == "target":
        target_text = f" (your target: {threshold:.2f})" if threshold is not None else ""
        description_parts.append(f"Price target met: **{final}**{target_text}")
        color = GREEN
    else:
        description_parts.append(f"On sale: **{final}** ({discount_percent}% off)")
        color = RED

    if discount_percent > 0 and price_info.get('initial_formatted'):
        description_parts.append(f"Normal price: ~~{price_info['initial_formatted']}~~")

    # Add historical low indicator
    if is_historical_low:
        description_parts.append("⭐ **LOWEST PRICE EVER!** ⭐")
        color = GOLD
    elif historical_low is not None and price_info.get('final') is not None \
            and historical_low < price_info['final'] / 100:
        description_parts.append(f"Lowest seen: {historical_low:.2f}")

    # Discord shows <t:...> in each reader's own time zone, e.g. "in 5 days"
    if price_info.get('discount_end'):
        end = int(price_info['discount_end'])
        description_parts.append(f"⏰ Sale ends <t:{end}:R> (<t:{end}:f>)")

    if price_info.get('review_label'):
        review = f"👍 {price_info['review_label']}"
        if price_info.get('review_percent') is not None:
            review += f" ({price_info['review_percent']}% of {price_info.get('review_count') or 0:,} reviews)"
        description_parts.append(review)

    if test:
        description_parts.insert(0, "🧪 **TEST MESSAGE - this is not a real sale.**")

    embed = {
        "title": game_name,
        "description": "\n".join(description_parts),
        "url": f"https://store.steampowered.com/app/{app_id}/",
        "color": color,
    }
    if price_info.get('header_image'):
        embed["image"] = {"url": price_info['header_image']}

    return embed

def post_to_webhook(webhook_url, payload):
    """Post a payload to a Discord webhook. Waits and retries once if Discord rate-limits us."""
    for attempt in range(2):
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 429 and attempt == 0:
            try:
                retry_after = float(response.json().get("retry_after", 1))
            except Exception:
                retry_after = 1
            logging.warning(f"Discord rate limit hit, retrying in {retry_after:.1f}s")
            time.sleep(min(retry_after, 30))
            continue
        response.raise_for_status()
        return True
    return False

def send_discord_notification(game_name, price_info, webhook_url, bot_name, bot_avatar, app_id,
                              reason="sale", threshold=None, is_historical_low=False,
                              historical_low=None, test=False):
    """
    Send a Discord notification about the sale or price target met.
    Returns True only if Discord accepted it, so a failed alert is retried next check.
    """
    embed = construct_embed(game_name, price_info, app_id, reason, threshold,
                            is_historical_low, historical_low, test)
    payload = {"embeds": [embed]}
    # Discord rejects an empty username or avatar URL, so only send them when set
    if bot_name:
        payload["username"] = bot_name[:80]
    if bot_avatar:
        payload["avatar_url"] = bot_avatar

    try:
        logging.info(f"Sending Discord notification for {game_name}...")
        if post_to_webhook(webhook_url, payload):
            logging.info("Notification sent successfully.")
            return True
    except requests.Timeout:
        logging.error("Timeout while sending Discord notification")
    except requests.RequestException as e:
        logging.error(f"Error sending Discord notification: {e}")
    except Exception as e:
        logging.error(f"Unexpected error sending Discord notification: {e}")
    return False
