import sqlite3
import os
from pyfiglet import Figlet

def get_all_games():
    """Retrieve all games from the database."""
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, game_name FROM games")
    games = cursor.fetchall()
    conn.close()
    return games

def clear_screen():
    """Clears the screen for better readability."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Prints a header with a cool design using ASCII art."""
    f = Figlet(font='slant')
    print("\033[1;34m" + f.renderText(title) + "\033[0m")