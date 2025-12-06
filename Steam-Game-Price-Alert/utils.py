import os
import requests
import logging
import re
from urllib.parse import urlparse
from pyfiglet import Figlet
from saved_games import get_all_games as _get_all_games

# Re-export get_all_games from saved_games to avoid duplication
def get_all_games():
    """Retrieve all games from the database."""
    return _get_all_games()

def clear_screen():
    """Clears the screen for better readability."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Prints a header with a cool design using ASCII art."""
    f = Figlet(font='slant')
    print("\033[1;34m" + f.renderText(title) + "\033[0m")

def extract_app_id(game_link):
    """Extract the APP_ID from the Steam game link."""
    try:
        app_id = game_link.split('/app/')[1].split('/')[0]
        return app_id
    except Exception as e:
        logging.error(f"Invalid game link: {e}")
        return None

def get_game_details(app_id, country_code, language):
    """Fetch game details from the Steam API with error handling."""
    try:
        response = requests.get(
            f'https://store.steampowered.com/api/appdetails?appids={app_id}&cc={country_code}&l={language}',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get(app_id, {}).get('data')
    except requests.RequestException as e:
        logging.error(f"Error fetching details for app {app_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching details for app {app_id}: {e}")
        return None

def validate_country_code(country_code):
    """Validate country code format (2 uppercase letters)."""
    if not country_code or len(country_code) != 2:
        return False
    return country_code.isalpha() and country_code.isupper()

def validate_language_code(language):
    """Validate language code format (2-5 lowercase letters/numbers)."""
    if not language or len(language) < 2 or len(language) > 5:
        return False
    return bool(re.match(r'^[a-z0-9]+$', language))

def validate_webhook_url(webhook_url):
    """Validate Discord webhook URL format."""
    if not webhook_url:
        return False
    try:
        parsed = urlparse(webhook_url)
        return (parsed.scheme in ['http', 'https'] and 
                ('discord.com' in parsed.netloc or 'discordapp.com' in parsed.netloc) and
                '/api/webhooks' in parsed.path)
    except Exception:
        return False

def validate_steam_link(steam_link):
    """Validate Steam store link format."""
    if not steam_link:
        return False
    try:
        parsed = urlparse(steam_link)
        return (parsed.scheme in ['http', 'https'] and 
                'steampowered.com' in parsed.netloc and
                '/app/' in parsed.path)
    except Exception:
        return False