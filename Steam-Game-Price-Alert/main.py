import sys
import html
import shutil
import logging
import argparse
import textwrap
import background
from paths import data_path
from saved_info import load_user_info, save_user_info
from utils import (
    get_all_games, extract_app_id, get_game_details, get_detailed_game_info,
    validate_country_code, validate_language_code,
    validate_webhook_url, validate_steam_link,
    clear_screen, print_header, format_price_line, format_sale_end
)
from steam_api import get_prices, get_store_items, search_games, resolve_steam_id, get_wishlist
from notifier import send_discord_notification
from saved_games import (
    initialize_database, add_game as add_game_to_db, remove_game,
    save_price_threshold, get_games_with_details,
    save_price_history, get_historical_low, is_lowest_ever
)
from scanner import scan_for_sales, scan_multiple_games

# Define constants
COUNTRY_CODE_PROMPT = "Enter the country code (e.g., US, GB, DE, FI): "
LANGUAGE_PROMPT = "Enter the language code (e.g., en for English, de for German): "
WEBHOOK_URL_PROMPT = "Enter your Discord webhook URL: "
BOT_NAME_PROMPT = "Enter the bot name: "
BOT_AVATAR_PROMPT = "Enter the bot avatar URL (e.g., a link to a PNG image, or leave empty): "

def setup_logging():
    """Log everything to debug.log next to the scripts. Done here, once, before anything logs."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.FileHandler(data_path("debug.log"), encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root.addHandler(handler)
    logging.getLogger("urllib3").setLevel(logging.INFO)

def print_option(title, color_code="\033[0;33m"):
    """Prints an option with a nice design."""
    print(f"{color_code} {title}\033[0m")

def get_user_input(prompt):
    """Gets user input and strips any leading/trailing whitespace."""
    return input(prompt).strip()

def get_user_info():
    """Gets user information from the user with validation."""
    while True:
        country_code = get_user_input(COUNTRY_CODE_PROMPT).upper()
        if validate_country_code(country_code):
            break
        print("\033[1;31mInvalid country code. Please enter a 2-letter code (e.g., US, GB, DE).\033[0m")

    while True:
        language = get_user_input(LANGUAGE_PROMPT).lower()
        if validate_language_code(language):
            break
        print("\033[1;31mInvalid language code. Please enter a valid code (e.g., en, es, fr).\033[0m")

    while True:
        webhook_url = get_user_input(WEBHOOK_URL_PROMPT)
        if validate_webhook_url(webhook_url):
            break
        print("\033[1;31mInvalid webhook URL. Please enter a valid Discord webhook URL.\033[0m")

    bot_name = get_user_input(BOT_NAME_PROMPT)
    bot_avatar = get_user_input(BOT_AVATAR_PROMPT)
    return country_code, language, webhook_url, bot_name, bot_avatar

def wrap_text(text, indent="  "):
    """Wrap long text to the terminal width (max 100 columns) so lines don't break mid-word."""
    width = min(shutil.get_terminal_size((80, 24)).columns, 100)
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)

def pick_game(games, prompt, color="\033[1;33m"):
    """Show a numbered game list and return the chosen game, or None to cancel."""
    for index, game in enumerate(games, start=1):
        print(f"{color} {index}. {game['name']}\033[0m")
    while True:
        try:
            choice = int(get_user_input(f"\n\033[1;36m{prompt} (or 0 to cancel): \033[0m"))
        except ValueError:
            print("\n\033[1;31mPlease enter a valid number.\033[0m")
            continue
        if choice == 0:
            return None
        if 1 <= choice <= len(games):
            return games[choice - 1]
        print("\n\033[1;31mInvalid choice. Try again.\033[0m")

