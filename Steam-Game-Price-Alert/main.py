import logging
from paths import data_path
from saved_info import load_user_info, save_user_info
from utils import (
    get_all_games, extract_app_id, get_game_details, get_detailed_game_info,
    validate_country_code, validate_language_code,
    validate_webhook_url, validate_steam_link,
    clear_screen, print_header, price_from_details, format_price_line
)
from saved_games import (
    initialize_database, add_game as add_game_to_db, remove_game,
    save_price_threshold, get_games_with_details,
    save_price_history, get_historical_low
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
        print_option("0. Exit")
        choice = get_user_input("\033[1;36mEnter a number (0-7): \033[0m")
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
        elif choice == "0":
            print("\nBye!")
            return
        else:
            print("\n\033[1;31mInvalid option. Try again!\033[0m\n")
            input("Press Enter to continue...")

def add_game(settings):
    """Handles adding a new game with an option to add more or return."""
    while True:
        clear_screen()
        print_header("Add a New Game")
        steam_link = get_user_input("Enter Steam game link (or 0 to cancel): ")
        if steam_link == "0":
            break
        if not steam_link:
            print("\033[1;31mSteam link cannot be empty.\033[0m")
            input("Press Enter to try again...")
            continue
        if not (steam_link.isdigit() or validate_steam_link(steam_link)):
            print("\033[1;31mInvalid Steam link format. Please provide a valid Steam store link (e.g., https://store.steampowered.com/app/123456/).\033[0m")
            input("Press Enter to try again...")
            continue
        app_id = extract_app_id(steam_link)
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

    for game in games:
        print(f"\033[1;36m{game['name']}\033[0m")
        info = price_from_details(get_game_details(game['app_id'], country_code, settings['language']))
        if info and info['final'] is not None:
            current_price = info['final'] / 100
            previous_low = get_historical_low(game['id'], game['app_id'], country_code)
            print(f"  Price: \033[1;32m{format_price_line(info)}\033[0m")
            if info['discount_percent'] > 0 and previous_low is not None and current_price <= previous_low:
                print(f"  \033[1;33m⭐ LOWEST PRICE EVER! ⭐\033[0m")
            elif previous_low is not None and previous_low < current_price:
                print(f"  Lowest seen: {previous_low:.2f}")
            if game['threshold'] is not None:
                print(f"  Your target: {game['threshold']:.2f}")
            save_price_history(game['id'], game['app_id'], current_price, info['discount_percent'], country_code)
        elif info and info['is_free']:
            print(f"  \033[1;32mFree to play\033[0m")
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
    if price['final'] is not None:
        historical_low = get_historical_low(game['id'], game['app_id'], settings['country_code'])
        if historical_low is not None:
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
        print(f"\n\033[1;32m📂 Categories:\033[0m {', '.join(game_info['categories'])}")

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
        desc = game_info['short_description']
        if len(desc) > 200:
            desc = desc[:200] + "..."
        print(f"  {desc}")

    print("\n" + "=" * 80)
    input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    setup_logging()
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nBye!")
    except Exception as e:
        logging.exception(f"[ERROR] An error occurred: {e}")
        print(f"\n\033[1;31m[ERROR] Something went wrong: {e}\nDetails were written to {data_path('debug.log')}\033[0m")
