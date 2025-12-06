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
            # Create price_history table for tracking price changes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    app_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    discount_percent INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                )
            ''')
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_history_game_app 
                ON price_history(game_id, app_id, timestamp)
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

def save_price_history(game_id, app_id, price, discount_percent):
    """Save price history for a game."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO price_history (game_id, app_id, price, discount_percent)
                VALUES (?, ?, ?, ?)
            ''', (game_id, app_id, price, discount_percent))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error saving price history for game ID {game_id}: {e}")

def get_historical_low(game_id, app_id):
    """Get the historical lowest price for a game."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MIN(price), timestamp 
                FROM price_history 
                WHERE game_id = ? AND app_id = ?
            ''', (game_id, app_id))
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving historical low for game ID {game_id}: {e}")
        return None

def get_price_history(game_id, app_id, limit=10):
    """Get recent price history for a game."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT price, discount_percent, timestamp 
                FROM price_history 
                WHERE game_id = ? AND app_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (game_id, app_id, limit))
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Error retrieving price history for game ID {game_id}: {e}")
        return []

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