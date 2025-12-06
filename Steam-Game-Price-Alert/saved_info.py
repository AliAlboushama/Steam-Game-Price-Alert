import json
import logging

def save_user_info(country_code, language, webhook_url, bot_name, bot_avatar):
    """
    Save user information to a JSON file.
    """
    try:
        user_info = {
            "country_code": country_code,
            "language": language,
            "webhook_url": webhook_url,
            "bot_name": bot_name,
            "bot_avatar": bot_avatar
        }
        with open("user_info.json", "w") as file:
            json.dump(user_info, file, indent=4)
        print("User information saved successfully.")
    except IOError as e:
        logging.error(f"Error saving user info: {e}")
        print(f"\033[1;31mError saving user information: {e}\033[0m")
        raise
    except Exception as e:
        logging.error(f"Unexpected error saving user info: {e}")
        print(f"\033[1;31mUnexpected error saving user information: {e}\033[0m")
        raise

def load_user_info():
    """
    Load user information from the JSON file.
    """
    try:
        with open("user_info.json", "r") as file:
            user_info = json.load(file)
            # Validate required fields
            required_fields = ["country_code", "language", "webhook_url", "bot_name", "bot_avatar"]
            if all(field in user_info for field in required_fields):
                return user_info
            else:
                logging.warning("User info file missing required fields")
                return None
    except FileNotFoundError:
        logging.info("No saved user information found.")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing user info JSON: {e}")
        print(f"\033[1;31mError reading user information file. Please reconfigure.\033[0m")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading user info: {e}")
        return None