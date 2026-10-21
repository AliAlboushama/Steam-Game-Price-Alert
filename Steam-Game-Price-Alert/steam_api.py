"""
Newer Steam store endpoints (no API key needed):
- IStoreBrowseService/GetItems: prices for up to 100 items per request, with the sale end date.
  Works for games ("1091500"), packages ("sub:469") and bundles ("bundle:232").
- IWishlistService/GetWishlist: a public Steam wishlist
- storesearch: find a game by name

Item ids are strings: a plain number is a game/DLC app id, "sub:N" a package, "bundle:N" a bundle.
"""
import re
import json
import time
import logging
import requests
from utils import HEADERS, steam_language, get_price_info, get_game_details

GET_ITEMS_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
WISHLIST_URL = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
ASSET_BASE = "https://shared.akamai.steamstatic.com/store_item_assets/"
BATCH_SIZE = 100       # ids go in the URL: 200 works, 300 is too long for Steam
RETRY_DELAYS = (5, 20)  # seconds to wait before the 2nd and 3rd try of a failed batch
MISS_CACHE_SECONDS = 24 * 3600

# Item types in GetItems responses
_TYPE_PREFIX = {0: "", 1: "sub:", 2: "bundle:"}
_REQUEST_KEY = {"": "appid", "sub:": "packageid", "bundle:": "bundleid"}

# Games Steam couldn't price even with the fallback, so we don't ask again every round
_missing_until = {}

def split_item_id(item_id):
    """'bundle:232' -> ('bundle:', 232), '1091500' -> ('', 1091500)."""
    item_id = str(item_id)
    for prefix in ("sub:", "bundle:"):
        if item_id.startswith(prefix):
            return prefix, int(item_id[len(prefix):])
    return "", int(item_id)

def store_url(item_id):
    """Store page link for a game, package or bundle."""
    prefix, number = split_item_id(item_id)
    path = {"": "app", "sub:": "sub", "bundle:": "bundle"}[prefix]
    return f"https://store.steampowered.com/{path}/{number}/"

def is_app(item_id):
    return str(item_id).isdigit()

def _price_from_store_item(item):
    """Turn one GetItems result into the same price dict the rest of the bot uses."""
    option = item.get('best_purchase_option') or {}
    assets = item.get('assets') or {}
    reviews = (item.get('reviews') or {}).get('summary_filtered') or {}

    header_image = ""
    if assets.get('asset_url_format') and assets.get('header'):
        header_image = ASSET_BASE + assets['asset_url_format'].replace("${FILENAME}", assets['header'])

    final = option.get('final_price_in_cents')
    final = int(final) if final not in (None, "") else None
    initial = option.get('original_price_in_cents')
    initial = int(initial) if initial not in (None, "") else final
    discount_ends = [d.get('discount_end_date') for d in option.get('active_discounts') or []
                     if d.get('discount_end_date')]

    return {
        'name': item.get('name', 'Unknown Game'),
        'is_free': bool(item.get('is_free')),
        'header_image': header_image,
        'final': final,
        'initial': initial,
        'discount_percent': option.get('discount_pct') or 0,
        'final_formatted': option.get('formatted_final_price'),
        'initial_formatted': option.get('formatted_original_price'),
        'currency': None,
        'discount_end': min(discount_ends) if discount_ends else None,
        'review_label': reviews.get('review_score_label'),
        'review_percent': reviews.get('percent_positive'),
        'review_count': reviews.get('review_count'),
        'coming_soon': bool((item.get('release') or {}).get('is_coming_soon')),
    }

