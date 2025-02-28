import sqlite3

def initialize_database():
    """Initialize the SQLite database for storing games."""
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            game_link TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_game(game_name, game_link):
    """Add a new game to the database."""
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (game_name, game_link) VALUES (?, ?)", (game_name, game_link))
    conn.commit()
    conn.close()
    print(f"Game '{game_name}' added successfully.")

def get_all_games():
    """Retrieve all games from the database."""
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, game_name FROM games")
    games = cursor.fetchall()
    conn.close()
    return games

def get_game_link(game_id):
    """Get the game link for a specific game ID."""
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT game_link FROM games WHERE id = ?", (game_id,))
    game_link = cursor.fetchone()
    conn.close()
    return game_link[0] if game_link else None

def remove_game(game_id):
    """Remove a game from the database by its ID."""
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()
    print(f"Game with ID {game_id} has been removed from the database.")

# This allows testing this module independently
if __name__ == "__main__":
    initialize_database()
    print("Database initialized.")
    # Test code if needed
    # add_game("Test Game", "https://example.com")
    # games = get_all_games()
    # print(f"Games in database: {games}")