def main_menu():
    """Displays the main menu and handles user choices."""
    initialize_database()
    user_info = load_user_info()
    if not user_info:
        country_code, language, webhook_url, bot_name, bot_avatar = get_user_info()
        save_user_info(country_code, language, webhook_url, bot_name, bot_avatar)
        user_info = load_user_info()
    settings = user_info

    while True:
        clear_screen()
        print_header("🎮 Saved Games 🎮")
        games = get_all_games()
        if games:
            for index, (game_id, game_name) in enumerate(games, start=1):
                print(f"\033[1;32m {index}. {game_name}\033[0m")
        else:
            print("\033[1;31m No games added yet.\033[0m")

        print_header("Choose an Option:")
        print_option("1. Scan for sales")
        print_option("2. Add a new game")
        print_option("3. Scan multiple games")
        print_option("4. Remove a game")
        print_option("5. Set price threshold")
        print_option("6. View current prices")
        print_option("7. View detailed game info")
        print_option("8. Import my Steam wishlist")
        print_option("9. Settings (and send a test notification)")
        print_option("0. Exit")
        choice = get_user_input("\033[1;36mEnter a number (0-9): \033[0m")
        if choice == "1":
            scan_for_sales(settings)
        elif choice == "2":
            add_game(settings)
        elif choice == "3":
            scan_multiple_games(settings)
        elif choice == "4":
            remove_game_menu()
        elif choice == "5":
            set_price_threshold()
        elif choice == "6":
            view_current_prices(settings)
        elif choice == "7":
            view_detailed_game_info(settings)
        elif choice == "8":
            import_wishlist(settings)
        elif choice == "9":
            settings_menu(settings)
        elif choice == "0":
            print("\nBye!")
            return
        else:
            print("\n\033[1;31mInvalid option. Try again!\033[0m\n")
            input("Press Enter to continue...")

def search_and_pick(term, settings):
    """Search the Steam store by name and let the user pick a result. Returns an app id or None."""
    print("\033[1;33mSearching Steam...\033[0m")
    results = search_games(term, settings['country_code'], settings['language'])
    if not results:
        print(f"\033[1;31mNo games found for '{term}'.\033[0m")
        return None
    print(f"\n\033[1;36mResults for '{term}':\033[0m")
    picked = pick_game([{'name': f"{name}  (app {app_id})", 'app_id': app_id} for app_id, name in results],
                       "Enter the number of the right game")
    return picked['app_id'] if picked else None

def add_game(settings):
    """Handles adding a new game with an option to add more or return."""
    while True:
        clear_screen()
        print_header("Add a New Game")
        steam_link = get_user_input("Enter a Steam link, app id, or game name to search (or 0 to cancel): ")
        if steam_link == "0":
            break
        if not steam_link:
            print("\033[1;31mThis cannot be empty.\033[0m")
            input("Press Enter to try again...")
            continue
        if steam_link.isdigit() or validate_steam_link(steam_link):
            app_id = extract_app_id(steam_link)
        elif steam_link.lower().startswith(("http://", "https://", "www.")):
            print("\033[1;31mInvalid Steam link format. Please provide a valid Steam store link (e.g., https://store.steampowered.com/app/123456/).\033[0m")
            input("Press Enter to try again...")
            continue
        else:
            app_id = search_and_pick(steam_link, settings)
            if not app_id:
                input("Press Enter to try again...")
                continue
        if not app_id:
            print("\033[1;31mCould not extract app ID from Steam link. Please provide a valid Steam store link.\033[0m")
            input("Press Enter to try again...")
            continue
        # Some games aren't sold in every country, so fall back to the US store for the name
        game_data = (get_game_details(app_id, settings['country_code'], settings['language'])
                     or get_game_details(app_id, "US", "en"))
        if game_data:
            game_name = game_data.get('name', 'Unknown Game')
            store_link = f"https://store.steampowered.com/app/{app_id}/"
            if add_game_to_db(game_name, store_link, app_id):
                print(f"\n\033[1;32m[OK] Game '{game_name}' added successfully!\033[0m\n")
            else:
                print(f"\n\033[1;33m'{game_name}' is already in your list.\033[0m\n")
        else:
            print("\033[1;31mFailed to fetch game details. Please try again.\033[0m")
            input("Press Enter to try again...")
            continue
        print("\033[1;36mWhat do you want to do next?\033[0m")
        print_option("1. Add another game")
        print_option("2. Return to menu")
        next_choice = get_user_input("\033[1;36mEnter a number (1-2): \033[0m")
        if next_choice == "2":
            break