def _fetch_batch(batch, country_code, language):
    """One GetItems request, tried up to 3 times with a pause. Returns the items, or None if Steam failed."""
    request = {
        "ids": [{_REQUEST_KEY[split_item_id(i)[0]]: split_item_id(i)[1]} for i in batch],
        "context": {"language": steam_language(language), "country_code": country_code},
        "data_request": {"include_all_purchase_options": True, "include_assets": True,
                         "include_reviews": True, "include_release": True},
    }
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            logging.warning(f"GetItems failed, retrying in {delay}s (try {attempt + 1})")
            time.sleep(delay)
        try:
            response = requests.get(GET_ITEMS_URL, params={"input_json": json.dumps(request)},
                                    headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.json().get('response', {}).get('store_items', [])
        except Exception as e:
            logging.error(f"GetItems failed for {len(batch)} items: {e}")
    return None

def get_store_items(item_ids, country_code, language):
    """
    Fetch prices for many items at once.
    Returns (prices, failed): prices = {item_id: price dict}; failed = True if Steam
    couldn't be reached for at least one batch even after retries.
    """
    item_ids = [str(i) for i in dict.fromkeys(item_ids) if re.fullmatch(r'(sub:|bundle:)?\d+', str(i))]
    results, failed = {}, False
    for start in range(0, len(item_ids), BATCH_SIZE):
        items = _fetch_batch(item_ids[start:start + BATCH_SIZE], country_code, language)
        if items is None:
            failed = True
            continue
        for item in items:
            if item.get('success') == 1 and item.get('id') is not None:
                key = _TYPE_PREFIX.get(item.get('item_type', 0), "") + str(item['id'])
                results[key] = _price_from_store_item(item)
    return results, failed

def get_prices(item_ids, country_code, language):
    """
    Prices for many items: one GetItems request per 100 items. Games that GetItems didn't
    answer (while Steam itself was fine) get one try on the older appdetails endpoint;
    misses are remembered for a day so a broken id doesn't cost a request every round.
    Returns (prices, failed) like get_store_items.
    """
    prices, failed = get_store_items(item_ids, country_code, language)
    if failed:
        # Steam is having trouble: don't hammer it with one request per game
        return prices, True
    now = time.time()
    for item_id in map(str, item_ids):
        if item_id in prices or not is_app(item_id) or _missing_until.get(item_id, 0) > now:
            continue
        logging.info(f"GetItems had no data for {item_id}, falling back to appdetails")
        info = get_price_info(item_id, country_code, language)
        if info:
            prices[item_id] = info
        else:
            _missing_until[item_id] = now + MISS_CACHE_SECONDS
    return prices, False

def get_dlc(app_id):
    """App ids of a game's DLC (empty list if none)."""
    data = get_game_details(app_id, "US", "en")
    return [str(d) for d in (data or {}).get('dlc') or []]

def search_games(term, country_code="US", language="en", limit=8):
    """Search the Steam store by name. Returns a list of (app_id, name)."""
    try:
        response = requests.get(SEARCH_URL, params={"term": term, "cc": country_code,
                                                    "l": steam_language(language)},
                                headers=HEADERS, timeout=10)
        response.raise_for_status()
        return [(str(i['id']), i['name']) for i in response.json().get('items', [])[:limit]
                if i.get('type', 'app') == 'app']
    except Exception as e:
        logging.error(f"Store search failed for '{term}': {e}")
        return []

def resolve_steam_id(profile):
    """
    Accept a SteamID64, a profile link (/profiles/7656... or /id/name) or a custom
    profile name, and return the SteamID64 as a string (or None).
    """
    profile = (profile or "").strip().rstrip('/')
    if re.fullmatch(r'7656\d{13}', profile):
        return profile
    match = re.search(r'/profiles/(7656\d{13})', profile)
    if match:
        return match.group(1)
    match = re.search(r'/id/([^/?#]+)', profile)
    vanity = match.group(1) if match else profile
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,32}', vanity):
        return None
    try:
        response = requests.get(f"https://steamcommunity.com/id/{vanity}/", params={"xml": 1},
                                headers=HEADERS, timeout=10)
        found = re.search(r'<steamID64>(\d+)</steamID64>', response.text)
        return found.group(1) if found else None
    except Exception as e:
        logging.error(f"Could not resolve Steam profile '{profile}': {e}")
        return None

def get_wishlist(steam_id):
    """
    Return the app ids on a public Steam wishlist, highest priority first.
    Returns None on a network error; an empty list means empty or private.
    """
    try:
        response = requests.get(WISHLIST_URL, params={"steamid": steam_id}, headers=HEADERS, timeout=15)
        response.raise_for_status()
        items = response.json().get('response', {}).get('items', [])
        items.sort(key=lambda i: i.get('priority', 0))
        return [str(i['appid']) for i in items if i.get('appid')]
    except Exception as e:
        logging.error(f"Could not load wishlist for {steam_id}: {e}")
        return None
