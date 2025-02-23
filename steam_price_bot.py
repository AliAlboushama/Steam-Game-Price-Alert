import time
import requests
from saved_info import load_user_info, save_user_info
from saved_games import initialize_database, add_game, get_all_games, get_game_link
from discord import send_discord_notification

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
        print("Fetching game details from Steam API...")
        response = requests.get(steam_api_url)
        response.raise_for_status()
        data = response.json()
        return data[app_id]['data']
    except Exception as e:
        print(f"[ERROR] Error fetching game details: {e}")
        return None

def main():
    """Main loop to check for price changes every hour."""
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
        # Use saved user info
        country_code = user_info["country_code"]
        language = user_info["language"]
        webhook_url = user_info["webhook_url"]
        bot_name = user_info["bot_name"]
        bot_avatar = user_info["bot_avatar"]

    while True:
        # List saved games
        games = get_all_games()
        if games:
            print("Saved games:")
            for game_id, game_name in games:
                print(f"{game_id}. {game_name}")
            
            # Ask the user if they want to scan or add more games
            choice = input("Do you want to (1) run the scan or (2) add more games to the database? Enter 1 or 2: ")
            
            if choice == "1":
                # User wants to run the scan
                game_choice = input("Enter the number of the game to scan: ")
                game_id = int(game_choice)
                game_link = get_game_link(game_id)
                app_id = extract_app_id(game_link)
                break  # Exit the loop and proceed to scanning
            elif choice == "2":
                # User wants to add more games
                game_link = input("Enter the Steam game link (e.g., https://store.steampowered.com/app/534380/): ")
                game_name = input("Enter the game name: ")
                add_game(game_name, game_link)
                print(f"Game '{game_name}' added successfully.")
            else:
                print("Invalid choice. Please enter 1 or 2.")
        else:
            # No games in the database, prompt to add a new game
            game_link = input("Enter the Steam game link (e.g., https://store.steampowered.com/app/534380/): ")
            game_name = input("Enter the game name: ")
            add_game(game_name, game_link)
            print(f"Game '{game_name}' added successfully.")

    last_known_price = None

    while True:
        game_data = get_game_details(app_id, country_code, language)
        if game_data and 'price_overview' in game_data:
            price_info = game_data['price_overview']
            current_price = price_info['final'] / 100  # Convert cents to dollars
            discount_percent = price_info['discount_percent']
            game_name = game_data['name']
            image_url = game_data['header_image']

            print(f"Game: {game_name}")
            print(f"Current Price: ${current_price:.2f} USD")
            print(f"Discount: {discount_percent}%")

            if discount_percent > 0:
                print(f"Sale detected! Last known price: {last_known_price}")
                if current_price != last_known_price:
                    # Use the Discord module to send the notification
                    send_discord_notification(game_name, current_price, discount_percent, image_url, webhook_url, bot_name, bot_avatar)
                    last_known_price = current_price
                else:
                    print("Sale detected, but price has not changed. No notification sent.")
            else:
                print("No sale detected.")

        else:
            print("[ERROR] Price information not available.")

        print("Sleeping for 1 hour before checking again...\n")
        time.sleep(3600)  # Wait 1 hour before checking again

if __name__ == "__main__":
    main()