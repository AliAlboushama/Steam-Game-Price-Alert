import json
import os
import logging
from paths import data_path

SALE_REMINDER_FILE = data_path("sale_reminder.json")

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
            os.replace(SALE_REMINDER_FILE, f"{SALE_REMINDER_FILE}.backup")
        except Exception:
            pass
        return {}
    except IOError as e:
        logging.error(f"Error reading sale reminder file: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading sale reminders: {e}")
        return {}

def _write_sale_reminders(sale_reminders):
    # Write to a temp file first so a crash mid-write can't corrupt the file
    tmp_file = f"{SALE_REMINDER_FILE}.tmp"
    with open(tmp_file, "w") as file:
        json.dump(sale_reminders, file, indent=4)
    os.replace(tmp_file, SALE_REMINDER_FILE)

def save_sale_reminder(app_id, game_name, current_price, discount_percent):
    """Save a sale reminder to sale_reminder.json."""
    try:
        sale_reminders = load_sale_reminders()
        sale_reminders[str(app_id)] = {
            "game_name": game_name,
            "current_price": current_price,
            "discount_percent": discount_percent
        }
        _write_sale_reminders(sale_reminders)
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
        return str(app_id) in sale_reminders
    except Exception as e:
        logging.error(f"Error checking sale notification status: {e}")
        return False

def should_notify(app_id, current_price):
    """
    True if this deal hasn't been sent yet, or the price dropped further since
    the last alert (e.g. a sale going from 20% off to 50% off).
    """
    try:
        previous = load_sale_reminders().get(str(app_id))
        if previous is None:
            return True
        return current_price < float(previous.get("current_price", current_price)) - 0.001
    except Exception as e:
        logging.error(f"Error checking sale notification status: {e}")
        return False

def remove_expired_sale(app_id):
    """Remove an expired sale from sale_reminder.json."""
    try:
        sale_reminders = load_sale_reminders()
        if str(app_id) in sale_reminders:
            del sale_reminders[str(app_id)]
            _write_sale_reminders(sale_reminders)
            logging.info(f"Expired sale removed for app ID {app_id}")
    except IOError as e:
        logging.error(f"Error removing expired sale: {e}")
    except Exception as e:
        logging.error(f"Unexpected error removing expired sale: {e}")