def remove_game_menu():
    """Removes a game from the saved games list."""
    games = get_games_with_details()
    if not games:
        print("\n\033[1;31mNo games to remove!\033[0m")
        input("\nPress Enter to return to menu...")
        return
    clear_screen()
    print_header("Remove a Game")
    print("\033[1;36mSelect a game to remove:\033[0m")
    game = pick_game(games, "Enter game number to remove")
    if game:
        remove_game(game['id'])
        print(f"\n\033[1;32m✓ '{game['name']}' removed successfully!\033[0m")
        input("\nPress Enter to return to menu...")

def set_price_threshold():
    """Handles setting price thresholds for games."""
    games = get_games_with_details()
    if not games:
        print("\n\033[1;31mNo games to set thresholds for!\033[0m")
        input("\nPress Enter to return to menu...")
        return
    clear_screen()
    print_header("Set Price Threshold")
    print("\033[1;36mSelect a game to set a price threshold:\033[0m")
    game = pick_game(games, "Enter game number to set threshold")
    if not game:
        return
    if game['threshold'] is not None:
        print(f"\nCurrent target for '{game['name']}': {game['threshold']:.2f}")
    while True:
        raw = get_user_input(f"\n\033[1;34mEnter the price threshold for '{game['name']}' in your store's "
                             f"currency (e.g. 19.99, or 0 to remove it): \033[0m").replace(",", ".")
        try:
            threshold = float(raw)
        except ValueError:
            print("\n\033[1;31mPlease enter a number like 19.99.\033[0m")
            continue
        if threshold < 0:
            print("\n\033[1;31mPrice threshold can't be negative.\033[0m")
            continue
        break
    if threshold == 0:
        save_price_threshold(game['id'], None)
        print(f"\n\033[1;32mPrice threshold for '{game['name']}' removed.\033[0m")
    else:
        save_price_threshold(game['id'], threshold)
        print(f"\n\033[1;32mPrice threshold for '{game['name']}' set to {threshold:.2f} successfully!\033[0m")
    input("\nPress Enter to return to menu...")

def view_current_prices(settings):
    """View current prices for all games in the watchlist."""
    clear_screen()
    print_header("💰 Current Prices 💰")
    games = get_games_with_details()
    if not games:
        print("\n\033[1;31mNo games in watchlist!\033[0m")
        input("\nPress Enter to return to menu...")
        return

    print("\n\033[1;33mFetching current prices...\033[0m\n")
    print("-" * 80)
    country_code = settings['country_code']
    prices = get_prices([g['app_id'] for g in games], country_code, settings['language'])

    for game in games:
        print(f"\033[1;36m{game['name']}\033[0m")
        info = prices.get(str(game['app_id']))
        if info and info['final'] is not None:
            current_price = info['final'] / 100
            previous_low = get_historical_low(game['id'], game['app_id'], country_code)
            print(f"  Price: \033[1;32m{format_price_line(info)}\033[0m")
            if info.get('discount_end'):
                print(f"  Sale ends: {format_sale_end(info['discount_end'])}")
            if is_lowest_ever(game['id'], game['app_id'], current_price, info['discount_percent'], country_code):
                print(f"  \033[1;33m⭐ LOWEST PRICE EVER! ⭐\033[0m")
            elif previous_low is not None and previous_low < current_price:
                print(f"  Lowest seen: {previous_low:.2f}")
            if game['threshold'] is not None:
                print(f"  Your target: {game['threshold']:.2f}")
            save_price_history(game['id'], game['app_id'], current_price, info['discount_percent'], country_code)
        elif info:
            print(f"  \033[1;33m{format_price_line(info)}\033[0m")
        else:
            print(f"  \033[1;31mPrice information not available\033[0m")
        print("-" * 80)

    input("\nPress Enter to return to menu...")

