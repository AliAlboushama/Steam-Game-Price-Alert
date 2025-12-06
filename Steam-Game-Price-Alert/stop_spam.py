import json
import os
import logging

SALE_REMINDER_FILE = "sale_reminder.json"

def load_sale_reminders():
    """Load saved sale reminders from sale_reminder.json."""
    if not os.path.exists(SALE_REMINDER_FILE):
        return {}  # Return an empty dictionary if the file doesn't exist
    try:
        with open(SALE_REMINDER_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing sale reminder JSON: {e}")
        print(f"\033[1;31m[ERROR] Error parsing sale reminder file. Resetting...\033[0m")
        # Backup corrupted file and return empty dict
        try:
            os.rename(SALE_REMINDER_FILE, f"{SALE_REMINDER_FILE}.backup")
        except Exception:
            pass
        return {}
    except IOError as e:
        logging.error(f"Error reading sale reminder file: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading sale reminders: {e}")
        return {}

def save_sale_reminder(app_id, game_name, current_price, discount_percent):
    """Save a sale reminder to sale_reminder.json."""
    try:
        sale_reminders = load_sale_reminders()
        sale_reminders[app_id] = {
            "game_name": game_name,
            "current_price": current_price,
            "discount_percent": discount_percent
        }
        with open(SALE_REMINDER_FILE, "w") as file:
            json.dump(sale_reminders, file, indent=4)
        logging.info(f"Sale reminder saved for {game_name} (app_id: {app_id})")
    except IOError as e:
        logging.error(f"Error saving sale reminder: {e}")
        print(f"\033[1;31m[ERROR] Error saving sale reminder: {e}\033[0m")
    except Exception as e:
        logging.error(f"Unexpected error saving sale reminder: {e}")
        print(f"\033[1;31m[ERROR] Unexpected error saving sale reminder: {e}\033[0m")

def is_sale_notified(app_id):
    """Check if a sale has already been notified."""
    try:
        sale_reminders = load_sale_reminders()
        return app_id in sale_reminders
    except Exception as e:
        logging.error(f"Error checking sale notification status: {e}")
        return False

def remove_expired_sale(app_id):
    """Remove an expired sale from sale_reminder.json."""
    try:
        sale_reminders = load_sale_reminders()
        if app_id in sale_reminders:
            del sale_reminders[app_id]
            with open(SALE_REMINDER_FILE, "w") as file:
                json.dump(sale_reminders, file, indent=4)
            logging.info(f"Expired sale removed for app ID {app_id}")
    except IOError as e:
        logging.error(f"Error removing expired sale: {e}")
    except Exception as e:
        logging.error(f"Unexpected error removing expired sale: {e}")