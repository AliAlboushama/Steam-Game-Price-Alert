"""
Discord webhook messages.
- Alerts found in one check are grouped: up to 10 per message instead of one message each.
- Big deals (price target met, lowest price ever) notify you; ordinary sales arrive silently
  (Discord's "suppress notifications" flag) unless the user turns that off.
- Every message id is kept, so an alert can be edited later: "Sale ended" or "Cheaper now".
"""
import time
import logging
from datetime import datetime, timezone
import requests
from saved_games import save_message, get_message, delete_message

COLOR_SALE = 0x66C0F4    # Steam blue
COLOR_TARGET = 0xA1CD44  # green
COLOR_LOWEST = 0xFFD166  # gold
COLOR_ENDED = 0x4B5563   # grey
COLOR_NOTICE = 0xE5C07B  # amber, for health warnings

FOOTER = "Steam Price Alert"
SUPPRESS_NOTIFICATIONS = 1 << 12
MAX_EMBEDS = 10           # Discord's limit per message
MAX_MESSAGE_CHARS = 5500  # Discord allows 6000 characters of embed text per message

def _money(amount, currency):
    return f"{amount:.2f} {currency}" if currency else f"{amount:.2f}"

def build_embed(alert, compact=False, test=False):
    """
    One alert as a Discord embed. alert keys: name, url, price (price dict), reason
    ("sale"/"target"), threshold, lowest_ever, steam_low (IsThereAnyDeal), local_low.
    """
    info = alert['price']
    final = info.get('final_formatted') or "?"
    percent = info.get('discount_percent', 0)

    if alert.get('reason') == "target":
        description = f"**{final}**"
        if percent and info.get('initial_formatted'):
            description += f"  ~~{info['initial_formatted']}~~  **-{percent}%**"
        if alert.get('threshold') is not None:
            description += f"\nAt or below your target of {alert['threshold']:.2f}"
        color = COLOR_TARGET
    else:
        description = f"**{final}**"
        if info.get('initial_formatted'):
            description += f"  ~~{info['initial_formatted']}~~"
        description += f"  **-{percent}%**"
        color = COLOR_SALE
    if alert.get('lowest_ever'):
        description += "\n**Lowest price ever**"
        color = COLOR_LOWEST

    fields = []
    if info.get('discount_end'):
        end = int(info['discount_end'])
        fields.append({"name": "Sale ends", "value": f"<t:{end}:R>", "inline": True})
    if info.get('review_label'):
        value = info['review_label']
        if info.get('review_percent') is not None:
            value += f" · {info['review_percent']}%"
        fields.append({"name": "Reviews", "value": value, "inline": True})
    if alert.get('steam_low'):
        low = alert['steam_low']
        value = _money(low['price'], low.get('currency'))
        if low.get('date'):
            value += f" · {low['date'][:7]}"
        fields.append({"name": "All-time low", "value": value, "inline": True})
    elif alert.get('local_low') is not None and info.get('final') is not None \
            and alert['local_low'] < info['final'] / 100:
        fields.append({"name": "Lowest seen", "value": f"{alert['local_low']:.2f}", "inline": True})

    embed = {
        "title": ("TEST · " if test else "") + alert['name'],
        "url": alert['url'],
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {"text": FOOTER + (" · Test message, not a real sale" if test else "")},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if info.get('header_image'):
        embed["thumbnail" if compact else "image"] = {"url": info['header_image']}
    return embed

def _request(method, url, payload):
    """Send to Discord, waiting and retrying (up to 3 times) when Discord says to slow down."""
    for attempt in range(3):
        # wait=true makes Discord return the new message (we need its id to edit it later)
        params = {"wait": "true"} if method == "POST" else None
        response = requests.request(method, url, json=payload, params=params, timeout=10)
        if response.status_code == 429 and attempt < 2:
            try:
                retry_after = float(response.json().get("retry_after", 1))
            except Exception:
                retry_after = 1
            logging.warning(f"Discord rate limit hit, retrying in {retry_after:.1f}s")
            time.sleep(min(retry_after, 30))
            continue
        # Pause before the next message if this was the last one allowed right now
        if response.headers.get("X-RateLimit-Remaining") == "0":
            time.sleep(min(float(response.headers.get("X-RateLimit-Reset-After", 1)), 30))
        return response
    return response

def _identity(settings):
    payload = {}
    # Discord rejects an empty username or avatar URL, so only send them when set
    if settings.get('bot_name'):
        payload["username"] = settings['bot_name'][:80]
    if settings.get('bot_avatar'):
        payload["avatar_url"] = settings['bot_avatar']
    return payload

def post_message(settings, embeds, content=None, silent=False):
    """Post one message. Returns the Discord message id, or None if it failed."""
    payload = dict(_identity(settings), embeds=embeds)
    if content:
        payload["content"] = content
    if silent:
        payload["flags"] = SUPPRESS_NOTIFICATIONS
    try:
        response = _request("POST", settings['webhook_url'], payload)
        response.raise_for_status()
        message_id = response.json().get("id")
        save_message(message_id, embeds)
        logging.info(f"Discord message {message_id} sent ({len(embeds)} embed(s))")
        return message_id
    except Exception as e:
        logging.error(f"Error sending Discord message: {e}")
        return None

def _chunks(alerts):
    """Split alerts into messages of at most 10 embeds and ~5500 characters."""
    chunk, size = [], 0
    for alert in alerts:
        length = len(alert['name']) + 400
        if chunk and (len(chunk) == MAX_EMBEDS or size + length > MAX_MESSAGE_CHARS):
            yield chunk
            chunk, size = [], 0
        chunk.append(alert)
        size += length
    if chunk:
        yield chunk

def send_alerts(alerts, settings, test=False):
    """
    Send alerts grouped into as few messages as possible. Loud alerts (target met, lowest ever)
    go in their own messages that notify; ordinary sales go in silent ones.
    Sets alert['message_id'] and alert['embed_index'] on the ones Discord accepted.
    """
    quiet_sales = settings.get('quiet_ordinary_sales', True)
    loud = [a for a in alerts if a.get('loud') or not quiet_sales]
    quiet = [a for a in alerts if not (a.get('loud') or not quiet_sales)]
    for group, silent in ((loud, False), (quiet, True)):
        for chunk in _chunks(group):
            compact = len(chunk) > 1
            embeds = [build_embed(a, compact=compact, test=test) for a in chunk]
            content = f"**{len(chunk)} deals**" if compact else None
            message_id = post_message(settings, embeds, content, silent=silent)
            for index, alert in enumerate(chunk):
                alert['message_id'] = message_id
                alert['embed_index'] = index if message_id else None
    return sum(1 for a in alerts if a.get('message_id'))

def edit_alert(settings, message_id, embed_index, note):
    """
    Mark one alert in an earlier message as no longer current (grey, struck-through price, a note).
    Returns True if Discord accepted the edit.
    """
    embeds = get_message(message_id)
    if not embeds or embed_index is None or embed_index >= len(embeds):
        return False
    embed = embeds[embed_index]
    if embed.get("color") == COLOR_ENDED:
        return True  # already marked
    first_line = embed.get("description", "").split("\n")[0]
    embed["description"] = f"~~{first_line.replace('~~', '')}~~\n{note}"
    embed["color"] = COLOR_ENDED
    embed["fields"] = [f for f in embed.get("fields", []) if f.get("name") != "Sale ends"]
    url = settings['webhook_url'].rstrip("/") + f"/messages/{message_id}"
    try:
        response = _request("PATCH", url, {"embeds": embeds})
        if response.status_code == 404:
            delete_message(message_id)  # someone deleted the message in Discord
            return False
        response.raise_for_status()
        save_message(message_id, embeds)
        return True
    except Exception as e:
        logging.error(f"Error editing Discord message {message_id}: {e}")
        return False

def send_notice(settings, title, text, color=COLOR_NOTICE):
    """A plain one-off message, e.g. 'the bot is having trouble'."""
    embed = {"title": title, "description": text, "color": color,
             "footer": {"text": FOOTER}, "timestamp": datetime.now(timezone.utc).isoformat()}
    return post_message(settings, [embed]) is not None