def view_detailed_game_info(settings):
    """View detailed information for a selected game."""
    games = get_games_with_details()
    if not games:
        print("\n\033[1;31mNo games in watchlist!\033[0m")
        input("\nPress Enter to return to menu...")
        return

    clear_screen()
    print_header("📋 Game Information 📋")
    print("\033[1;36mSelect a game to view detailed information:\033[0m")
    game = pick_game(games, "Enter game number")
    if not game:
        return

    clear_screen()
    print_header("📋 Game Details 📋")
    print("\033[1;33mLoading game information...\033[0m\n")

    game_info = get_detailed_game_info(game['app_id'], settings['country_code'], settings['language'])
    if not game_info:
        print(f"\n\033[1;31mFailed to fetch game information.\033[0m")
        input("\nPress Enter to return to menu...")
        return

    print(f"\033[1;36m{game_info['name']}\033[0m")
    print("=" * 80)

    # Price information
    price = game_info['price']
    print(f"\n\033[1;32m💰 Price Information:\033[0m")
    print(f"  Current: \033[1;32m{format_price_line(price)}\033[0m")
    sale = get_store_items([game['app_id']], settings['country_code'], settings['language']).get(str(game['app_id']))
    if sale and sale.get('discount_end'):
        print(f"  Sale ends: {format_sale_end(sale['discount_end'])}")
    if price['final'] is not None:
        historical_low = get_historical_low(game['id'], game['app_id'], settings['country_code'])
        if historical_low is not None and historical_low < price['final'] / 100:
            print(f"  Lowest seen: {historical_low:.2f}")

    # Release date
    print(f"\n\033[1;32m📅 Release Date:\033[0m {game_info['release_date']}")

    # Developers and Publishers
    if game_info['developers']:
        print(f"\n\033[1;32m👨‍💻 Developers:\033[0m {', '.join(game_info['developers'])}")
    if game_info['publishers']:
        print(f"\n\033[1;32m🏢 Publishers:\033[0m {', '.join(game_info['publishers'])}")

    # Genres
    if game_info['genres']:
        print(f"\n\033[1;32m🎮 Genres:\033[0m {', '.join(game_info['genres'])}")

    # Categories
    if game_info['categories']:
        print(f"\n\033[1;32m📂 Categories:\033[0m")
        print(wrap_text(', '.join(game_info['categories'])))

    # Reviews
    print(f"\n\033[1;32m⭐ Reviews:\033[0m")
    print(f"  Summary: {game_info['review_score_desc']}")
    if game_info['total_reviews'] > 0:
        positive_pct = round(100 * game_info['total_positive'] / game_info['total_reviews'])
        print(f"  Total Reviews: {game_info['total_reviews']:,} ({positive_pct}% positive)")
        print(f"  Positive: {game_info['total_positive']:,} | Negative: {game_info['total_negative']:,}")

    # Metacritic
    if game_info['metacritic']:
        print(f"\n\033[1;32m🎯 Metacritic Score:\033[0m {game_info['metacritic']}/100")

    # Recommendations
    if game_info['recommendations'] > 0:
        print(f"\n\033[1;32m👍 Recommendations:\033[0m {game_info['recommendations']:,}")

    # Description
    if game_info['short_description']:
        print(f"\n\033[1;32m📝 Description:\033[0m")
        desc = html.unescape(game_info['short_description'])
        if len(desc) > 300:
            desc = desc[:300].rsplit(' ', 1)[0] + "..."
        print(wrap_text(desc))

    print("\n" + "=" * 80)
    input("\nPress Enter to return to menu...")

def save_settings(settings):
    """Write the settings dict (including any extra options) back to user_info.json."""
    extra = {k: v for k, v in settings.items()
             if k not in ("country_code", "language", "webhook_url", "bot_name", "bot_avatar")}
    save_user_info(settings['country_code'], settings['language'], settings['webhook_url'],
                   settings['bot_name'], settings['bot_avatar'], **extra)

