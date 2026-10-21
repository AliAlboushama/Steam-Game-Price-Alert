"""
IsThereAnyDeal (optional): the real all-time lowest price on Steam, not just what this bot has seen.
Needs a free API key from https://isthereanydeal.com/apps/my/ (the "API Key", not the OAuth client).
"""
import logging
import requests
from saved_games import get_itad_ids, save_itad_ids

API = "https://api.isthereanydeal.com"
STEAM_SHOP = 61
CHUNK = 200  # both endpoints take up to 200 ids per call

def _steam_key(item_id):
    """Our item id -> ITAD's Steam id: '1091500' -> 'app/1091500', 'sub:469' -> 'sub/469'."""
    item_id = str(item_id)
    if ":" in item_id:
        kind, number = item_id.split(":", 1)
        return f"{kind}/{number}"
    return f"app/{item_id}"

def _post(path, api_key, body, params=None):
    response = requests.post(f"{API}{path}", params=params, json=body,
                             headers={"ITAD-API-Key": api_key}, timeout=15)
    response.raise_for_status()
    return response.json()

def check_key(api_key):
    """True if the key works (one tiny lookup)."""
    try:
        _post(f"/lookup/id/shop/{STEAM_SHOP}/v1", api_key, ["app/220"])
        return True
    except Exception as e:
        logging.warning(f"IsThereAnyDeal key check failed: {e}")
        return False

def _itad_ids(item_ids, api_key):
    """{item_id: itad_id}, looking up (and caching) only the ones we haven't seen before."""
    keys = {str(i): _steam_key(i) for i in item_ids}
    cached = get_itad_ids(list(keys.values()))
    unknown = [k for k in keys.values() if k not in cached]
    for start in range(0, len(unknown), CHUNK):
        found = _post(f"/lookup/id/shop/{STEAM_SHOP}/v1", api_key, unknown[start:start + CHUNK])
        save_itad_ids(found)
        cached.update(found)
    return {item: cached.get(key) for item, key in keys.items() if cached.get(key)}

def get_steam_lows(item_ids, api_key, country_code):
    """
    All-time lowest Steam price per item, in the country's currency:
    {item_id: {'price': 14.99, 'currency': 'EUR', 'cut': 75, 'date': '2025-03-20'}}.
    Returns {} if there's no key or IsThereAnyDeal can't be reached.
    """
    if not api_key or not item_ids:
        return {}
    try:
        ids = _itad_ids(item_ids, api_key)
        by_itad = {v: k for k, v in ids.items()}
        lows = {}
        itad_list = list(by_itad)
        for start in range(0, len(itad_list), CHUNK):
            data = _post("/games/storelow/v2", api_key, itad_list[start:start + CHUNK],
                         params={"country": country_code, "shops": STEAM_SHOP})
            for game in data:
                steam_low = next((l for l in game.get('lows') or []
                                  if (l.get('shop') or {}).get('id') == STEAM_SHOP), None)
                if steam_low and game.get('id') in by_itad:
                    lows[by_itad[game['id']]] = {
                        'price': steam_low['price']['amount'],
                        'currency': steam_low['price'].get('currency'),
                        'cut': steam_low.get('cut'),
                        'date': (steam_low.get('timestamp') or "")[:10],
                    }
        return lows
    except Exception as e:
        logging.error(f"IsThereAnyDeal lookup failed: {e}")
        return {}
