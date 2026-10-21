import time
import logging
from saved_games import get_games_with_details, save_price_history, get_historical_low
from utils import clear_screen, print_header, get_price_info, format_price_line
from stop_spam import save_sale_reminder, should_notify, is_sale_notified, remove_expired_sale
from notifier import send_discord_notification

SLEEP_TIME = 3600  # 1 hour

MODE_TARGET = "1"  # notify when price drops to the user's threshold
MODE_SALE = "2"    # notify for any discount

def choose_mode():
    """Ask which scanning mode to use. Returns MODE_TARGET, MODE_SALE or None."""
    clear_screen()
    print_header("🔍 Choose Scanning Mode 🔍")
    print("\n\033[1;36mChoose scanning mode:\033[0m")
    print("\033[0;33m 1. Use price target (notify when price drops below a threshold)\033[0m")
    print("\033[0;33m 2. Detect sales normally (notify for any discount)\033[0m")
    while True:
        mode_choice = input("\n\033[1;36mEnter a number (1-2, or 0 to cancel): \033[0m").strip()
        if mode_choice in (MODE_TARGET, MODE_SALE):
            return mode_choice
        if mode_choice == "0":
            return None
        print("\033[1;31mPlease enter 1 or 2.\033[0m")

def check_game(game, price_info, settings, mode):
    """
    Check one game's price, print it, record it, and send a Discord alert if it qualifies.
    Returns True if an alert was sent.
    """
    game_id, game_name, app_id = game['id'], game['name'], game['app_id']
    country_code = settings['country_code']

    print(f"\n\033[1;36mGame: {game_name}\033[0m")
    if not price_info or price_info.get('final') is None:
        if price_info and price_info.get('is_free'):
            print("\033[1;32mFree to play - nothing to watch.\033[0m")
        else:
            print(f"\033[1;31m[ERROR] Price information not available for '{game_name}'.\033[0m")
        return False

    current_price = price_info['final'] / 100
    discount_percent = price_info['discount_percent']

    # Compare against the lowest price seen BEFORE this check, otherwise the current
    # price is always "the lowest ever" (it was just saved)
    previous_low = get_historical_low(game_id, app_id, country_code)
    is_historical_low = (discount_percent > 0 and previous_low is not None
                         and current_price <= previous_low)
    save_price_history(game_id, app_id, current_price, discount_percent, country_code)

    print(f"\033[1;32mCurrent Price: {format_price_line(price_info)}\033[0m")
    if is_historical_low:
        print(f"\033[1;33m⭐ LOWEST PRICE EVER! ⭐\033[0m")

    threshold = game.get('threshold')
    if mode == MODE_TARGET:
        if threshold is None:
            print("\033[1;33mNo price target set for this game (use 'Set price threshold').\033[0m")
            return False
        qualifies, reason = current_price <= threshold, "target"
    else:
        qualifies, reason = discount_percent > 0, "sale"

    if not qualifies:
        print("Price target not met." if mode == MODE_TARGET else "No sale detected.")
        if is_sale_notified(app_id):
            print("Deal has ended. Removing from sale reminders...")
            remove_expired_sale(app_id)
        return False

    if not should_notify(app_id, current_price):
        print("Deal already notified. Skipping notification.")
        return False

    if reason == "target":
        print(f"\033[1;31mPrice target met! {price_info['final_formatted']} (target {threshold:.2f})\033[0m")
    else:
        print(f"\033[1;31mSale detected! {price_info['final_formatted']} ({discount_percent}% off)\033[0m")

    sent = send_discord_notification(
        game_name=game_name,
        price_info=price_info,
        webhook_url=settings['webhook_url'],
        bot_name=settings['bot_name'],
        bot_avatar=settings['bot_avatar'],
        app_id=app_id,
        reason=reason,
        threshold=threshold,
        is_historical_low=is_historical_low,
        historical_low=previous_low,
    )
    if sent:
        save_sale_reminder(app_id, game_name, current_price, discount_percent)
        print("\033[1;32mDiscord notification sent.\033[0m")
    else:
        # Not marked as notified, so the next check tries again
        print("\033[1;31mDiscord notification FAILED - will retry next check (see debug.log).\033[0m")
    return sent