def import_wishlist(settings):
    """Add every game on a public Steam wishlist to the watchlist."""
    clear_screen()
    print_header("Import Wishlist")
    print("\033[1;36mYour wishlist must be public: Steam > Profile > Edit Profile > "
          "Privacy Settings > Game details = Public.\033[0m\n")
    saved = settings.get('wishlist_profile')
    prompt = "Enter your Steam profile link, custom URL name or SteamID64"
    if saved:
        prompt += f" (Enter = {saved})"
    profile = get_user_input(prompt + ", or 0 to cancel: ") or saved or ""
    if not profile or profile == "0":
        return

    print("\033[1;33mLooking up your profile...\033[0m")
    steam_id = resolve_steam_id(profile)
    if not steam_id:
        print("\033[1;31mCould not find that Steam profile. Try the full link to your profile.\033[0m")
        input("\nPress Enter to return to menu...")
        return
    app_ids = get_wishlist(steam_id)
    if app_ids is None:
        print("\033[1;31mCould not reach Steam. Please try again later.\033[0m")
        input("\nPress Enter to return to menu...")
        return
    if not app_ids:
        print("\033[1;31mThe wishlist is empty or private.\033[0m")
        input("\nPress Enter to return to menu...")
        return

    existing = {str(g['app_id']) for g in get_games_with_details()}
    new_ids = [a for a in app_ids if a not in existing]
    print(f"\nFound \033[1;32m{len(app_ids)}\033[0m games on the wishlist, "
          f"\033[1;32m{len(new_ids)}\033[0m not in your list yet.")
    settings['wishlist_profile'] = profile
    save_settings(settings)
    if not new_ids:
        input("\nPress Enter to return to menu...")
        return

    print("\033[1;33mLooking up names...\033[0m")
    items = get_store_items(new_ids, settings['country_code'], settings['language'])
    to_add = [(a, items[a]['name']) for a in new_ids if a in items]
    skipped = len(new_ids) - len(to_add)
    for app_id, name in to_add:
        print(f"\033[1;32m  + {name}\033[0m")
    if skipped:
        print(f"\033[1;33m  ({skipped} game(s) skipped - not sold in your store or removed from Steam)\033[0m")
    if not to_add or get_user_input(f"\nAdd these {len(to_add)} games? (y/n): ").lower() != "y":
        return
    added = sum(1 for app_id, name in to_add
                if add_game_to_db(name, f"https://store.steampowered.com/app/{app_id}/", app_id))
    print(f"\n\033[1;32m[OK] Added {added} games.\033[0m")
    input("\nPress Enter to return to menu...")

def send_test_notification(settings):
    """Demo mode: send a clearly-marked TEST alert through the real Discord code, using a real price."""
    # Use one of your games that is really on sale right now, so the test looks like a real alert
    app_ids = [str(g['app_id']) for g in get_games_with_details()] or ["1091500"]
    prices = get_prices(app_ids, settings['country_code'], settings['language'])
    priced = [(a, prices[a]) for a in app_ids if a in prices and prices[a].get('final') is not None]
    on_sale = [(a, p) for a, p in priced if p.get('discount_percent', 0) > 0]
    if on_sale:
        app_id, info = on_sale[0]
        reason, threshold = "sale", None
    elif priced:
        # Nothing on sale: show it as a price-target alert at today's price
        app_id, info = priced[0]
        reason, threshold = "target", info['final'] / 100
    else:
        app_id, reason, threshold = "0", "sale", None
        info = {'name': 'Example Game', 'final': 1999, 'initial': 3999, 'discount_percent': 50,
                'final_formatted': '19.99', 'initial_formatted': '39.99', 'header_image': ''}
    print(f"\033[1;33mSending a test message to Discord (using {info['name']})...\033[0m")
    sent = send_discord_notification(info['name'], info, settings['webhook_url'], settings['bot_name'],
                                     settings['bot_avatar'], app_id, reason=reason, threshold=threshold,
                                     test=True)
    if sent:
        print("\033[1;32m[OK] Discord accepted the test message - check your channel.\033[0m")
    else:
        print("\033[1;31mDiscord did NOT accept the message. Check the webhook URL (details in debug.log).\033[0m")

