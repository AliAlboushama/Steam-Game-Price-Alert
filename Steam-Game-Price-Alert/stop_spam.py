import json
import os

def load_sale_reminders():
    """Load saved sale reminders from sale_reminder.json."""
    if not os.path.exists("sale_reminder.json"):
        return {}  # Return an empty dictionary if the file doesn't exist
    try:
        with open("sale_reminder.json", "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"[ERROR] Error loading sale reminders: {e}")
        return {}

def save_sale_reminder(app_id, game_name, current_price, discount_percent):
    """Save a sale reminder to sale_reminder.json."""
    sale_reminders = load_sale_reminders()
    sale_reminders[app_id] = {
        "game_name": game_name,
        "current_price": current_price,
        "discount_percent": discount_percent
    }
    try:
        with open("sale_reminder.json", "w") as file:
            json.dump(sale_reminders, file, indent=4)
        print(f"Sale reminder saved for {game_name}.")
    except Exception as e:
        print(f"[ERROR] Error saving sale reminder: {e}")

def is_sale_notified(app_id):
    """Check if a sale has already been notified."""
    sale_reminders = load_sale_reminders()
    return app_id in sale_reminders

def remove_expired_sale(app_id):
    """Remove an expired sale from sale_reminder.json."""
    sale_reminders = load_sale_reminders()
    if app_id in sale_reminders:
        del sale_reminders[app_id]
        try:
            with open("sale_reminder.json", "w") as file:
                json.dump(sale_reminders, file, indent=4)
            print(f"Expired sale removed for app ID {app_id}.")
        except Exception as e:
            print(f"[ERROR] Error removing expired sale: {e}")