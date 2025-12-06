import sqlite3
import logging

DB_NAME = "saved_games.db"

def initialize_database():
    """Initialize the SQLite database for storing games and price thresholds."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_name TEXT NOT NULL,
                    game_link TEXT NOT NULL,
                    price_threshold REAL
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
        raise

def add_game(game_name, game_link):
    """Add a new game to the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO games (game_name, game_link) VALUES (?, ?)", (game_name, game_link))
            conn.commit()
        print(f"Game '{game_name}' added successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error adding game '{game_name}': {e}")
        raise

def get_all_games():
    """Retrieve all games from the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, game_name FROM games")
            games = cursor.fetchall()
            return games
    except sqlite3.Error as e:
        logging.error(f"Error retrieving games: {e}")
        return []

def get_game_link(game_id):
    """Get the game link for a specific game ID."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT game_link FROM games WHERE id = ?", (game_id,))
            game_link = cursor.fetchone()
            return game_link[0] if game_link else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving game link for ID {game_id}: {e}")
        return None

def remove_game(game_id):
    """Remove a game from the database by its ID."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
            conn.commit()
        print(f"Game with ID {game_id} has been removed from the database.")
    except sqlite3.Error as e:
        logging.error(f"Error removing game ID {game_id}: {e}")
        raise

def save_price_threshold(game_id, threshold):
    """Save the price threshold for a game in the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE games SET price_threshold = ? WHERE id = ?", (threshold, game_id))
            conn.commit()
        print(f"Price threshold for game ID {game_id} set to {threshold}.")
    except sqlite3.Error as e:
        logging.error(f"Error saving price threshold for game ID {game_id}: {e}")
        raise

def get_price_threshold(game_id):
    """Retrieve the price threshold for a game from the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT price_threshold FROM games WHERE id = ?", (game_id,))
            threshold = cursor.fetchone()
            return threshold[0] if threshold else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving price threshold for game ID {game_id}: {e}")
        return None

# This allows testing this module independently
if __name__ == "__main__":
    initialize_database()
    print("Database initialized.")
    # Test code if needed
    # add_game("Test Game", "https://example.com")
    # save_price_threshold(1, 29.99)
    # threshold = get_price_threshold(1)
    # print(f"Price threshold for game ID 1: {threshold}")
    # games = get_all_games()
    # print(f"Games in database: {games}")