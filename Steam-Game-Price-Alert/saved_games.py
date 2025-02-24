import sqlite3

def initialize_database():
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
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (game_name, game_link) VALUES (?, ?)", (game_name, game_link))
    conn.commit()
    conn.close()
    print(f"Game '{game_name}' added successfully.")

def get_all_games():
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, game_name FROM games")
    games = cursor.fetchall()
    conn.close()
    return games

def get_game_link(game_id):
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT game_link FROM games WHERE id = ?", (game_id,))
    game_link = cursor.fetchone()
    conn.close()
    return game_link[0] if game_link else None

def remove_game(game_id):
    conn = sqlite3.connect("saved_games.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()
    print(f"Game with ID {game_id} has been removed from the database.")

def display_menu():
    games = get_all_games()
    print("\n" + "=" * 40)
    print("           🎮  SAVED GAMES  🎮")
    print("=" * 40 + "\n")
    
    if games:
        for game in games:
            print(f"{game[0]}️⃣  {game[1]}")
    else:
        print("No games saved yet.")
    
    print("\n" + "=" * 40)
    print("           📌  MAIN MENU  📌")
    print("=" * 40)
    print("1️⃣  Scan for sales")
    print("2️⃣  Add a new game")
    print("3️⃣  Scan multiple games")
    print("4️⃣  Remove a game")
    print("=" * 40)
    return input("🔹 Enter your choice (1-4): ")