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
                    send_discord_notification(
                        game_name=game_name,
                        current_price=current_price,
                        discount_percent=discount_percent,
                        image_url=image_url,
                        webhook_url=webhook_url,
                        bot_name=bot_name,
                        bot_avatar=bot_avatar,
                        app_id=app_id  # Pass the app_id here
                    )
                    last_known_price = current_price
                else:
                    print("Sale detected, but price has not changed. No notification sent.")
            else:
                print("No sale detected.")

        else:
            print("[ERROR] Price information not available.")

        print("Sleeping for 1 hour before checking again...\n")
        time.sleep(3600)  # Wait 1 hour before checking again