import time
import logging
from saved_games import get_game_link
from utils import get_all_games, clear_screen, print_header, extract_app_id, get_game_details
from stop_spam import save_sale_reminder, is_sale_notified, remove_expired_sale
from discord import send_discord_notification
from saved_games import get_price_threshold

def scan_for_sales(country_code, language, webhook_url, bot_name, bot_avatar):
    """Scans a single game for sales in an hourly loop."""
    games = get_all_games()
    if not games:
        print("\nNo saved games to scan for sales!")
        input("\nPress Enter to return to the menu...")
        return

    # Display the saved games with their IDs (indexes)
    print("\033[1;35mSelect a game to scan for sales:\033[0m")
    for index, (game_id, game_name) in enumerate(games, start=1):
        print(f"\033[1;36m  {index}. {game_name}\033[0m")

    try:
        choice = int(input("\n\033[1;36mEnter game number to scan (or 0 to cancel): \033[0m"))
        if choice == 0:
            return  # Return to menu
        elif 1 <= choice <= len(games):
            game_id, game_name = games[choice - 1]
            game_link = get_game_link(game_id)
            app_id = extract_app_id(game_link)
            if app_id:
                print(f"\n\033[1;32mInitializing scan for '{game_name}'...\033[0m")
                print("Press Ctrl+C to stop scanning and return to the menu.")
                print("-------------------------------------------------")

                try:
                    while True:  # Infinite loop for continuous scanning
                        hacker_text = "Fetching game details from Steam API..."
                        print(f"\033[1;33m{hacker_text}\033[0m")
                        game_data = get_game_details(app_id, country_code, language)
                        if game_data and 'price_overview' in game_data:
                            price_info = game_data['price_overview']
                            current_price = price_info['final'] / 100  # Convert cents to dollars
                            discount_percent = price_info['discount_percent']
                            image_url = game_data['header_image']

                            print(f"\033[1;36mGame: {game_name}\033[0m")
                            print(f"\033[1;32mCurrent Price: ${current_price:.2f} USD\033[0m")
                            print(f"\033[1;35mDiscount: {discount_percent}%\033[0m")

                            if discount_percent > 0:
                                if not is_sale_notified(app_id):
                                    # New sale detected
                                    print(f"\033[1;31mSale detected! Current price: ${current_price:.2f} ({discount_percent}% off)\033[0m")
                                    send_discord_notification(
                                        game_name=game_name,
                                        current_price=current_price,
                                        discount_percent=discount_percent,
                                        image_url=image_url,
                                        webhook_url=webhook_url,
                                        bot_name=bot_name,
                                        bot_avatar=bot_avatar,
                                        app_id=app_id
                                    )
                                    # Save sale details
                                    save_sale_reminder(app_id, game_name, current_price, discount_percent)
                                else:
                                    print("Sale already notified. Skipping notification.")
                            else:
                                # Sale is no longer active
                                if is_sale_notified(app_id):
                                    print("Sale has ended. Removing from sale reminders...")
                                    remove_expired_sale(app_id)
                        else:
                            print(f"[ERROR] Price information not available for '{game_name}'.")

                        print("-------------------------------------------------")
                        print("Sleeping for 1 hour before checking again...\n")
                        time.sleep(3600)  # Wait 1 hour before checking again

                except KeyboardInterrupt:
                    print("\nScanning stopped. Returning to menu...")
                    return  # Return to menu if user presses Ctrl+C
            else:
                print("[ERROR] Invalid game link.")
        else:
            print("\nInvalid choice. Try again.")
    except ValueError:
        print("\nPlease enter a valid number.")

