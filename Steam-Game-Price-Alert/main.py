import sys
import html
import logging
import argparse
from rich.table import Table
from rich.text import Text
import ui
import background
from paths import data_path
from saved_info import load_user_info, save_user_info
from utils import (
    extract_app_id, get_game_details, get_detailed_game_info,
    validate_country_code, validate_language_code,
    validate_webhook_url, validate_steam_link, format_sale_end
)
from saved_games import (
    initialize_database, add_game as add_game_to_db, remove_game,
    save_price_threshold, get_games_with_details,
    save_price_history, get_historical_low, is_lowest_ever
)
from steam_api import (get_prices, get_store_items, search_games, resolve_steam_id, get_wishlist,
                       get_dlc, store_url, is_app)
from itad import get_steam_lows, check_key
from notifier import send_alerts
from scanner import scan_for_sales, scan_multiple_games

# Define constants
COUNTRY_CODE_PROMPT = "Country code (e.g. US, GB, DE, FI): "
LANGUAGE_PROMPT = "Language code (e.g. en, de, fr): "
WEBHOOK_URL_PROMPT = "Discord webhook URL: "
BOT_NAME_PROMPT = "Bot name (Enter for Discord's default): "
BOT_AVATAR_PROMPT = "Bot avatar image URL (Enter for none): "
CORE_SETTINGS = ("country_code", "language", "webhook_url", "bot_name", "bot_avatar")

