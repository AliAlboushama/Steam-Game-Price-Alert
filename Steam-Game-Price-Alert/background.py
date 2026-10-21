"""
Background mode: check every saved game on a timer, with no menu.
Run with `python main.py --daemon` (forever) or `python main.py --once` (one check, for cron).

Staying healthy on a 24/7 server:
- every round has a time limit; a hung round exits so systemd/Docker restart the bot
- optional heartbeat URL (e.g. healthchecks.io): pinged each round, so you hear about it
  even when the whole server is down
- after 3 failed rounds in a row the bot posts a warning to Discord, and an all-clear when it recovers
- `--once` exits with code 2 when the check failed, so cron/monitoring can see it
"""
import sys
import time
import json
import signal
import logging
import faulthandler
from datetime import datetime, timedelta
import requests
from paths import data_path
from saved_info import load_user_info
from saved_games import initialize_database, get_games_with_details, add_game, remove_wishlist_games_not_in
from scanner import check_games, check_interval, MODE_AUTO
from steam_api import resolve_steam_id, get_wishlist, get_store_items, store_url
from notifier import send_notice, COLOR_TARGET

ROUND_TIME_LIMIT = 15 * 60  # seconds; a check never takes this long unless something hangs
WARN_AFTER_FAILURES = 3
HEALTH_FILE = data_path("health.json")

def _stop(signum, frame):
    # systemctl stop / docker stop send SIGTERM; handle it like Ctrl+C
    raise KeyboardInterrupt

def _ping(settings, suffix=""):
    """Heartbeat ping (healthchecks.io style: /start, success, /fail). Never fails the check."""
    url = (settings.get('healthcheck_url') or "").rstrip("/")
    if url:
        try:
            requests.get(url + suffix, timeout=10)
        except Exception as e:
            logging.warning(f"Heartbeat ping failed: {e}")

def _load_health():
    try:
        with open(HEALTH_FILE) as f:
            return json.load(f)
    except Exception:
        return {"failures": 0, "warned": False}

def _save_health(health):
    try:
        with open(HEALTH_FILE, "w") as f:
            json.dump(health, f)
    except Exception as e:
        logging.error(f"Could not save health state: {e}")

def _track_health(settings, failed, reason):
    """Count failed rounds; warn on Discord after 3 in a row, and say when it's fixed."""
    health = _load_health()
    if failed:
        health["failures"] += 1
        if health["failures"] >= WARN_AFTER_FAILURES and not health["warned"]:
            health["warned"] = send_notice(
                settings, "Steam Price Alert is having trouble",
                f"The last {health['failures']} checks failed: {reason}.\n"
                "Alerts may be missed until this is fixed. Details are in debug.log.")
    else:
        if health["warned"]:
            send_notice(settings, "Steam Price Alert is working again",
                        "Checks are succeeding again. No action needed.", color=COLOR_TARGET)
        health = {"failures": 0, "warned": False}
    _save_health(health)

def sync_wishlist(settings):
    """
    Add games that are new on the user's wishlist and remove wishlist games that left it
    (bought or un-wishlisted). Games added by hand are never removed.
    """
    steam_id = resolve_steam_id(settings['wishlist_profile'])
    app_ids = get_wishlist(steam_id) if steam_id else None
    if not app_ids:
        return  # network error, private or empty: change nothing
    for name in remove_wishlist_games_not_in(app_ids):
        print(f"Removed (no longer on your wishlist): {name}")
    existing = {str(g['app_id']) for g in get_games_with_details()}
    new_ids = [a for a in app_ids if a not in existing]
    if not new_ids:
        return
    items, _ = get_store_items(new_ids, settings['country_code'], settings['language'])
    for app_id in new_ids:
        if app_id in items and add_game(items[app_id]['name'], store_url(app_id), app_id, source='wishlist'):
            print(f"Added from wishlist: {items[app_id]['name']}")

def run_round(settings):
    """One full check. Returns (summary text, failed, reason)."""
    if settings.get('wishlist_sync') and settings.get('wishlist_profile'):
        sync_wishlist(settings)
    games = get_games_with_details()
    if not games:
        return "No games to check.", False, ""
    result = check_games(games, settings, MODE_AUTO)
    summary = f"Checked {result['checked']} game(s), sent {result['alerts']} alert(s)."
    if result['failed']:
        summary += f" Problem: {result['reason']}."
    return summary, result['failed'], result['reason']

def run(once=False):
    """Check all games now, then (unless once=True) again every interval until stopped."""
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        # Show lines straight away in logs, and never crash on a character the console can't print
        sys.stdout.reconfigure(line_buffering=True, errors="replace")

    settings = load_user_info()
    if not settings:
        print("No settings found. Run `python3 main.py` once to set up your country and Discord webhook.")
        return 1
    initialize_database()
    signal.signal(signal.SIGTERM, _stop)
    logging.info("Background mode started" + (" (single check)" if once else ""))

    try:
        while True:
            # Re-read settings every round, so changes made in the menu are picked up
            settings = load_user_info() or settings
            _ping(settings, "/start")
            faulthandler.dump_traceback_later(ROUND_TIME_LIMIT, exit=True)
            try:
                summary, failed, reason = run_round(settings)
            except Exception as e:
                logging.exception(f"Background check failed: {e}")
                summary, failed, reason = f"Check failed: {e}.", True, str(e)
            finally:
                faulthandler.cancel_dump_traceback_later()
            _ping(settings, "/fail" if failed else "")
            _track_health(settings, failed, reason)
            logging.info(summary)

            stamp = f"{datetime.now():%Y-%m-%d %H:%M}"
            if once:
                print(f"[{stamp}] {summary}")
                return 2 if failed else 0
            interval = check_interval(settings)
            next_check = datetime.now() + timedelta(seconds=interval)
            print(f"[{stamp}] {summary} Next check at {next_check:%H:%M}.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped.")
        logging.info("Background mode stopped")
        return 0
