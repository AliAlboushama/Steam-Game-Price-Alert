import time
import requests
import json
import os
from saved_info import load_user_info, save_user_info
from saved_games import initialize_database, add_game, get_all_games, get_game_link
from discord import send_discord_notification

# List to store saved games dynamically
saved_games = []

def clear_screen():
    """Clears the screen for better readability."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Prints a header with a cool design."""
    print("\033[1;34m╔════════════════════════════════════════╗\033[0m")
    print(f"\033[1;36m║  {title.center(34)}  ║\033[0m")
    print("\033[1;34m╚════════════════════════════════════════╝\033[0m")

def print_option(title, color_code="\033[0;33m"):
    """Prints an option with a nice design."""
    print(f"{color_code}  {title}\033[0m")

def extract_app_id(game_link):
    """Extract the APP_ID from the Steam game link."""
    try:
        app_id = game_link.split('/app/')[1].split('/')[0]
        return app_id
    except Exception as e:
        print(f"[ERROR] Invalid game link. Please provide a valid Steam store link.")
        return None

def get_game_details(app_id, country_code, language):
    """Fetch game details from the Steam API."""
    steam_api_url = f'https://store.steampowered.com/api/appdetails?appids={app_id}&cc={country_code}&l={language}'
    try:
        response = requests.get(steam_api_url)
        response.raise_for_status()
        data = response.json()
        return data[app_id]['data']
    except Exception as e:
        print(f"[ERROR] Error fetching game details: {e}")
        return None