def scan_multiple_games(country_code, language, webhook_url, bot_name, bot_avatar):
    """Scans multiple games for sales in an hourly loop."""
    games = get_all_games()
    if not games:
        print("\nNo saved games to scan for sales!")
        input("\nPress Enter to return to the menu...")
        return

    # Step 1: Game Selection
    clear_screen()
    print_header("🎮 Select Multiple Games 🎮")
    print("\n\033[1;35mSelect multiple games by their IDs to scan for sales:\033[0m")
    for index, (game_id, game_name) in enumerate(games, start=1):
        print(f"\033[1;36m  {index}. {game_name}\033[0m")

    # Ask the user to input game IDs separated by commas
    game_ids_input = input("\n\033[1;36mEnter game IDs (separated by commas) or 0 to cancel: \033[0m")
    game_ids = [int(id.strip()) for id in game_ids_input.split(',') if id.strip().isdigit()]

    if not game_ids or (len(game_ids) == 1 and game_ids[0] == 0):
        print("\nNo valid game IDs entered. Returning to menu...")
        input("\nPress Enter to return to the menu...")
        return

    # Check if the entered game IDs are valid
    invalid_ids = [game_id for game_id in game_ids if game_id < 1 or game_id > len(games)]
    if invalid_ids:
        print(f"\nInvalid game IDs: {', '.join(map(str, invalid_ids))}. Please try again.")
        input("\nPress Enter to return to the menu...")
        return

    # Step 2: Scanning Mode Choice
    clear_screen()
    print_header("🔍 Choose Scanning Mode 🔍")
    print("\n\033[1;36mChoose scanning mode:\033[0m")
    print("\033[0;33m 1. Use price target (notify when price drops below a threshold)\033[0m")
    print("\033[0;33m 2. Detect sales normally (notify for any discount)\033[0m")
    mode_choice = input("\n\033[1;36mEnter a number (1-2): \033[0m").strip()

    # Get the selected games
    selected_games = [(games[game_id - 1][0], games[game_id - 1][1]) for game_id in game_ids]

    # Step 3: Start Scanning
    clear_screen()
    print_header("🕵️‍♂️ Scanning in Progress 🕵️‍♂️")
    print(f"\n\033[1;32mScanning the selected games for sales every hour...\033[0m")
    print("Press Ctrl+C to stop scanning and return to the menu.")
    print("-------------------------------------------------")

    try:
        while True:  # Infinite loop for continuous scanning
            for game_id, game_name in selected_games:
                game_link = get_game_link(game_id)
                app_id = extract_app_id(game_link)
                if app_id:
                    hacker_text = "Fetching game details from Steam API..."
                    print(f"\033[1;33m{hacker_text}\033[0m")
                    game_data = get_game_details(app_id, country_code, language)
                    if game_data and 'price_overview' in game_data:
                        price_info = game_data['price_overview']
                        current_price = price_info['final'] / 100  # Convert cents to dollars
                        discount_percent = price_info['discount_percent']
                        image_url = game_data['header_image']

                        print(f"\033[1;36mGame: {game_name}\033[0m")
                        print(f"\033[1;32mCurrent Price: ${current_price:.2f} USD\033[0m")
                        print(f"\033[1;35mDiscount: {discount_percent}%\033[0m")

                        if discount_percent > 0:
                            if not is_sale_notified(app_id):
                                # New sale detected
                                print(f"\033[1;31mSale detected for '{game_name}'!\033[0m")
                                send_discord_notification(
                                    game_name=game_name,
                                    current_price=current_price,
                                    discount_percent=discount_percent,
                                    image_url=image_url,
                                    webhook_url=webhook_url,
                                    bot_name=bot_name,
                                    bot_avatar=bot_avatar,
                                    app_id=app_id
                                )
                                save_sale_reminder(app_id, game_name, current_price, discount_percent)
                            else:
                                print(f"Sale already notified for '{game_name}'. Skipping notification.")
                        else:
                            if is_sale_notified(app_id):
                                remove_expired_sale(app_id)

                print("-------------------------------------------------")
            print("Sleeping for 1 hour before checking again...\n")
            time.sleep(3600)  # Wait 1 hour before checking again

    except KeyboardInterrupt:
        print("\nScanning stopped. Returning to menu...")
        return  # Return to menu if user presses Ctrl+C
