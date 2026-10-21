import requests
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (Steam-Game-Price-Alert)"}

# Steam ignores ISO codes like "de" and silently falls back to English - it wants these names
STEAM_LANGUAGES = {
    "ar": "arabic", "bg": "bulgarian", "zh": "schinese", "tw": "tchinese", "cs": "czech",
    "da": "danish", "nl": "dutch", "en": "english", "fi": "finnish", "fr": "french",
    "de": "german", "el": "greek", "hu": "hungarian", "id": "indonesian", "it": "italian",
    "ja": "japanese", "ko": "koreana", "no": "norwegian", "pl": "polish", "pt": "portuguese",
    "br": "brazilian", "ro": "romanian", "ru": "russian", "es": "spanish",
    "sv": "swedish", "th": "thai", "tr": "turkish", "uk": "ukrainian", "vi": "vietnamese",
}

def steam_language(language):
    """Turn a saved language code ("en", "de") into the name Steam understands ("english")."""
    language = (language or "en").lower()
    return STEAM_LANGUAGES.get(language, language)

def extract_app_id(game_link):
    """
    Extract the item id from a Steam store link (or a bare app id):
    /app/N -> "N", /sub/N -> "sub:N", /bundle/N -> "bundle:N".
    """
    if not game_link:
        return None
    game_link = str(game_link).strip()
    if game_link.isdigit():
        return game_link
    match = re.search(r'/(app|sub|bundle)/(\d+)', game_link)
    if match:
        kind, number = match.groups()
        return number if kind == "app" else f"{kind}:{number}"
    logging.error(f"Invalid game link: {game_link}")
    return None

def get_game_details(app_id, country_code, language):
    """Fetch game details from the Steam API with error handling."""
    app_id = str(app_id)
    try:
        response = requests.get(
            'https://store.steampowered.com/api/appdetails',
            params={'appids': app_id, 'cc': country_code, 'l': steam_language(language)},
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        data = response.json() or {}
        return (data.get(app_id) or {}).get('data')
    except requests.RequestException as e:
        logging.error(f"Error fetching details for app {app_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching details for app {app_id}: {e}")
        return None

def price_from_details(game_data):
    """
    Turn Steam's appdetails into one price dict used everywhere in the bot.
    Prices come pre-formatted in the user's currency (e.g. "17,99€"), so we never print "$" by mistake.
    """
    if not game_data:
        return None
    info = {
        'name': game_data.get('name', 'Unknown Game'),
        'is_free': bool(game_data.get('is_free')),
        'header_image': game_data.get('header_image', ''),
        'final': None,
        'initial': None,
        'discount_percent': 0,
        'final_formatted': None,
        'initial_formatted': None,
        'currency': None,
        'discount_end': None,
    }
    price = game_data.get('price_overview')
    if price:
        info.update({
            'final': price['final'],
            'initial': price.get('initial', price['final']),
            'discount_percent': price.get('discount_percent', 0),
            'final_formatted': price.get('final_formatted') or f"{price['final'] / 100:.2f}",
            'initial_formatted': price.get('initial_formatted') or None,
            'currency': price.get('currency'),
        })
    return info

def get_price_info(app_id, country_code, language):
    """Fetch the current price for one game, in the user's currency."""
    return price_from_details(get_game_details(app_id, country_code, language))

def format_price_line(info):
    """One line describing a price, e.g. '17,99€ (was 59,99€) - 70% OFF'."""
    if info.get('final') is None:
        if info.get('is_free'):
            return "Free to play"
        if info.get('coming_soon'):
            return "Coming soon - not on sale yet"
        return "Not sold on Steam right now"
    if info.get('discount_percent', 0) > 0 and info.get('initial_formatted'):
        return f"{info['final_formatted']} (was {info['initial_formatted']}) - {info['discount_percent']}% OFF"
    return info['final_formatted']

def format_sale_end(timestamp):
    """'Mon 26 Oct 20:00 (in 5 days)' in the computer's local time."""
    end = datetime.fromtimestamp(int(timestamp))
    left = end - datetime.now()
    if left.total_seconds() <= 0:
        remaining = "ended"
    elif left.days >= 1:
        remaining = f"in {left.days} day{'s' if left.days != 1 else ''}"
    else:
        remaining = f"in {max(1, left.seconds // 3600)} hour(s)"
    return f"{end.strftime('%a %d %b %H:%M')} ({remaining})"

def get_review_summary(app_id, language="en"):
    """
    Fetch the Steam user review summary (score label and counts).
    The 'reviews' field in appdetails is critic quotes as HTML text, not scores.
    """
    try:
        response = requests.get(
            f'https://store.steampowered.com/appreviews/{app_id}',
            params={'json': 1, 'language': 'all', 'purchase_type': 'all',
                    'num_per_page': 0, 'l': steam_language(language)},
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        return response.json().get('query_summary') or None
    except Exception as e:
        logging.error(f"Error fetching reviews for app {app_id}: {e}")
        return None

def get_detailed_game_info(app_id, country_code, language):
    """Get detailed game information including release date, reviews, and tags."""
    game_data = get_game_details(app_id, country_code, language)
    if not game_data:
        return None

    info = {
        'name': game_data.get('name', 'Unknown'),
        'release_date': (game_data.get('release_date') or {}).get('date', 'Unknown'),
        'header_image': game_data.get('header_image', ''),
        'short_description': game_data.get('short_description', 'No description available'),
        'price': price_from_details(game_data),
        'genres': [genre.get('description', '') for genre in game_data.get('genres') or []],
        'categories': [cat.get('description', '') for cat in game_data.get('categories') or []],
        'recommendations': (game_data.get('recommendations') or {}).get('total', 0),
        'metacritic': (game_data.get('metacritic') or {}).get('score', None),
        'developers': game_data.get('developers') or [],
        'publishers': game_data.get('publishers') or [],
        'review_score_desc': 'No reviews',
        'total_reviews': 0,
        'total_positive': 0,
        'total_negative': 0,
    }

    reviews = get_review_summary(app_id, language)
    if reviews and reviews.get('total_reviews'):
        info['review_score_desc'] = reviews.get('review_score_desc', 'No reviews')
        info['total_reviews'] = reviews.get('total_reviews', 0)
        info['total_positive'] = reviews.get('total_positive', 0)
        info['total_negative'] = reviews.get('total_negative', 0)

    return info

def validate_country_code(country_code):
    """Validate country code format (2 uppercase letters)."""
    if not country_code or len(country_code) != 2:
        return False
    return country_code.isalpha() and country_code.isupper()

def validate_language_code(language):
    """Validate language: a short code we can map ("en", "de") or a Steam language name ("german")."""
    if not language:
        return False
    return language in STEAM_LANGUAGES or language in STEAM_LANGUAGES.values()

def validate_webhook_url(webhook_url):
    """Validate Discord webhook URL format."""
    if not webhook_url:
        return False
    try:
        parsed = urlparse(webhook_url)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme == 'https' and
                host in ('discord.com', 'discordapp.com', 'ptb.discord.com', 'canary.discord.com') and
                parsed.path.startswith('/api/webhooks/'))
    except Exception:
        return False

def validate_steam_link(steam_link):
    """Validate Steam store link format."""
    if not steam_link:
        return False
    try:
        parsed = urlparse(steam_link.strip())
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in ['http', 'https'] and
                (host == 'steampowered.com' or host.endswith('.steampowered.com')) and
                re.search(r'/(app|sub|bundle)/\d+', parsed.path) is not None)
    except Exception:
        return False