def settings_menu(settings):
    """Change saved settings without deleting user_info.json."""
    while True:
        clear_screen()
        print_header("Settings")
        webhook = settings['webhook_url']
        masked = webhook[:webhook.find('/api/webhooks/') + 14] + "..." if '/api/webhooks/' in webhook else webhook
        print(f"\033[1;36m Country:\033[0m {settings['country_code']}    "
              f"\033[1;36mLanguage:\033[0m {settings['language']}")
        print(f"\033[1;36m Webhook:\033[0m {masked}")
        print(f"\033[1;36m Bot name:\033[0m {settings['bot_name'] or '(Discord default)'}    "
              f"\033[1;36mAvatar:\033[0m {settings['bot_avatar'] or '(Discord default)'}")
        print(f"\033[1;36m Check every:\033[0m {settings.get('check_interval_minutes', 60)} minutes    "
              f"\033[1;36mAuto-add wishlist games:\033[0m {'ON' if settings.get('wishlist_sync') else 'OFF'}\n")
        print_option("1. Change country")
        print_option("2. Change language")
        print_option("3. Change Discord webhook")
        print_option("4. Change bot name")
        print_option("5. Change bot avatar")
        print_option("6. Change how often to check")
        print_option("7. Send a test notification")
        print_option("8. Auto-add new wishlist games in background mode (ON/OFF)")
        print_option("0. Back")
        choice = get_user_input("\033[1;36mEnter a number (0-8): \033[0m")
        if choice == "0":
            return
        if choice == "1":
            value = get_user_input(COUNTRY_CODE_PROMPT).upper()
            if not validate_country_code(value):
                print("\033[1;31mInvalid country code.\033[0m")
            else:
                settings['country_code'] = value
        elif choice == "2":
            value = get_user_input(LANGUAGE_PROMPT).lower()
            if not validate_language_code(value):
                print("\033[1;31mInvalid language code.\033[0m")
            else:
                settings['language'] = value
        elif choice == "3":
            value = get_user_input(WEBHOOK_URL_PROMPT)
            if not validate_webhook_url(value):
                print("\033[1;31mInvalid webhook URL.\033[0m")
            else:
                settings['webhook_url'] = value
        elif choice == "4":
            settings['bot_name'] = get_user_input(BOT_NAME_PROMPT)
        elif choice == "5":
            settings['bot_avatar'] = get_user_input(BOT_AVATAR_PROMPT)
        elif choice == "6":
            value = get_user_input("Check every how many minutes? (10 or more, default 60): ")
            if not value.isdigit() or int(value) < 10:
                print("\033[1;31mPlease enter a whole number of 10 or more.\033[0m")
            else:
                settings['check_interval_minutes'] = int(value)
        elif choice == "7":
            send_test_notification(settings)
            input("\nPress Enter to continue...")
            continue
        elif choice == "8":
            if not settings.get('wishlist_profile'):
                print("\033[1;33mImport your wishlist once first (main menu option 8).\033[0m")
                input("Press Enter to continue...")
                continue
            settings['wishlist_sync'] = not settings.get('wishlist_sync')
            print(f"Auto-add wishlist games is now {'ON' if settings['wishlist_sync'] else 'OFF'}.")
        else:
            print("\033[1;31mInvalid option.\033[0m")
        save_settings(settings)
        input("Press Enter to continue...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Steam Game Price Alert - Discord alerts for Steam sales.")
    parser.add_argument("--daemon", "--background", action="store_true",
                        help="check all saved games on a timer, without the menu (for servers / startup)")
    parser.add_argument("--once", action="store_true",
                        help="check all saved games once and exit (for cron / Task Scheduler)")
    args = parser.parse_args()
    setup_logging()
    if args.daemon or args.once:
        sys.exit(background.run(once=args.once))
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nBye!")
    except Exception as e:
        logging.exception(f"[ERROR] An error occurred: {e}")
        print(f"\n\033[1;31m[ERROR] Something went wrong: {e}\nDetails were written to {data_path('debug.log')}\033[0m")
