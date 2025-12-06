import logging
import time
from saved_info import load_user_info, save_user_info
from saved_games import initialize_database, add_game as add_game_to_db, remove_game, save_price_threshold, get_price_threshold, get_game_link
from utils import (
    get_all_games, extract_app_id, get_game_details, get_detailed_game_info,
    validate_country_code, validate_language_code, 
    validate_webhook_url, validate_steam_link,
    clear_screen, print_header
)
from saved_games import (
    initialize_database, add_game as add_game_to_db, remove_game, 
    save_price_threshold, get_price_threshold, get_game_link,
    save_price_history, get_historical_low
)
from scanner import scan_for_sales, scan_multiple_games
from discord import send_discord_notification
from stop_spam import save_sale_reminder, is_sale_notified, remove_expired_sale

# Define constants
SLEEP_TIME = 3600  # 1 hour
COUNTRY_CODE_PROMPT = "Enter the country code (e.g., US, UK): "
LANGUAGE_PROMPT = "Enter the language code (e.g., en for English): "
WEBHOOK_URL_PROMPT = "Enter your Discord webhook URL: "
BOT_NAME_PROMPT = "Enter the bot name: "
BOT_AVATAR_PROMPT = "Enter the bot avatar URL (e.g., a link to a PNG image): "

# Configure logging
logging.basicConfig(
    filename='debug.log', 
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
        print("\033[1;31mInvalid country code. Please enter a 2-letter code (e.g., US, UK, DE).\033[0m")
    
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

def scan_for_sales_with_threshold(country_code, language, webhook_url, bot_name, bot_avatar):
    """Scans for games that meet or fall below the user's price threshold or detect sales normally."""
    games = get_all_games()
    if not games:
        print("\nNo saved games to scan for sales!")
        input("\nPress Enter to return to the menu...")
        return

    # Step 1: Game Selection
    clear_screen()
    print_header("🎮 Select a Game 🎮")
    print("\n\033[1;35mSelect a game to scan for sales:\033[0m")
    for index, (game_id, game_name) in enumerate(games, start=1):
        print(f"\033[1;36m  {index}. {game_name}\033[0m")

    try:
        choice = int(get_user_input("\n\033[1;36mEnter game number to scan (or 0 to cancel): \033[0m"))
        if choice == 0:
            return  # Return to menu
        elif 1 <= choice <= len(games):
            game_id, game_name = games[choice - 1]
            game_link = get_game_link(game_id)
            app_id = extract_app_id(game_link)
            if app_id:
                # Step 2: Scanning Mode Choice
                clear_screen()
                print_header("🔍 Choose Scanning Mode 🔍")
                print("\n\033[1;36mChoose scanning mode:\033[0m")
                print("\033[0;33m 1. Use price target (notify when price drops below a threshold)\033[0m")
                print("\033[0;33m 2. Detect sales normally (notify for any discount)\033[0m")
                mode_choice = get_user_input("\n\033[1;36mEnter a number (1-2): \033[0m")

                # Step 3: Start Scanning
                clear_screen()
                print_header("🕵️‍♂️ Scanning in Progress 🕵️‍♂️")
                print(f"\n\033[1;32mInitializing scan for '{game_name}'...\033[0m")
                print("Press Ctrl+C to stop scanning and return to the menu.")
                print("-------------------------------------------------")

                try:
                    while True:  # Infinite loop for continuous scanning
                        hacker_text = "Fetching game details from Steam API..."
                        print(f"\n\033[1;33m{hacker_text}\033[0m")
                        game_data = get_game_details(app_id, country_code, language)
                        if game_data and 'price_overview' in game_data:
                            price_info = game_data['price_overview']
                            current_price = price_info['final'] / 100  # Convert cents to dollars
                            discount_percent = price_info['discount_percent']
                            image_url = game_data['header_image']
                            
                            # Save price history
                            save_price_history(game_id, app_id, current_price, discount_percent)
                            
                            # Check for historical low
                            historical_low = get_historical_low(game_id, app_id)
                            is_historical_low = historical_low is not None and current_price <= historical_low

                            print(f"\n\033[1;36mGame: {game_name}\033[0m")
                            print(f"\033[1;32mCurrent Price: ${current_price:.2f} USD\033[0m")
                            print(f"\033[1;35mDiscount: {discount_percent}%\033[0m")
                            if is_historical_low:
                                print(f"\033[1;33m⭐ LOWEST PRICE EVER! ⭐\033[0m")

                            if mode_choice == "1":
                                # Use price target
                                threshold = get_price_threshold(game_id)
                                if threshold is not None and current_price <= threshold:
                                    if not is_sale_notified(app_id):
                                        print(f"\n\033[1;31mPrice target met! Current price: ${current_price:.2f} (Threshold: ${threshold:.2f})\033[0m")
                                        send_discord_notification(
                                            game_name=game_name,
                                            current_price=current_price,
                                            discount_percent=discount_percent,
                                            image_url=image_url,
                                            webhook_url=webhook_url,
                                            bot_name=bot_name,
                                            bot_avatar=bot_avatar,
                                            app_id=app_id,
                                            is_historical_low=is_historical_low,
                                            historical_low=historical_low
                                        )
                                        save_sale_reminder(app_id, game_name, current_price, discount_percent)
                                    else:
                                        print("\nSale already notified. Skipping notification.")
                                else:
                                    print("\nPrice target not met. Skipping notification.")
                                    if is_sale_notified(app_id):
                                        remove_expired_sale(app_id)
                            elif mode_choice == "2":
                                # Detect sales normally
                                if discount_percent > 0:
                                    if not is_sale_notified(app_id):
                                        print(f"\n\033[1;31mSale detected! Current price: ${current_price:.2f} ({discount_percent}% off)\033[0m")
                                        send_discord_notification(
                                            game_name=game_name,
                                            current_price=current_price,
                                            discount_percent=discount_percent,
                                            image_url=image_url,
                                            webhook_url=webhook_url,
                                            bot_name=bot_name,
                                            bot_avatar=bot_avatar,
                                            app_id=app_id,
                                            is_historical_low=is_historical_low,
                                            historical_low=historical_low
                                        )
                                        save_sale_reminder(app_id, game_name, current_price, discount_percent)
                                    else:
                                        print("\nSale already notified. Skipping notification.")
                                else:
                                    print("\nNo sale detected. Skipping notification.")
                                    if is_sale_notified(app_id):
                                        remove_expired_sale(app_id)
                            else:
                                print("\n\033[1;31mInvalid mode choice. Try again.\033[0m")
                                break

                        print("\n-------------------------------------------------")
                        print("Sleeping for 1 hour before checking again...\n")
                        time.sleep(SLEEP_TIME)  # Wait 1 hour before checking again

                except KeyboardInterrupt:
                    print("\nScanning stopped. Returning to menu...")
                    return  # Return to menu if user presses Ctrl+C
            else:
                print("\n[ERROR] Invalid game link.")
        else:
            print("\nInvalid choice. Try again.")
    except ValueError:
        print("\nPlease enter a valid number.")

def main_menu():
    """Displays the main menu and handles user choices."""
    initialize_database()
    user_info = load_user_info()
    if not user_info:
        country_code, language, webhook_url, bot_name, bot_avatar = get_user_info()
        save_user_info(country_code, language, webhook_url, bot_name, bot_avatar)
    else:
        country_code = user_info["country_code"]
        language = user_info["language"]
        webhook_url = user_info["webhook_url"]
        bot_name = user_info["bot_name"]
        bot_avatar = user_info["bot_avatar"]

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
        choice = get_user_input("\033[1;36mEnter a number (1-7): \033[0m")
        if choice == "1":
            scan_for_sales_with_threshold(country_code, language, webhook_url, bot_name, bot_avatar)
        elif choice == "2":
            add_game()
        elif choice == "3":
            scan_multiple_games(country_code, language, webhook_url, bot_name, bot_avatar)
        elif choice == "4":
            remove_game_menu()
        elif choice == "5":
            set_price_threshold()
        elif choice == "6":
            view_current_prices(country_code, language)
        elif choice == "7":
            view_detailed_game_info(country_code, language)
        else:
            print("\n\033[1;31mInvalid option. Try again!\033[0m\n")

def add_game():
    """Handles adding a new game with an option to add more or return."""
    while True:
        clear_screen()
        print_header("Add a New Game")
        steam_link = get_user_input("Enter Steam game link: ")
        if not steam_link:
            print("\033[1;31mSteam link cannot be empty.\033[0m")
            continue
        if not validate_steam_link(steam_link):
            print("\033[1;31mInvalid Steam link format. Please provide a valid Steam store link (e.g., https://store.steampowered.com/app/123456/).\033[0m")
            continue
        app_id = extract_app_id(steam_link)
        if not app_id:
            print("\033[1;31mCould not extract app ID from Steam link. Please provide a valid Steam store link.\033[0m")
            continue
        game_data = get_game_details(app_id, "US", "en")
        if game_data:
            game_name = game_data.get('name', 'Unknown Game')
            add_game_to_db(game_name, steam_link)
            print(f"\n\033[1;32m[OK] Game '{game_name}' added successfully!\033[0m\n")
        else:
            print("\033[1;31mFailed to fetch game details. Please try again.\033[0m")
            continue
        print("\033[1;36mWhat do you want to do next?\033[0m")
        print_option("1. Add another game")
        print_option("2. Return to menu")
        next_choice = get_user_input("\033[1;36mEnter a number (1-2): \033[0m")
        if next_choice == "2":
            break

def remove_game_menu():
    """Removes a game from the saved games list."""
    games = get_all_games()
    if not games:
        print("\n\033[1;31mNo games to remove!\033[0m")
        input("\nPress Enter to return to menu...")
        return
    while True:
        clear_screen()
        print_header("Remove a Game")
        print("\033[1;36mSelect a game to remove:\033[0m")
        for index, (game_id, game_name) in enumerate(games, start=1):
            print(f"\033[1;33m {index}. {game_name}\033[0m")
        try:
            choice = int(get_user_input("\n\033[1;36mEnter game number to remove (or 0 to cancel): \033[0m"))
            if choice == 0:
                break
            elif 1 <= choice <= len(games):
                game_id, game_name = games[choice - 1]
                remove_game(game_id)
                print(f"\n\033[1;32m✓ '{game_name}' removed successfully!\033[0m")
                input("\nPress Enter to return to menu...")
                break
            else:
                print("\n\033[1;31mInvalid choice. Try again.\033[0m")
        except ValueError:
            print("\n\033[1;31mPlease enter a valid number.\033[0m")

def set_price_threshold():
    """Handles setting price thresholds for games."""
    while True:
        clear_screen()
        print_header("Set Price Threshold")
        games = get_all_games()
        if not games:
            print("\n\033[1;31mNo games to set thresholds for!\033[0m")
            input("\nPress Enter to return to menu...")
            return

        print("\033[1;36mSelect a game to set a price threshold:\033[0m")
        for index, (game_id, game_name) in enumerate(games, start=1):
            print(f"\033[1;33m {index}. {game_name}\033[0m")

        try:
            choice = int(get_user_input("\n\033[1;36mEnter game number to set threshold (or 0 to cancel): \033[0m"))
            if choice == 0:
                break
            elif 1 <= choice <= len(games):
                game_id, game_name = games[choice - 1]
                threshold = float(get_user_input(f"\n\033[1;34mEnter the price threshold for '{game_name}': \033[0m"))
                if threshold <= 0:
                    print("\n\033[1;31mPrice threshold must be greater than zero.\033[0m")
                    continue
                save_price_threshold(game_id, threshold)
                print(f"\n\033[1;32mPrice threshold for '{game_name}' set to {threshold} successfully!\033[0m")
                input("\nPress Enter to return to menu...")
                break
            else:
                print("\n\033[1;31mInvalid choice. Try again.\033[0m")
        except ValueError:
            print("\n\033[1;31mPlease enter a valid number.\033[0m")

def view_current_prices(country_code, language):
    """View current prices for all games in the watchlist."""
    clear_screen()
    print_header("💰 Current Prices 💰")
    games = get_all_games()
    if not games:
        print("\n\033[1;31mNo games in watchlist!\033[0m")
        input("\nPress Enter to return to menu...")
        return
    
    print("\n\033[1;33mFetching current prices...\033[0m\n")
    print("-" * 80)
    
    for game_id, game_name in games:
        game_link = get_game_link(game_id)
        app_id = extract_app_id(game_link)
        if app_id:
            game_data = get_game_details(app_id, country_code, language)
            if game_data and 'price_overview' in game_data:
                price_info = game_data['price_overview']
                current_price = price_info['final'] / 100
                discount_percent = price_info['discount_percent']
                original_price = price_info.get('initial', price_info['final']) / 100
                
                # Get historical low
                historical_low = get_historical_low(game_id, app_id)
                is_historical_low = historical_low is not None and current_price <= historical_low
                
                print(f"\033[1;36m{game_name}\033[0m")
                if discount_percent > 0:
                    print(f"  Price: \033[1;32m${current_price:.2f}\033[0m (was ${original_price:.2f}) - \033[1;31m{discount_percent}% OFF\033[0m")
                else:
                    print(f"  Price: \033[1;32m${current_price:.2f}\033[0m")
                
                if is_historical_low:
                    print(f"  \033[1;33m⭐ LOWEST PRICE EVER! ⭐\033[0m")
                elif historical_low:
                    print(f"  Historical Low: ${historical_low:.2f}")
                
                # Save to price history
                save_price_history(game_id, app_id, current_price, discount_percent)
            else:
                print(f"\033[1;36m{game_name}\033[0m")
                print(f"  \033[1;31mPrice information not available\033[0m")
        print("-" * 80)
    
    input("\nPress Enter to return to menu...")

def view_detailed_game_info(country_code, language):
    """View detailed information for a selected game."""
    games = get_all_games()
    if not games:
        print("\n\033[1;31mNo games in watchlist!\033[0m")
        input("\nPress Enter to return to menu...")
        return
    
    while True:
        clear_screen()
        print_header("📋 Game Information 📋")
        print("\033[1;36mSelect a game to view detailed information:\033[0m")
        for index, (game_id, game_name) in enumerate(games, start=1):
            print(f"\033[1;33m {index}. {game_name}\033[0m")
        
        try:
            choice = int(get_user_input("\n\033[1;36mEnter game number (or 0 to cancel): \033[0m"))
            if choice == 0:
                break
            elif 1 <= choice <= len(games):
                game_id, game_name = games[choice - 1]
                game_link = get_game_link(game_id)
                app_id = extract_app_id(game_link)
                
                if app_id:
                    clear_screen()
                    print_header("📋 Game Details 📋")
                    print("\033[1;33mLoading game information...\033[0m\n")
                    
                    game_info = get_detailed_game_info(app_id, country_code, language)
                    if game_info:
                        print(f"\033[1;36m{game_info['name']}\033[0m")
                        print("=" * 80)
                        
                        # Price information
                        if game_info['price_overview']:
                            price_info = game_info['price_overview']
                            current_price = price_info['final'] / 100
                            discount_percent = price_info['discount_percent']
                            original_price = price_info.get('initial', price_info['final']) / 100
                            
                            print(f"\n\033[1;32m💰 Price Information:\033[0m")
                            if discount_percent > 0:
                                print(f"  Current: \033[1;32m${current_price:.2f}\033[0m (was ${original_price:.2f}) - \033[1;31m{discount_percent}% OFF\033[0m")
                            else:
                                print(f"  Current: \033[1;32m${current_price:.2f}\033[0m")
                            
                            # Historical low
                            historical_low = get_historical_low(game_id, app_id)
                            if historical_low:
                                is_lowest = current_price <= historical_low
                                if is_lowest:
                                    print(f"  \033[1;33m⭐ LOWEST PRICE EVER! ⭐\033[0m")
                                else:
                                    print(f"  Historical Low: ${historical_low:.2f}")
                        
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
                        print(f"  Summary: {game_info['review_summary']}")
                        if game_info['total_reviews'] > 0:
                            print(f"  Score: {game_info['review_score']}/100 ({game_info['review_score_desc']})")
                            print(f"  Total Reviews: {game_info['total_reviews']:,}")
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
                            # Wrap description text
                            desc = game_info['short_description']
                            if len(desc) > 200:
                                desc = desc[:200] + "..."
                            print(f"  {desc}")
                        
                        print("\n" + "=" * 80)
                    else:
                        print(f"\n\033[1;31mFailed to fetch game information.\033[0m")
                    
                    input("\nPress Enter to return to menu...")
                    break
                else:
                    print("\n\033[1;31mInvalid game link.\033[0m")
            else:
                print("\n\033[1;31mInvalid choice. Try again.\033[0m")
        except ValueError:
            print("\n\033[1;31mPlease enter a valid number.\033[0m")

if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        logging.error(f"[ERROR] An error occurred: {e}")