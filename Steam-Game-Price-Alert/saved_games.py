import re
import json
import sqlite3
import logging
from paths import data_path

DB_NAME = data_path("saved_games.db")

def _app_id_from_link(game_link):
    match = re.search(r'/(app|sub|bundle)/(\d+)', game_link or "")
    if not match:
        return None
    kind, number = match.groups()
    return number if kind == "app" else f"{kind}:{number}"

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

            # Upgrade databases made by older versions: store the app id (to stop duplicates)
            # and the country each price was seen in (prices in EUR and USD must not be compared)
            game_columns = [row[1] for row in cursor.execute("PRAGMA table_info(games)")]
            if 'app_id' not in game_columns:
                cursor.execute("ALTER TABLE games ADD COLUMN app_id TEXT")
            for game_id, game_link in cursor.execute(
                    "SELECT id, game_link FROM games WHERE app_id IS NULL").fetchall():
                cursor.execute("UPDATE games SET app_id = ? WHERE id = ?",
                               (_app_id_from_link(game_link), game_id))
            history_columns = [row[1] for row in cursor.execute("PRAGMA table_info(price_history)")]
            if 'country_code' not in history_columns:
                cursor.execute("ALTER TABLE price_history ADD COLUMN country_code TEXT")
            # Where a game came from: NULL = added by hand, 'wishlist' = wishlist import/sync
            if 'source' not in game_columns:
                cursor.execute("ALTER TABLE games ADD COLUMN source TEXT")
            # Discord messages we sent, so an alert can be edited later (sale ended, cheaper now)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    embeds TEXT NOT NULL,
                    created DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Steam id -> IsThereAnyDeal id, looked up once
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS itad_ids (
                    steam_key TEXT PRIMARY KEY,
                    itad_id TEXT
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
        raise

def add_game(game_name, game_link, app_id=None, source=None):
    """Add a new game to the database. Returns False if the game is already saved."""
    app_id = str(app_id or _app_id_from_link(game_link) or "")
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            if app_id and cursor.execute("SELECT 1 FROM games WHERE app_id = ?", (app_id,)).fetchone():
                return False
            cursor.execute("INSERT INTO games (game_name, game_link, app_id, source) VALUES (?, ?, ?, ?)",
                           (game_name, game_link, app_id or None, source))
            conn.commit()
        logging.info(f"Game '{game_name}' added (app_id: {app_id})")
        return True
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

def get_games_with_details(game_ids=None):
    """Retrieve games as dicts with id, name, app_id and price threshold."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT id, game_name, app_id, price_threshold, game_link, source FROM games").fetchall()
    except sqlite3.Error as e:
        logging.error(f"Error retrieving games: {e}")
        return []
    games = [{'id': r[0], 'name': r[1], 'app_id': r[2] or _app_id_from_link(r[4]),
              'threshold': r[3], 'source': r[5]} for r in rows]
    if game_ids is not None:
        wanted = set(game_ids)
        games = [g for g in games if g['id'] in wanted]
    return games

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
    """Remove a game and its price history from the database by its ID."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_history WHERE game_id = ?", (game_id,))
            cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
            conn.commit()
        logging.info(f"Game with ID {game_id} removed from the database.")
    except sqlite3.Error as e:
        logging.error(f"Error removing game ID {game_id}: {e}")
        raise

def save_price_threshold(game_id, threshold):
    """Save the price threshold for a game in the database (None clears it)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE games SET price_threshold = ? WHERE id = ?", (threshold, game_id))
            conn.commit()
        logging.info(f"Price threshold for game ID {game_id} set to {threshold}.")
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

def save_price_history(game_id, app_id, price, discount_percent, country_code=None):
    """Save a price for a game - only when it changed, so the table doesn't grow every hour."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            last = cursor.execute('''
                SELECT price, discount_percent FROM price_history
                WHERE game_id = ? AND app_id = ? AND (country_code = ? OR country_code IS NULL)
                ORDER BY id DESC LIMIT 1
            ''', (game_id, str(app_id), country_code)).fetchone()
            if last and abs(last[0] - price) < 0.001 and last[1] == discount_percent:
                return
            cursor.execute('''
                INSERT INTO price_history (game_id, app_id, price, discount_percent, country_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (game_id, str(app_id), price, discount_percent, country_code))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error saving price history for game ID {game_id}: {e}")