def setup_logging():
    """Log everything to debug.log next to the scripts. Done here, once, before anything logs."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.FileHandler(data_path("debug.log"), encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root.addHandler(handler)
    logging.getLogger("urllib3").setLevel(logging.INFO)

def _ask_valid(prompt, check, error, transform=lambda v: v):
    while True:
        value = transform(ui.ask(prompt))
        if check(value):
            return value
        ui.error(error)

def get_user_info():
    """First run: ask for the settings the bot needs."""
    ui.header("First-time setup")
    ui.note("Your country decides the store and currency. Everything can be changed later in Settings.\n")
    country_code = _ask_valid(COUNTRY_CODE_PROMPT, validate_country_code,
                              "Please enter a 2-letter code (e.g. US, GB, DE).", str.upper)
    language = _ask_valid(LANGUAGE_PROMPT, validate_language_code,
                          "Please enter a code like en, es or fr.", str.lower)
    webhook_url = _ask_valid(WEBHOOK_URL_PROMPT, validate_webhook_url,
                             "That isn't a Discord webhook URL (https://discord.com/api/webhooks/...).")
    bot_name = ui.ask(BOT_NAME_PROMPT)
    bot_avatar = ui.ask(BOT_AVATAR_PROMPT)
    return country_code, language, webhook_url, bot_name, bot_avatar

def save_settings(settings):
    """Write the settings dict (including any extra options) back to user_info.json."""
    extra = {k: v for k, v in settings.items() if k not in CORE_SETTINGS}
    save_user_info(*(settings[k] for k in CORE_SETTINGS), **extra)

def games_table(games):
    """Numbered table of saved games."""
    table = ui.table(("#", {"style": "accent", "justify": "right"}), "Game", "Target", "Added from")
    for index, game in enumerate(games, start=1):
        target = f"{game['threshold']:.2f}" if game['threshold'] is not None else ""
        source = "wishlist" if game.get('source') == 'wishlist' else ""
        if not is_app(game['app_id']):
            source = (source + " · " if source else "") + str(game['app_id']).split(":")[0]
        table.add_row(str(index), Text(game['name'], style="name"), target, Text(source, style="muted"))
    ui.console.print(table)

def pick_game(games, prompt):
    """Show the game table and return the chosen game, or None to cancel."""
    games_table(games)
    while True:
        answer = ui.ask(f"{prompt} (0 to cancel): ")
        if answer == "0" or answer == "":
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(games):
            return games[int(answer) - 1]
        ui.error("Please enter a number from the list.")

def main_menu():
    """Displays the main menu and handles user choices."""
    initialize_database()
    settings = load_user_info()
    if not settings:
        save_user_info(*get_user_info())
        settings = load_user_info()

    actions = {
        "1": lambda: scan_for_sales(settings),
        "2": lambda: add_game(settings),
        "3": lambda: scan_multiple_games(settings),
        "4": remove_game_menu,
        "5": set_price_threshold,
        "6": lambda: view_current_prices(settings),
        "7": lambda: view_detailed_game_info(settings),
        "8": lambda: import_wishlist(settings),
        "9": lambda: settings_menu(settings),
    }
    while True:
        games = get_games_with_details()
        ui.header("Saved games", f"{settings['country_code']} · {len(games)} game(s)")
        if games:
            games_table(games)
            ui.console.print()
        else:
            ui.note("No games yet. Add one (2) or import your Steam wishlist (8).\n")
        ui.menu([("1", "Scan one game"), ("2", "Add a game"), ("3", "Scan several games"),
                 ("4", "Remove a game"), ("5", "Set price target"),
                 ("6", "Current prices"), ("7", "Game details"), ("8", "Import Steam wishlist"),
                 ("9", "Settings"), ("0", "Exit")])
        choice = ui.ask("Choose: ")
        if choice == "0":
            ui.note("Bye.")
            return
        if choice in actions:
            actions[choice]()
        else:
            ui.error("Please choose one of the numbers above.")
            ui.pause("Press Enter to continue")

def search_and_pick(term, settings):
    """Search the Steam store by name and let the user pick a result. Returns an app id or None."""
    results = search_games(term, settings['country_code'], settings['language'])
    if not results:
        ui.error(f"No games found for '{term}'.")
        return None
    picked = pick_game([{'name': name, 'app_id': app_id, 'threshold': None} for app_id, name in results],
                       "Which one")
    return picked['app_id'] if picked else None

def _item_name(item_id, settings):
    """Name of a game, package or bundle (any store if it isn't sold in the user's country)."""
    items, _ = get_store_items([item_id], settings['country_code'], settings['language'])
    if item_id in items:
        return items[item_id]['name']
    if is_app(item_id):
        data = get_game_details(item_id, "US", "en")
        return data.get('name') if data else None
    return None

def offer_dlc(app_id, game_name, settings):
    """After adding a game, offer to watch its DLC too."""
    dlc_ids = get_dlc(app_id)
    if not dlc_ids:
        return
    if ui.ask(f"{game_name} has {len(dlc_ids)} DLC. Watch them too? (y/n): ").lower() != "y":
        return
    items, _ = get_store_items(dlc_ids, settings['country_code'], settings['language'])
    added = sum(1 for d in dlc_ids if d in items
                and add_game_to_db(items[d]['name'], store_url(d), d))
    ui.ok(f"Added {added} DLC.")

def add_game(settings):
    """Add a game, DLC, package or bundle by link, app id or name."""
    while True:
        ui.header("Add a game")
        ui.note("Paste a Steam store link (game, DLC, /sub/ package or /bundle/), an app id,\n"
                "or type a name to search.\n")
        answer = ui.ask("Link, id or name (0 to cancel): ")
        if answer in ("0", ""):
            return
        if answer.isdigit() or validate_steam_link(answer):
            item_id = extract_app_id(answer)
        elif answer.lower().startswith(("http://", "https://", "www.")):
            ui.error("That isn't a Steam store link (e.g. https://store.steampowered.com/app/123456/).")
            ui.pause("Press Enter to try again")
            continue
        else:
            item_id = search_and_pick(answer, settings)
            if not item_id:
                ui.pause("Press Enter to try again")
                continue

        name = _item_name(item_id, settings)
        if not name:
            ui.error("Steam doesn't know that id. Please check it and try again.")
            ui.pause("Press Enter to try again")
            continue
        if add_game_to_db(name, store_url(item_id), item_id):
            ui.ok(f"Added [name]{name}[/]")
            if is_app(item_id):
                offer_dlc(item_id, name, settings)
        else:
            ui.warn(f"{name} is already in your list.")
        if ui.ask("Add another? (y/n): ").lower() != "y":
            return

def remove_game_menu():
    """Removes a game from the saved games list."""
    games = get_games_with_details()
    if not games:
        ui.warn("No games to remove.")
        ui.pause()
        return
    ui.header("Remove a game")
    game = pick_game(games, "Game number to remove")
    if game:
        remove_game(game['id'])
        ui.ok(f"Removed {game['name']} and its price history.")
        ui.pause()

def set_price_threshold():
    """Handles setting price thresholds for games."""
    games = get_games_with_details()
    if not games:
        ui.warn("No games yet - add one first.")
        ui.pause()
        return
    ui.header("Set price target")
    game = pick_game(games, "Game number")
    if not game:
        return
    if game['threshold'] is not None:
        ui.note(f"Current target for {game['name']}: {game['threshold']:.2f}")
    while True:
        raw = ui.ask("Target price in your store's currency, e.g. 19.99 (0 removes it): ").replace(",", ".")
        try:
            threshold = float(raw)
        except ValueError:
            ui.error("Please enter a number like 19.99.")
            continue
        if threshold < 0:
            ui.error("A target can't be negative.")
            continue
        break
    if threshold == 0:
        save_price_threshold(game['id'], None)
        ui.ok(f"Target for {game['name']} removed.")
    else:
        save_price_threshold(game['id'], threshold)
        ui.ok(f"Target for {game['name']} set to {threshold:.2f}.")
    ui.pause()

def view_current_prices(settings):
    """All prices at once, in a table."""
    games = get_games_with_details()
    ui.header("Current prices", settings['country_code'])
    if not games:
        ui.warn("No games in your list yet.")
        ui.pause()
        return
    country_code = settings['country_code']
    with ui.console.status("Fetching prices from Steam..."):
        ids = [g['app_id'] for g in games]
        prices, failed = get_prices(ids, country_code, settings['language'])
        lows = get_steam_lows(ids, settings.get('itad_api_key'), country_code)
    if failed:
        ui.warn("Steam didn't answer for some games - try again in a minute.")

    table = ui.table("Game", ("Price", {"no_wrap": True}), ("", {"no_wrap": True}), "Sale ends", "Notes")
    for game in games:
        info = prices.get(str(game['app_id']))
        notes = Text()
        if info and info.get('final') is not None:
            current_price = info['final'] / 100
            discount = info['discount_percent']
            steam_low = lows.get(str(game['app_id']))
            if steam_low:
                lowest = discount > 0 and current_price <= steam_low['price'] + 0.001
            else:
                lowest = is_lowest_ever(game['id'], game['app_id'], current_price, discount, country_code)
            local_low = get_historical_low(game['id'], game['app_id'], country_code)
            if lowest:
                notes.append("Lowest ever  ", style="gold")
            if steam_low and not lowest:
                notes.append(f"Low {steam_low['price']:.2f}  ", style="muted")
            elif not steam_low and local_low is not None and local_low < current_price:
                notes.append(f"Lowest seen {local_low:.2f}  ", style="muted")
            if game['threshold'] is not None:
                met = current_price <= game['threshold']
                notes.append(f"Target {game['threshold']:.2f}", style="good" if met else "muted")
            save_price_history(game['id'], game['app_id'], current_price, discount, country_code)
        ends = format_sale_end(info['discount_end']) if info and info.get('discount_end') else ""
        table.add_row(Text(game['name'], style="name"), ui.price_text(info),
                      ui.discount_badge((info or {}).get('discount_percent', 0)), Text(ends, style="muted"), notes)
    ui.console.print(table)
    ui.pause()

def view_detailed_game_info(settings):
    """Everything about one game."""
    games = get_games_with_details()
    if not games:
        ui.warn("No games in your list yet.")
        ui.pause()
        return
    ui.header("Game details")
    game = pick_game(games, "Game number")
    if not game:
        return

    item_id = str(game['app_id'])
    with ui.console.status("Loading from Steam..."):
        prices, _ = get_store_items([item_id], settings['country_code'], settings['language'])
        sale = prices.get(item_id)
        details = get_detailed_game_info(item_id, settings['country_code'], settings['language']) \
            if is_app(item_id) else None
        lows = get_steam_lows([item_id], settings.get('itad_api_key'), settings['country_code'])

    ui.header("Game details")
    name = (details or {}).get('name') or (sale or {}).get('name') or game['name']
    ui.console.print(Text(name, style="bold #ffffff"))
    ui.console.print(Text(store_url(item_id), style="muted"))
    ui.console.print()

    info = sale or (details or {}).get('price')
    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="muted", no_wrap=True)
    grid.add_column()
    price = ui.price_text(info)
    if info and info.get('discount_percent'):
        price.append("  ")
        price.append_text(ui.discount_badge(info['discount_percent']))
    grid.add_row("Price", price)
    if info and info.get('discount_end'):
        grid.add_row("Sale ends", format_sale_end(info['discount_end']))
    if lows.get(item_id):
        low = lows[item_id]
        grid.add_row("All-time low", f"{low['price']:.2f} {low.get('currency') or ''} on Steam ({low['date']})")
    else:
        local_low = get_historical_low(game['id'], item_id, settings['country_code'])
        if local_low is not None and info and info.get('final') is not None and local_low < info['final'] / 100:
            grid.add_row("Lowest seen", f"{local_low:.2f}")
    if game['threshold'] is not None:
        grid.add_row("Your target", f"{game['threshold']:.2f}")

    if details:
        grid.add_row("", "")
        grid.add_row("Released", details['release_date'])
        if details['developers']:
            grid.add_row("Developer", ", ".join(details['developers']))
        if details['publishers']:
            grid.add_row("Publisher", ", ".join(details['publishers']))
        if details['genres']:
            grid.add_row("Genres", ", ".join(details['genres']))
        if details['total_reviews'] > 0:
            positive = round(100 * details['total_positive'] / details['total_reviews'])
            grid.add_row("Reviews", f"{details['review_score_desc']} · {positive}% of "
                                    f"{details['total_reviews']:,} reviews")
        if details['metacritic']:
            grid.add_row("Metacritic", f"{details['metacritic']}/100")
        if details['categories']:
            grid.add_row("Features", ", ".join(details['categories']))
        if details['short_description']:
            grid.add_row("", "")
            grid.add_row("About", html.unescape(details['short_description']))
    ui.console.print(grid)
    ui.pause()

def import_wishlist(settings):
    """Add every game on a public Steam wishlist to the watchlist."""
    ui.header("Import Steam wishlist")
    ui.note("Your wishlist must be public: Steam > Profile > Edit Profile > Privacy Settings >\n"
            "Game details = Public.\n")
    saved = settings.get('wishlist_profile')
    prompt = "Profile link, custom URL name or SteamID64"
    if saved:
        prompt += f" (Enter = {saved})"
    profile = ui.ask(prompt + ": ") or saved or ""
    if not profile or profile == "0":
        return

    with ui.console.status("Reading your wishlist..."):
        steam_id = resolve_steam_id(profile)
        app_ids = get_wishlist(steam_id) if steam_id else None
    if not steam_id:
        ui.error("Couldn't find that Steam profile. Try the full link to your profile.")
        ui.pause()
        return
    if app_ids is None:
        ui.error("Couldn't reach Steam. Please try again later.")
        ui.pause()
        return
    if not app_ids:
        ui.error("The wishlist is empty or private.")
        ui.pause()
        return

    existing = {str(g['app_id']) for g in get_games_with_details()}
    new_ids = [a for a in app_ids if a not in existing]
    settings['wishlist_profile'] = profile
    save_settings(settings)
    ui.console.print(f"Found [name]{len(app_ids)}[/] games on the wishlist, "
                     f"[name]{len(new_ids)}[/] not in your list yet.")
    if not new_ids:
        ui.pause()
        return

    with ui.console.status("Looking up names..."):
        items, _ = get_store_items(new_ids, settings['country_code'], settings['language'])
    to_add = [(a, items[a]['name']) for a in new_ids if a in items]
    skipped = len(new_ids) - len(to_add)
    table = ui.table("Game", ("Price", {"no_wrap": True}), ("", {"no_wrap": True}))
    for app_id, name in to_add:
        table.add_row(name, ui.price_text(items[app_id]), ui.discount_badge(items[app_id]['discount_percent']))
    ui.console.print(table)
    if skipped:
        ui.note(f"{skipped} game(s) skipped: not sold in your store or removed from Steam.")
    if not to_add or ui.ask(f"Add these {len(to_add)} games? (y/n): ").lower() != "y":
        return
    added = sum(1 for app_id, name in to_add
                if add_game_to_db(name, store_url(app_id), app_id, source='wishlist'))
    ui.ok(f"Added {added} games.")
    ui.pause()

def send_test_notification(settings):
    """Demo mode: send a clearly marked TEST alert through the real Discord code, using a real price."""
    games = get_games_with_details() or [{'id': 0, 'name': 'Cyberpunk 2077', 'app_id': '1091500', 'threshold': None}]
    with ui.console.status("Sending a test message to Discord..."):
        ids = [str(g['app_id']) for g in games]
        prices, _ = get_prices(ids, settings['country_code'], settings['language'])
        priced = [g for g in games if (prices.get(str(g['app_id'])) or {}).get('final') is not None]
        # Prefer a game that's really on sale, so the test looks like a real alert
        priced.sort(key=lambda g: -prices[str(g['app_id'])].get('discount_percent', 0))
        if not priced:
            ui.error("Couldn't get a price from Steam to build the test message.")
            return
        game = priced[0]
        info = prices[str(game['app_id'])]
        on_sale = info.get('discount_percent', 0) > 0
        alert = {'name': game['name'], 'url': store_url(game['app_id']), 'price': info,
                 'reason': "sale" if on_sale else "target",
                 'threshold': None if on_sale else info['final'] / 100,
                 'lowest_ever': False, 'loud': True,
                 'steam_low': get_steam_lows([game['app_id']], settings.get('itad_api_key'),
                                             settings['country_code']).get(str(game['app_id']))}
        sent = send_alerts([alert], settings, test=True)
    if sent:
        ui.ok(f"Discord accepted the test message ({game['name']}). Check your channel.")
    else:
        ui.error("Discord did NOT accept the message. Check the webhook URL (details in debug.log).")

def _toggle(settings, key, default=False):
    settings[key] = not settings.get(key, default)
    ui.ok(f"Now {'ON' if settings[key] else 'OFF'}.")

def settings_menu(settings):
    """Change saved settings without deleting user_info.json."""
    def on(key, default=False):
        return "on" if settings.get(key, default) else "off"

    while True:
        ui.header("Settings")
        webhook = settings['webhook_url']
        masked = webhook[:webhook.find('/api/webhooks/') + 14] + "..." if '/api/webhooks/' in webhook else webhook
        grid = Table.grid(padding=(0, 3))
        grid.add_column(style="muted"); grid.add_column()
        grid.add_column(style="muted"); grid.add_column()
        grid.add_row("Country", settings['country_code'], "Language", settings['language'])
        grid.add_row("Webhook", masked, "Bot name", settings['bot_name'] or "Discord default")
        grid.add_row("Check every", f"{settings.get('check_interval_minutes', 60)} min",
                     "Minimum discount", f"{settings.get('min_discount_percent', 0)}%")
        grid.add_row("Quiet ordinary sales", on('quiet_ordinary_sales', True),
                     "Only all-time lows", on('alert_only_at_lowest'))
        grid.add_row("IsThereAnyDeal key", "set" if settings.get('itad_api_key') else "not set",
                     "Wishlist auto-sync", on('wishlist_sync'))
        grid.add_row("Heartbeat URL", "set" if settings.get('healthcheck_url') else "not set", "", "")
        ui.console.print(grid)
        ui.console.print()
        ui.menu([("1", "Country"), ("2", "Language"), ("3", "Discord webhook"), ("4", "Bot name"),
                 ("5", "Bot avatar"), ("6", "How often to check"), ("7", "Minimum discount"),
                 ("8", "Quiet ordinary sales on/off"), ("9", "IsThereAnyDeal API key"),
                 ("10", "Only alert at all-time low on/off"), ("11", "Wishlist auto-sync on/off"),
                 ("12", "Heartbeat URL"), ("13", "Send a test notification"), ("0", "Back")])
        choice = ui.ask("Choose: ")
        if choice == "0":
            return
        if choice == "1":
            value = ui.ask(COUNTRY_CODE_PROMPT).upper()
            if validate_country_code(value):
                settings['country_code'] = value
            else:
                ui.error("Invalid country code.")
        elif choice == "2":
            value = ui.ask(LANGUAGE_PROMPT).lower()
            if validate_language_code(value):
                settings['language'] = value
            else:
                ui.error("Invalid language code.")
        elif choice == "3":
            value = ui.ask(WEBHOOK_URL_PROMPT)
            if validate_webhook_url(value):
                settings['webhook_url'] = value
            else:
                ui.error("Invalid webhook URL.")
        elif choice == "4":
            settings['bot_name'] = ui.ask(BOT_NAME_PROMPT)
        elif choice == "5":
            settings['bot_avatar'] = ui.ask(BOT_AVATAR_PROMPT)
        elif choice == "6":
            value = ui.ask("Check every how many minutes? (10 or more, default 60): ")
            if value.isdigit() and int(value) >= 10:
                settings['check_interval_minutes'] = int(value)
            else:
                ui.error("Please enter a whole number of 10 or more.")
        elif choice == "7":
            value = ui.ask("Only alert for sales of at least how many percent? (0-95): ")
            if value.isdigit() and 0 <= int(value) <= 95:
                settings['min_discount_percent'] = int(value)
            else:
                ui.error("Please enter a number from 0 to 95.")
        elif choice == "8":
            ui.note("On: ordinary sales arrive without a sound; a met target or lowest-ever price still notifies.")
            _toggle(settings, 'quiet_ordinary_sales', default=True)
        elif choice == "9":
            ui.note("Free key: isthereanydeal.com/apps/my/ - use the 'API Key', not the OAuth client ID/secret.")
            value = ui.ask("API key (Enter to remove): ")
            if not value:
                settings.pop('itad_api_key', None)
                ui.ok("Removed.")
            elif check_key(value):
                settings['itad_api_key'] = value
                ui.ok("Key works.")
            else:
                ui.error("IsThereAnyDeal didn't accept that key.")
        elif choice == "10":
            if not settings.get('itad_api_key'):
                ui.warn("This needs an IsThereAnyDeal API key first (option 9).")
            else:
                _toggle(settings, 'alert_only_at_lowest')
        elif choice == "11":
            if not settings.get('wishlist_profile'):
                ui.warn("Import your wishlist once first (main menu option 8).")
            else:
                ui.note("Background mode adds new wishlist games and removes ones you bought or un-wishlisted.")
                _toggle(settings, 'wishlist_sync')
        elif choice == "12":
            ui.note("Optional: a healthchecks.io ping URL. It warns you if the bot stops checking.")
            value = ui.ask("Heartbeat URL (Enter to remove): ")
            if value and not value.startswith("https://"):
                ui.error("Please enter an https:// URL.")
            elif value:
                settings['healthcheck_url'] = value
            else:
                settings.pop('healthcheck_url', None)
        elif choice == "13":
            send_test_notification(settings)
            ui.pause("Press Enter to continue")
            continue
        else:
            ui.error("Please choose one of the numbers above.")
        save_settings(settings)
        ui.pause("Press Enter to continue")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Steam Game Price Alert - Discord alerts for Steam sales.")
    parser.add_argument("--daemon", "--background", action="store_true",
                        help="check all saved games on a timer, without the menu (for servers)")
    parser.add_argument("--once", action="store_true",
                        help="check all saved games once and exit (for cron)")
    args = parser.parse_args()
    setup_logging()
    if args.daemon or args.once:
        sys.exit(background.run(once=args.once))
    try:
        main_menu()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or Ctrl+D: just leave
        ui.note("\nBye.")
    except Exception as e:
        logging.exception(f"[ERROR] An error occurred: {e}")
        ui.error(f"Something went wrong: {e}")
        ui.note(f"Details were written to {data_path('debug.log')}")