def check_games(games, settings, mode):
    """Check every game once."""
    for game in games:
        print("\033[1;33mFetching game details from Steam API...\033[0m")
        price_info = get_price_info(game['app_id'], settings['country_code'], settings['language'])
        try:
            check_game(game, price_info, settings, mode)
        except Exception as e:
            logging.exception(f"Error checking {game['name']}: {e}")
            print(f"\033[1;31m[ERROR] Could not check '{game['name']}': {e}\033[0m")
        print("-------------------------------------------------")

def scan_loop(games, settings, mode):
    """Check the games every hour until the user presses Ctrl+C."""
    clear_screen()
    print_header("🕵️‍♂️ Scanning in Progress 🕵️‍♂️")
    names = ", ".join(f"'{g['name']}'" for g in games)
    print(f"\n\033[1;32mScanning {names} for sales every hour...\033[0m")
    print("Press Ctrl+C to stop scanning and return to the menu.")
    print("-------------------------------------------------")
    try:
        while True:
            check_games(games, settings, mode)
            print(f"Sleeping for {SLEEP_TIME // 60} minutes before checking again...\n")
            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        print("\nScanning stopped. Returning to menu...")

def _list_games(games, color="\033[1;36m"):
    for index, game in enumerate(games, start=1):
        print(f"{color}  {index}. {game['name']}\033[0m")

def scan_for_sales(settings):
    """Scan a single game for sales in an hourly loop."""
    games = get_games_with_details()
    if not games:
        print("\nNo saved games to scan for sales!")
        input("\nPress Enter to return to the menu...")
        return

    clear_screen()
    print_header("🎮 Select a Game 🎮")
    print("\n\033[1;35mSelect a game to scan for sales:\033[0m")
    _list_games(games)
    try:
        choice = int(input("\n\033[1;36mEnter game number to scan (or 0 to cancel): \033[0m"))
    except ValueError:
        print("\nPlease enter a valid number.")
        input("\nPress Enter to return to the menu...")
        return
    if choice == 0:
        return
    if not 1 <= choice <= len(games):
        print("\nInvalid choice. Try again.")
        input("\nPress Enter to return to the menu...")
        return

    mode = choose_mode()
    if mode:
        scan_loop([games[choice - 1]], settings, mode)

def scan_multiple_games(settings):
    """Scans multiple games for sales in an hourly loop."""
    games = get_games_with_details()
    if not games:
        print("\nNo saved games to scan for sales!")
        input("\nPress Enter to return to the menu...")
        return

    # Step 1: Game Selection
    clear_screen()
    print_header("🎮 Select Multiple Games 🎮")
    print("\n\033[1;35mSelect multiple games by their numbers to scan for sales:\033[0m")
    _list_games(games)

    # Ask the user to input game numbers separated by commas
    numbers_input = input("\n\033[1;36mEnter game numbers (separated by commas), 'all', or 0 to cancel: \033[0m")
    if numbers_input.strip().lower() == "all":
        numbers = list(range(1, len(games) + 1))
    else:
        numbers = [int(n.strip()) for n in numbers_input.split(',') if n.strip().isdigit()]

    if not numbers or numbers == [0]:
        print("\nNo valid game numbers entered. Returning to menu...")
        input("\nPress Enter to return to the menu...")
        return

    # Check if the entered game numbers are valid
    invalid = [n for n in numbers if n < 1 or n > len(games)]
    if invalid:
        print(f"\nInvalid game numbers: {', '.join(map(str, invalid))}. Please try again.")
        input("\nPress Enter to return to the menu...")
        return

    # Step 2: Scanning Mode Choice
    mode = choose_mode()
    if not mode:
        return

    # Step 3: Start Scanning (duplicates removed, order kept)
    selected = [games[n - 1] for n in dict.fromkeys(numbers)]
    scan_loop(selected, settings, mode)
