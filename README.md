# Steam Game Price Alert Bot

🎮 Never miss a Steam sale again! This bot watches the games you care about and pings your Discord channel the moment one goes on sale or drops below your target price.

## ✨ Features

### Alerts
- **Discord notifications** with the game's cover, sale price, normal price, discount, **when the sale ends** and the Steam review score
- **Two ways to alert**: any discount, or only when the price drops to *your* target
- **Lowest price ever** ⭐ highlight when a sale beats every price the bot has seen
- **No spam**: one alert per sale, plus a new one if the sale gets deeper (e.g. 20% → 50% off)
- **Never misses an alert**: if Discord is down, the bot tries again next check
- **Test button**: send a clearly marked TEST alert to check your webhook works

### Games
- **Import your Steam wishlist** in one step, and optionally keep it in sync automatically
- **Add games by name** (type "stardew valley"), by store link, or by app id
- **Your real currency**: prices shown exactly as your Steam store shows them (`17,99€`, `£14.99`, `$17.99`)
- **Game info**: release date, reviews, Metacritic, genres, developers, description
- **Price history** saved in a local database

### Runs on its own
- **Background mode** (`--daemon`) checks all your games on a timer with no menu
- Ready-made setups for **Docker**, **Linux (systemd)** and **Windows**, so it keeps running after a restart
- **Fast**: one Steam request checks up to 50 games

## Screenshots
![Main Page](https://files.catbox.moe/eggd5n.png)

![Scanning Game Sales UI](https://files.catbox.moe/8quot8.png)

## Discord Notification Preview

![Discord Notification Preview](https://files.catbox.moe/9eiuob.png)

Each alert includes:
- Cover image and a link to the Steam store page
- Sale price, normal price and discount
- ⏰ When the sale ends, shown in each reader's own time zone
- 👍 Steam review score
- ⭐ "Lowest price ever" when it applies
- Colour: red = sale, green = your price target met, gold = lowest price ever

## Requirements

- **Python 3.8+**
- `requests` and `pyfiglet` (installed below)
- A Discord webhook (Discord server settings → Integrations → Webhooks → New Webhook → Copy URL)

## Installation

```bash
git clone https://github.com/UnboundFate/Steam-Game-Price-Alert.git
cd Steam-Game-Price-Alert/Steam-Game-Price-Alert
pip install -r requirements.txt
python3 main.py
```

On Windows use `python main.py`.

### First run

The bot asks for:
- **Country code**: decides the store and currency (e.g. `US`, `GB`, `DE`, `FI`)
- **Language code**: e.g. `en`, `de`, `fr` (or a Steam language name like `german`)
- **Discord webhook URL**
- **Bot name** and **avatar URL** (both optional; leave empty for Discord's default)

You can change all of these later in **Settings** (menu option 9).

## Usage

### Main menu

| Option | What it does |
|---|---|
| 1. Scan for sales | Watch one game |
| 2. Add a new game | Paste a store link, an app id, or type a name to search |
| 3. Scan multiple games | Watch several games (or type `all`) |
| 4. Remove a game | Remove a game and its price history |
| 5. Set price threshold | Set a target price for a game (in your store's currency; `0` removes it) |
| 6. View current prices | All prices at once, with sale end times |
| 7. View detailed game info | Reviews, release date, genres and more |
| 8. Import my Steam wishlist | Add every game on your public wishlist |
| 9. Settings | Change country, language, webhook, bot name/avatar, check interval, wishlist auto-add, **send a test notification** |

### Importing your wishlist

Your wishlist must be public: Steam → Profile → Edit Profile → Privacy Settings → **Game details: Public**.
Then pick option 8 and enter your profile link (`https://steamcommunity.com/id/yourname/`), your custom URL name, or your SteamID64.

Turn on **Settings → Auto-add new wishlist games** and background mode will add anything you wishlist later.

### Scanning modes

1. **Price target**: alerts when the price drops to your target (set with option 5)
2. **Any sale**: alerts whenever the game is discounted

Background mode uses both: a game with a target uses the target, every other game alerts on any sale.

## Run it in the background

Set up your settings and games with `python3 main.py` first. Then pick one of these:

### Any computer: just the command

```bash
python3 main.py --daemon   # check all games forever (Ctrl+C to stop)
python3 main.py --once     # check all games once and exit (for cron / Task Scheduler)
```

### Windows

Double-click `run-in-background.bat`. It runs with no window until you log out or restart.
To start it automatically when you log in, press `Win+R`, type `shell:startup`, and put a shortcut to `run-in-background.bat` in that folder.
To stop it: Task Manager → Details → end `pythonw.exe`.

### Linux (systemd)

```bash
# edit YOUR_USER and the paths in the file first
sudo cp deploy/steam-price-alert.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now steam-price-alert
journalctl -u steam-price-alert -f   # logs
```

### Docker

From the top folder of the repo:

```bash
docker compose run --rm steam-price-alert python main.py   # first time: settings + games
docker compose up -d                                       # run in the background
docker compose logs -f                                     # logs
```

Your data is kept in the `steam-alert-data` volume. Change `TZ` in `docker-compose.yml` to your time zone.

## Configuration

| Setting | Where |
|---|---|
| Country, language, webhook, bot name/avatar | Settings menu, or `user_info.json` |
| How often to check (default 60 minutes, minimum 10) | Settings menu → "Change how often to check" |
| Where data files are stored | Next to the scripts, or set the `STEAM_ALERT_DATA_DIR` environment variable |

## File Structure

```
Steam-Game-Price-Alert/
├── main.py                 # Menu and command line (--daemon, --once)
├── background.py           # Background mode
├── scanner.py              # Price checks and alert decisions
├── steam_api.py            # Steam store API: prices, wishlist, search
├── notifier.py             # Discord messages
├── saved_games.py          # Database: games, targets, price history
├── saved_info.py           # Your settings
├── stop_spam.py            # Remembers which sales were already sent
├── utils.py                # Helpers: links, validation, formatting
├── paths.py                # Where data files are stored
├── run-in-background.bat   # Windows background start
└── requirements.txt

Created automatically (never commit these, they hold your webhook):
├── user_info.json
├── saved_games.db
├── sale_reminder.json
└── debug.log
```

## FAQ

**Q: Not receiving Discord notifications?**
A: Open Settings → "Send a test notification". If Discord rejects it, check the webhook URL. Details are in `debug.log`.

**Q: Can I change how often prices are checked?**
A: Yes: Settings → "Change how often to check" (minimum 10 minutes).

**Q: Why does a game say "Coming soon - not on sale yet"?**
A: It isn't released yet. Keep it in your list; you'll get an alert if it launches with a discount.

**Q: What is "Lowest price ever"?**
A: The bot saves every price change it sees. When a sale matches or beats the lowest one it has recorded, the alert is highlighted. It only knows the prices it has seen itself.

**Q: Will the bot keep working after I restart my computer?**
A: Only in background mode with one of the setups above (Windows startup shortcut, systemd or Docker). Your games and settings are always kept.

**Q: I'm upgrading from v1.x. Do I lose my games?**
A: No. Your database is upgraded automatically the first time v2 starts.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with a detailed description

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Support

For issues or questions, open an issue on GitHub.
