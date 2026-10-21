# Steam Game Price Alert Bot

🎮 Never miss a Steam sale again! This bot monitors your wishlist games and instantly notifies you through Discord when prices drop. Perfect for gamers who want to grab their favorite titles at the best prices.


## ✨ Features

### Core Features
- **Sale Monitoring**: Automatically checks game prices via Steam API hourly
- **Discord Notifications**: Sends rich embeds to your Discord channel when sales are detected
- **Price History Tracking**: Tracks price changes over time in SQLite database
- **Historical Low Detection**: Automatically detects and highlights "Lowest Price Ever!" deals
- **Multiple Scanning Modes**: 
  - Price target mode (notify when price drops below threshold)
  - Normal sale detection mode (notify for any discount)
- **Scan Multiple Games**: Track multiple game sales simultaneously

### Game Management
- **Add/Remove Games**: Manage your watchlist easily
- **View Current Prices**: Check all game prices at once without starting a scan
- **Detailed Game Info**: View comprehensive game information including:
  - Release date
  - Reviews and ratings (Steam reviews + Metacritic)
  - Genres and categories
  - Developers and publishers
  - Game description
  - Historical low prices

### User Experience
- **Input Validation**: Validates country codes, language codes, webhook URLs, and Steam links
- **Persistent Settings**: Saves user preferences (country, language, webhook, bot name/avatar)
- **Error Handling**: Robust error handling with logging throughout
- **Clean Interface**: Auto-refreshing display with ASCII art headers
- **Price Thresholds**: Set custom price targets for individual games

## Screenshots
![Main Page](https://files.catbox.moe/eggd5n.png)

![Scanning Game Sales UI](https://files.catbox.moe/8quot8.png)

## How It Works

1. **Game Addition**: Extracts `app_id` from Steam store links and fetches game details
2. **Price Monitoring**: Fetches current prices from Steam API using country/language settings
3. **Price History**: Automatically saves all price checks to SQLite database
4. **Sale Detection**: 
   - Compares current price with historical data
   - Checks against user-defined price targets (if configured)
   - Detects any discounts or price drops
5. **Historical Low**: Compares current price with all historical prices to identify record lows
6. **Notifications**: Sends rich Discord embeds with:
   - Game name, image, and store link
   - Current price and discount percentage
   - Historical low indicator (when applicable)
7. **Duplicate Prevention**: Tracks active sales to prevent spam notifications
8. **Data Persistence**: All data saved to database and JSON files for reliability

## Discord Notification Preview

Here's how the sale notifications appear in your Discord channel:

![Discord Notification Preview](https://files.catbox.moe/9eiuob.png)

The notification includes:
- Game's header image/thumbnail
- Current price and discount percentage
- **Historical low indicator** (when applicable)
- Direct link to Steam store page
- Color-coded embeds (red for sales, green for price targets)

## Requirements

This project requires **Python 3.7+** and the following packages:

- `requests` (>=2.31.0)
- `pyfiglet` (>=1.0.2)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/UnboundFate/Steam-Game-Price-Alert.git
cd Steam-Game-Price-Alert/Steam-Game-Price-Alert
```

2. Install required packages:
```bash
# Using pip
pip install -r requirements.txt

# Or install individually
pip install requests pyfiglet
```

3. Set up Discord webhook:
   - Open Discord server settings
   - Create webhook in desired channel
   - Copy webhook URL

4. Run the script:
```bash
python3 main.py
```

## Usage

### First Run Setup

When you first run the script, it will prompt you to enter:
- **Country code** (e.g., US, UK, DE) - Validated as 2-letter uppercase code
- **Language code** (e.g., en, es, fr) - Validated format
- **Discord webhook URL** - Validated Discord webhook format
- **Bot name** - Name displayed in Discord notifications
- **Bot avatar URL** - Optional image URL for bot avatar

These settings are saved in `user_info.json` for future use.

### Main Menu Options

1. **Scan for sales** - Monitor a single game for price drops
2. **Add a new game** - Add games to your watchlist using Steam store links
3. **Scan multiple games** - Monitor multiple games simultaneously
4. **Remove a game** - Remove games from your watchlist
5. **Set price threshold** - Set custom price targets for games
6. **View current prices** - Check all game prices at once (NEW!)
7. **View detailed game info** - See comprehensive game information (NEW!)

### Adding Games

You can add games by providing a Steam store link:
- Example: `https://store.steampowered.com/app/12345/GameName/`
- The script validates the link format and extracts the game ID automatically

### Price Monitoring

The bot offers two scanning modes:

1. **Price Target Mode**: Notifies you when a game's price drops below your set threshold
2. **Normal Sale Detection**: Notifies you whenever any discount is detected

### Historical Low Tracking

- The bot automatically tracks price history for all monitored games
- When a price matches or beats the historical low, you'll see:
  - ⭐ **LOWEST PRICE EVER!** ⭐ indicator in console
  - Special highlight in Discord notifications
  - Historical low price displayed in game info views

### Operation

- The script checks for sales hourly (configurable)
- Sends Discord notifications when sales are detected
- Prevents duplicate notifications for the same sale
- Automatically tracks price history in the database

## Configuration

### Discord Webhook Setup

1. Go to Discord server settings
2. Navigate to Integrations > Webhooks
3. Create new webhook
4. Copy URL for script configuration

### Bot Customization

You can customize:
- Bot name
- Avatar image (via URL)

## File Structure

```
Steam-Game-Price-Alert/
├── main.py              # Main application entry point
├── scanner.py           # Scanning functions for single/multiple games
├── notifier.py          # Discord webhook notification handler
├── paths.py             # Where data files are stored
├── saved_games.py       # Database operations for games and price history
├── saved_info.py        # User settings management
├── stop_spam.py         # Sale notification tracking (prevents duplicates)
├── utils.py             # Utility functions (API calls, validation, formatting)
├── requirements.txt     # Python dependencies
├── saved_games.db       # SQLite database (created automatically)
├── user_info.json       # User configuration (created automatically)
└── sale_reminder.json   # Active sale tracking (created automatically)
```

## FAQ

**Q: How do I add multiple games?**  
A: Use option 2 in the main menu to add games. You can add multiple games in sequence, or use option 3 to scan multiple games at once.

**Q: Can I change how often prices are checked?**  
A: Yes, modify the `SLEEP_TIME` constant in `main.py` (default: 3600 seconds = 1 hour).

**Q: Not receiving Discord notifications?**  
A: Verify your webhook URL is correct, the webhook is enabled in your Discord server, and check the `debug.log` file for error messages.

**Q: What is the "Historical Low" feature?**  
A: The bot tracks all price changes over time. When a price matches or beats the lowest price ever recorded, it shows a special indicator. This helps you identify the best deals!

**Q: Can I view game information without scanning?**  
A: Yes! Use option 7 "View detailed game info" to see comprehensive information about any game in your watchlist, including reviews, tags, and release dates.

**Q: How does price history tracking work?**  
A: Every time the bot checks a game's price (during scans or when viewing current prices), it saves the price to the database. This creates a historical record that enables the "Lowest Price Ever" feature.

**Q: Will the bot work if I restart my computer?**  
A: The bot saves all data (games, settings, price history) to files and database. You can restart anytime and continue where you left off. However, you'll need to manually restart the scanning process.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create feature branch
3. Submit pull request with detailed description

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
- Open an issue on GitHub
