"""
Background mode: check every saved game on a timer, with no menu.
Run with `python main.py --daemon` (forever) or `python main.py --once` (one check, for cron).
"""
import re
import sys
import time
import signal
import logging
from datetime import datetime, timedelta
from saved_info import load_user_info
from saved_games import initialize_database, get_games_with_details, add_game
from scanner import check_games, check_interval, MODE_AUTO
from steam_api import resolve_steam_id, get_wishlist, get_store_items

ANSI_COLORS = re.compile(r'\033\[[0-9;]*m')

class _StripColors:
    """Remove terminal colour codes when output goes to a log (systemd, Docker, a file)."""
    def __init__(self, stream):
        self.stream = stream
    def write(self, text):
        return self.stream.write(ANSI_COLORS.sub('', text))
    def flush(self):
        self.stream.flush()
    def __getattr__(self, name):
        return getattr(self.stream, name)

def _stop(signum, frame):
    # systemctl stop / docker stop send SIGTERM; handle it like Ctrl+C
    raise KeyboardInterrupt

def sync_wishlist(settings):
    """Add games that are new on the user's wishlist. Returns how many were added."""
    steam_id = resolve_steam_id(settings['wishlist_profile'])
    app_ids = get_wishlist(steam_id) if steam_id else None
    if not app_ids:
        return 0
    existing = {str(g['app_id']) for g in get_games_with_details()}
    new_ids = [a for a in app_ids if a not in existing]
    if not new_ids:
        return 0
    items = get_store_items(new_ids, settings['country_code'], settings['language'])
    added = 0
    for app_id in new_ids:
        if app_id in items and add_game(items[app_id]['name'],
                                        f"https://store.steampowered.com/app/{app_id}/", app_id):
            print(f"Added from wishlist: {items[app_id]['name']}")
            added += 1
    return added

def run(once=False):
    """Check all games now, then (unless once=True) again every interval until stopped."""
    if sys.stdout is not None:
        if hasattr(sys.stdout, "reconfigure"):
            # Show lines straight away in logs, and never crash on an emoji the console can't print
            sys.stdout.reconfigure(line_buffering=True, errors="replace")
        if not sys.stdout.isatty():
            sys.stdout = _StripColors(sys.stdout)

    settings = load_user_info()
    if not settings:
        print("No settings found. Run `python main.py` once to set up your country and Discord webhook.")
        return 1
    initialize_database()
    signal.signal(signal.SIGTERM, _stop)
    logging.info("Background mode started" + (" (single check)" if once else ""))

    try:
        while True:
            # Re-read settings and games every round, so changes made in the menu are picked up
            settings = load_user_info() or settings
            try:
                if settings.get('wishlist_sync') and settings.get('wishlist_profile'):
                    sync_wishlist(settings)
                games = get_games_with_details()
                alerts = check_games(games, settings, MODE_AUTO) if games else 0
                summary = f"Checked {len(games)} game(s), sent {alerts} alert(s)."
            except Exception as e:
                logging.exception(f"Background check failed: {e}")
                summary = f"Check failed: {e} (will try again)"
            if once:
                print(f"[{datetime.now():%Y-%m-%d %H:%M}] {summary}")
                return 0
            interval = check_interval(settings)
            next_check = datetime.now() + timedelta(seconds=interval)
            print(f"[{datetime.now():%Y-%m-%d %H:%M}] {summary} Next check at {next_check:%H:%M}.")
            logging.info(summary)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped.")
        logging.info("Background mode stopped")
        return 0
