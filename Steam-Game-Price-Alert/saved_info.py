import json

def save_user_info(country_code, language, webhook_url, bot_name, bot_avatar):
    """
    Save user information to a JSON file.
    """
    user_info = {
        "country_code": country_code,
        "language": language,
        "webhook_url": webhook_url,
        "bot_name": bot_name,
        "bot_avatar": bot_avatar
    }
    with open("user_info.json", "w") as file:
        json.dump(user_info, file)
    print("User information saved successfully.")

def load_user_info():
    """
    Load user information from the JSON file.
    """
    try:
        with open("user_info.json", "r") as file:
            user_info = json.load(file)
        return user_info
    except FileNotFoundError:
        print("No saved user information found.")
        return None