def get_historical_low(game_id, app_id, country_code=None):
    """Get the lowest price we have ever recorded for a game (in this country's currency)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MIN(price)
                FROM price_history
                WHERE game_id = ? AND app_id = ? AND (country_code = ? OR country_code IS NULL)
            ''', (game_id, str(app_id), country_code))
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving historical low for game ID {game_id}: {e}")
        return None

def is_lowest_ever(game_id, app_id, price, discount_percent, country_code=None):
    """
    True if a discounted price matches or beats every price recorded before.
    Call it BEFORE saving the current price. We also need to have seen a higher
    price at some point - a game first seen mid-sale has nothing to compare against.
    """
    if discount_percent <= 0:
        return False
    try:
        with sqlite3.connect(DB_NAME) as conn:
            low, high = conn.execute('''
                SELECT MIN(price), MAX(price) FROM price_history
                WHERE game_id = ? AND app_id = ? AND (country_code = ? OR country_code IS NULL)
            ''', (game_id, str(app_id), country_code)).fetchone()
    except sqlite3.Error as e:
        logging.error(f"Error checking lowest price for game ID {game_id}: {e}")
        return False
    return low is not None and price <= low + 0.001 and high > price + 0.001

def remove_wishlist_games_not_in(app_ids):
    """
    Remove games that came from the wishlist but aren't on it any more (bought or
    un-wishlisted). Games added by hand are never touched. Returns the removed names.
    """
    keep = {str(a) for a in app_ids}
    if not keep:
        return []  # an empty list usually means private/failed - never wipe on that
    removed = []
    for game in get_games_with_details():
        if game.get('source') == 'wishlist' and str(game['app_id']) not in keep:
            remove_game(game['id'])
            removed.append(game['name'])
    return removed

def save_message(message_id, embeds):
    """Remember a Discord message's embeds so it can be edited later."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT OR REPLACE INTO messages (message_id, embeds) VALUES (?, ?)",
                         (str(message_id), json.dumps(embeds)))
    except sqlite3.Error as e:
        logging.error(f"Error saving message {message_id}: {e}")

def get_message(message_id):
    """The saved embeds of a Discord message, or None."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            row = conn.execute("SELECT embeds FROM messages WHERE message_id = ?",
                               (str(message_id),)).fetchone()
        return json.loads(row[0]) if row else None
    except (sqlite3.Error, ValueError) as e:
        logging.error(f"Error reading message {message_id}: {e}")
        return None

def delete_message(message_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM messages WHERE message_id = ?", (str(message_id),))
    except sqlite3.Error as e:
        logging.error(f"Error deleting message {message_id}: {e}")

def get_itad_ids(steam_keys):
    """Cached IsThereAnyDeal ids: {steam_key: itad_id or None} for keys we've looked up before."""
    if not steam_keys:
        return {}
    try:
        with sqlite3.connect(DB_NAME) as conn:
            marks = ",".join("?" * len(steam_keys))
            rows = conn.execute(f"SELECT steam_key, itad_id FROM itad_ids WHERE steam_key IN ({marks})",
                                list(steam_keys)).fetchall()
        return dict(rows)
    except sqlite3.Error as e:
        logging.error(f"Error reading IsThereAnyDeal ids: {e}")
        return {}

def save_itad_ids(mapping):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.executemany("INSERT OR REPLACE INTO itad_ids (steam_key, itad_id) VALUES (?, ?)",
                             list(mapping.items()))
    except sqlite3.Error as e:
        logging.error(f"Error saving IsThereAnyDeal ids: {e}")

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
            ''', (game_id, str(app_id), limit))
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Error retrieving price history for game ID {game_id}: {e}")
        return []

# This allows testing this module independently
if __name__ == "__main__":
    initialize_database()
    print("Database initialized.")