def load_saved_sales():
    """Load saved sale details from saved_sale.json."""
    try:
        with open("saved_sale.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  # Return an empty dictionary if the file doesn't exist

def save_sale_details(app_id, game_name, current_price, discount_percent):
    """Save sale details to saved_sale.json."""
    saved_sales = load_saved_sales()
    saved_sales[app_id] = {
        "game_name": game_name,
        "current_price": current_price,
        "discount_percent": discount_percent
    }
    with open("saved_sale.json", "w") as file:
        json.dump(saved_sales, file, indent=4)

def remove_expired_sale(app_id):
    """Remove expired sale details from saved_sale.json."""
    saved_sales = load_saved_sales()
    if app_id in saved_sales:
        del saved_sales[app_id]
        with open("saved_sale.json", "w") as file:
            json.dump(saved_sales, file, indent=4)

def remove_game_from_database(game_id):
    """Remove a game from the database."""
    games = get_all_games()
    if game_id in games:
        # Remove the game from the database
        games = [(id, name) for id, name in games if id != game_id]
        save_user_info(games)
        print(f"Game with ID {game_id} has been removed from the database.")
    else:
        print(f"[ERROR] Game ID {game_id} not found.")

def main_menu():
    """Displays the main menu and handles user choices."""
    initialize_database()

    # Load saved user info
    user_info = load_user_info()
    if not user_info:
        # Prompt for user info if not saved
        country_code = input("Enter the country code (e.g., US, UK): ").upper()
        language = input("Enter the language code (e.g., en for English): ").lower()
        webhook_url = input("Enter your Discord webhook URL: ")
        bot_name = input("Enter the bot name: ")
        bot_avatar = input("Enter the bot avatar URL (e.g., a link to a PNG image): ")
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
                print(f"\033[1;32m  {index}. {game_name}\033[0m")
        else:
            print("\033[1;31m  No games added yet.\033[0m")

        print_header("Choose an Option:")
        print_option("1️⃣  Scan for sales")
        print_option("2️⃣  Add a new game")
        print_option("3️⃣  Scan multiple games")
        print_option("4️⃣  Remove a game")

        choice = input("\033[1;36mEnter a number (1-4): \033[0m")

        if choice == "1":
            scan_for_sales(country_code, language, webhook_url, bot_name, bot_avatar)
        elif choice == "2":
            add_game()
        elif choice == "3":
            scan_multiple_games(country_code, language, webhook_url, bot_name, bot_avatar)
        elif choice == "4":
            remove_game()
        else:
            print("\n\033[1;31mInvalid option. Try again!\033[0m\n")

def add_game():
    """Handles adding a new game with an option to add more or return."""
    while True:
        clear_screen()
        print_header("Add a New Game")
        steam_link = input("Enter Steam game link: ")
        game_name = input("Enter game name: ")

        # Add the game to the database
        add_game(game_name, steam_link)

        print(f"\n\033[1;32m✔ Game '{game_name}' added successfully!\033[0m\n")

        # Ask user what to do next
        print("\033[1;36mWhat do you want to do next?\033[0m")
        print_option("1️⃣  Add another game")
        print_option("2️⃣  Return to menu")

        next_choice = input("\033[1;36mEnter a number (1-2): \033[0m")

        if next_choice == "2":
            break  # Return to main menu

def remove_game():
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
            print(f"\033[1;33m  {index}. {game_name}\033[0m")

        try:
            choice = int(input("\n\033[1;36mEnter game number to remove (or 0 to cancel): \033[0m"))
            if choice == 0:
                break
            elif 1 <= choice <= len(games):
                game_id, game_name = games[choice - 1]
                remove_game_from_database(game_id)
                print(f"\n\033[1;32m✔ '{game_name}' removed successfully!\033[0m")
                input("\nPress Enter to return to menu...")
                break
            else:
                print("\n\033[1;31mInvalid choice. Try again.\033[0m")
        except ValueError:
            print("\n\033[1;31mPlease enter a valid number.\033[0m")

def scan_for_sales(country_code, language, webhook_url, bot_name, bot_avatar):
    """Scans a single game for sales in an hourly loop."""
    games = get_all_games()
    if not games:
        print("\nNo saved games to scan for sales!")
        input("\nPress Enter to return to the menu...")
        return

    # Display the saved games with their IDs (indexes)
    print("\nSelect a game to scan for sales:")
    for index, (game_id, game_name) in enumerate(games, start=1):
        print(f"  {index}. {game_name}")

    try:
        choice = int(input("\nEnter game number to scan (or 0 to cancel): "))
        if choice == 0:
            return  # Return to menu
        elif 1 <= choice <= len(games):
            game_id, game_name = games[choice - 1]
            game_link = get_game_link(game_id)
            app_id = extract_app_id(game_link)
            if app_id:
                print(f"\nScanning '{game_name}' for sales every hour...")
                print("Press Ctrl+C to stop scanning and return to the menu.")
                print("-------------------------------------------------")

                try:
                    while True:  # Infinite loop for continuous scanning
                        print("Fetching game details from Steam API...")
                        game_data = get_game_details(app_id, country_code, language)
                        if game_data and 'price_overview' in game_data:
                            price_info = game_data['price_overview']
                            current_price = price_info['final'] / 100  # Convert cents to dollars
                            discount_percent = price_info['discount_percent']
                            image_url = game_data['header_image']

                            print(f"Game: {game_name}")
                            print(f"Current Price: ${current_price:.2f} USD")
                            print(f"Discount: {discount_percent}%")

                            saved_sales = load_saved_sales()

                            if discount_percent > 0:
                                if app_id not in saved_sales:
                                    # New sale detected
                                    last_known_price = saved_sales.get(app_id, {}).get("current_price", "N/A")
                                    print(f"Sale detected! Last known price: {last_known_price}")
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
                                    save_sale_details(app_id, game_name, current_price, discount_percent)
                                else:
                                    print("Sale already notified. Skipping notification.")
                            else:
                                # Sale is no longer active
                                if app_id in saved_sales:
                                    print("Sale has ended. Removing from saved_sale.json...")
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

    # Display the saved games with their IDs (indexes)
    print("\nSelect multiple games by their IDs to scan for sales:")
    for index, (game_id, game_name) in enumerate(games, start=1):
        print(f"  {index}. {game_name}")
    
    # Ask the user to input game IDs separated by commas
    game_ids_input = input("\nEnter game IDs (separated by commas) or 0 to cancel: ")
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

    # Get the selected games
    selected_games = [(games[game_id - 1][0], games[game_id - 1][1]) for game_id in game_ids]

    print(f"\nScanning the selected games for sales every hour...")
    print("Press Ctrl+C to stop scanning and return to the menu.")
    print("-------------------------------------------------")

    try:
        while True:  # Infinite loop for continuous scanning
            for game_id, game_name in selected_games:
                game_link = get_game_link(game_id)
                app_id = extract_app_id(game_link)
                if app_id:
                    print("Fetching game details from Steam API...")
                    game_data = get_game_details(app_id, country_code, language)
                    if game_data and 'price_overview' in game_data:
                        price_info = game_data['price_overview']
                        current_price = price_info['final'] / 100  # Convert cents to dollars
                        discount_percent = price_info['discount_percent']
                        image_url = game_data['header_image']

                        print(f"Game: {game_name}")
                        print(f"Current Price: ${current_price:.2f} USD")
                        print(f"Discount: {discount_percent}%")

                        saved_sales = load_saved_sales()

                        if discount_percent > 0:
                            if app_id not in saved_sales:
                                # New sale detected
                                last_known_price = saved_sales.get(app_id, {}).get("current_price", "N/A")
                                print(f"Sale detected! Last known price: {last_known_price}")
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
                                save_sale_details(app_id, game_name, current_price, discount_percent)
                            else:
                                print("Sale already notified. Skipping notification.")
                        else:
                            # Sale is no longer active
                            if app_id in saved_sales:
                                print("Sale has ended. Removing from saved_sale.json...")
                                remove_expired_sale(app_id)
                    else:
                        print(f"[ERROR] Price information not available for '{game_name}'.")
                else:
                    print(f"[ERROR] Invalid game link for '{game_name}'.")

                print("-------------------------------------------------")

            print("Sleeping for 1 hour before checking again...\n")
            time.sleep(3600)  # Wait 1 hour before checking again

    except KeyboardInterrupt:
        print("\nScanning stopped. Returning to menu...")
        return  # Return to menu if user presses Ctrl+C

# Run the script
if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")