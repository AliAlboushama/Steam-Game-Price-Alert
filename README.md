# Steam Game Sale Alert Bot

🎮 Never miss a Steam sale again! This bot monitors your wishlist games and instantly notifies you through Discord when prices drop. Perfect for gamers who want to grab their favorite titles at the best prices.

## Features

- **Sale Monitoring**: Automatically checks game prices via Steam API hourly
- **Discord Notifications**: Sends alerts to your Discord channel when sales are detected
- **User Preferences**: Stores country code, language, and Discord webhook settings
- **Game Database**: Maintains game information in SQLite
- **Sale Tracking**: Prevents duplicate notifications by tracking active sales

## How It Works

1. Fetches game details from Steam API using the game's `app_id`
2. Compares current price with previous price to detect sales
3. Sends Discord notification with game name, price, discount, and image
4. Saves sale details to prevent duplicate notifications
5. Removes games from tracking when sales end

## Discord Notification Preview

Here's how the sale notifications appear in your Discord channel:

![Discord Notification Preview](https://files.catbox.moe/9eiuob.png)

The notification includes the game's thumbnail, pricing details, and a direct link to the Steam store page.

## Requirements

- Python 3.x
- Required package: `requests`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/Steam-Game-Sale-Alerts.git
cd Steam-Game-Sale-Alerts
```

2. Install required package:
```bash
pip install requests
```

3. Set up Discord webhook:
   - Open Discord server settings
   - Create webhook in desired channel
   - Copy webhook URL

4. Run the script:
```bash
python3 steam_price_bot.py
```

## Usage

### First Run Setup

The script will prompt you to enter:
- Country code (e.g., US, UK)
- Language code (e.g., en for English)
- Discord webhook URL
- Bot name and avatar URL

These settings are saved in `user_info.json` for future use.

### Adding Games

You can add games by providing:
- Steam game link (e.g., https://store.steampowered.com/app/12345/)
- Game name

### Operation

The script automatically checks for sales hourly and sends Discord notifications when sales are detected.

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

## FAQ

**Q: How do I add multiple games?**  
A: Run the script and select the option to add more games when prompted.

**Q: Can I change how often prices are checked?**  
A: Yes, modify the `time.sleep(3600)` value in the script to adjust the frequency (in seconds).

**Q: Not receiving Discord notifications?**  
A: Verify your webhook URL is correct and the webhook is enabled in your Discord server.

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
- Contact: your-email@example.com