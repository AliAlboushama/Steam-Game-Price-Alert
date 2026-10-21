"""
Newer Steam store endpoints (no API key needed):
- IStoreBrowseService/GetItems: prices for up to 50 games in one request, with the sale end date
- IWishlistService/GetWishlist: a public Steam wishlist
- storesearch: find a game by name
"""
import re
import json
import logging
import requests
from utils import HEADERS, steam_language, get_price_info

GET_ITEMS_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
WISHLIST_URL = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
ASSET_BASE = "https://shared.akamai.steamstatic.com/store_item_assets/"
BATCH_SIZE = 50  # the request goes in the URL; 300 ids is too long for Steam

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

def get_store_items(app_ids, country_code, language):
    """
    Fetch prices for many games at once. Returns {app_id (str): price dict}.
    Games Steam doesn't return (removed, region-locked) are simply missing from the result.
    """
    app_ids = [str(a) for a in dict.fromkeys(app_ids) if str(a).isdigit()]
    results = {}
    for start in range(0, len(app_ids), BATCH_SIZE):
        batch = app_ids[start:start + BATCH_SIZE]
        request = {
            "ids": [{"appid": int(a)} for a in batch],
            "context": {"language": steam_language(language), "country_code": country_code},
            "data_request": {"include_all_purchase_options": True, "include_assets": True,
                             "include_reviews": True, "include_release": True},
        }
        try:
            response = requests.get(GET_ITEMS_URL, params={"input_json": json.dumps(request)},
                                    headers=HEADERS, timeout=15)
            response.raise_for_status()
            for item in response.json().get('response', {}).get('store_items', []):
                if item.get('success') == 1 and item.get('appid'):
                    results[str(item['appid'])] = _price_from_store_item(item)
        except Exception as e:
            logging.error(f"GetItems failed for {len(batch)} games: {e}")
    return results

def get_prices(app_ids, country_code, language):
    """
    Prices for many games: one GetItems request per 50 games, and the older
    appdetails endpoint for any game GetItems couldn't answer.
    """
    prices = get_store_items(app_ids, country_code, language)
    for app_id in app_ids:
        app_id = str(app_id)
        if app_id not in prices:
            logging.info(f"GetItems had no data for {app_id}, falling back to appdetails")
            info = get_price_info(app_id, country_code, language)
            if info:
                prices[app_id] = info
    return prices

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
