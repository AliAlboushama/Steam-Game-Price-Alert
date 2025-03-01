import os
import sys
from saved_info import load_user_info, save_user_info
from saved_games import initialize_database, add_game as add_game_to_db, remove_game
from utils import get_all_games
from scanner import scan_for_sales, scan_multiple_games, extract_app_id, get_game_details
from pyfiglet import Figlet

def clear_screen():
    """Clears the screen for better readability."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Prints a header with a cool design using ASCII art."""
    f = Figlet(font='slant')
    print("\033[1;34m" + f.renderText(title) + "\033[0m")

def print_option(title, color_code="\033[0;33m"):
    """Prints an option with a nice design."""
    print(f"{color_code}  {title}\033[0m")

def main_menu():
    """Displays the main menu and handles user choices."""
    initialize_database()

    # Load saved user info
    user_info = load_user_info()
    if not user_info:
        # Prompt for user info if not saved
        country_code = input("Enter the country code (e.g., US, UK): ").strip().upper()
        if not country_code:
            print("\033[1;31mCountry code cannot be empty.\033[0m")
            return

        language = input("Enter the language code (e.g., en for English): ").strip().lower()
        if not language:
            print("\033[1;31mLanguage code cannot be empty.\033[0m")
            return

        webhook_url = input("Enter your Discord webhook URL: ").strip()
        if not webhook_url:
            print("\033[1;31mWebhook URL cannot be empty.\033[0m")
            return

        bot_name = input("Enter the bot name: ").strip()
        if not bot_name:
            print("\033[1;31mBot name cannot be empty.\033[0m")
            return

        bot_avatar = input("Enter the bot avatar URL (e.g., a link to a PNG image): ").strip()
        if not bot_avatar:
            print("\033[1;31mBot avatar URL cannot be empty.\033[0m")
            return

        save_user_info(country_code, language, webhook_url, bot_name, bot_avatar)
    else:
        country_code = user_info["country_code"]
        language = user_info["language"]
        webhook_url = user_info["webhook_url"]
        bot_name = user_info["bot_name"]
        bot_avatar = user_info["bot_avatar"]

    while True:
        clear_screen()
        print_header("ðŸŽ® Saved Games ðŸŽ®")

        games = get_all_games()
        if games:
            for index, (game_id, game_name) in enumerate(games, start=1):
                print(f"\033[1;32m  {index}. {game_name}\033[0m")
        else:
            print("\033[1;31m  No games added yet.\033[0m")

        print_header("Choose an Option:")
        print_option("1. Scan for sales")
        print_option("2. Add a new game")
        print_option("3. Scan multiple games")
        print_option("4. Remove a game")

        choice = input("\033[1;36mEnter a number (1-4): \033[0m").strip()

        if choice == "1":
            scan_for_sales(country_code, language, webhook_url, bot_name, bot_avatar)
        elif choice == "2":
            add_game()
        elif choice == "3":
            scan_multiple_games(country_code, language, webhook_url, bot_name, bot_avatar)
        elif choice == "4":
            remove_game_menu()
        else:
            print("\n\033[1;31mInvalid option. Try again!\033[0m\n")

def add_game():
    """Handles adding a new game with an option to add more or return."""
    while True:
        clear_screen()
        print_header("Add a New Game")
        steam_link = input("Enter Steam game link: ").strip()
        if not steam_link:
            print("\033[1;31mSteam link cannot be empty.\033[0m")
            continue

        # Extract the APP_ID from the Steam link
        app_id = extract_app_id(steam_link)
        if not app_id:
            print("\033[1;31mInvalid Steam link. Please provide a valid Steam store link.\033[0m")
            continue

        # Fetch game details from the Steam API
        game_data = get_game_details(app_id, "US", "en")  # Using default country and language
        if game_data:
            game_name = game_data.get('name', 'Unknown Game')
            # Add the game to the database using the imported function
            add_game_to_db(game_name, steam_link)

            print(f"\n\033[1;32m[OK] Game '{game_name}' added successfully!\033[0m\n")
        else:
            print("\033[1;31mFailed to fetch game details. Please try again.\033[0m")
            continue

        # Ask user what to do next
        print("\033[1;36mWhat do you want to do next?\033[0m")
        print_option("1. Add another game")
        print_option("2. Return to menu")

        next_choice = input("\033[1;36mEnter a number (1-2): \033[0m").strip()

        if next_choice == "2":
            break  # Return to main menu

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
            print(f"\033[1;33m  {index}. {game_name}\033[0m")

        try:
            choice = int(input("\n\033[1;36mEnter game number to remove (or 0 to cancel): \033[0m").strip())
            if choice == 0:
                break
            elif 1 <= choice <= len(games):
                game_id, game_name = games[choice - 1]
                remove_game(game_id)
                print(f"\n\033[1;32mâœ” '{game_name}' removed successfully!\033[0m")
                input("\nPress Enter to return to menu...")
                break
            else:
                print("\n\033[1;31mInvalid choice. Try again.\033[0m")
        except ValueError:
            print("\n\033[1;31mPlease enter a valid number.\033[0m")

# Run the script
if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
