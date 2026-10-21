import time
import logging
from rich.text import Text
import ui
from saved_games import get_games_with_details, save_price_history, get_historical_low, is_lowest_ever
from utils import format_sale_end
from stop_spam import save_sale_reminder, should_notify, get_sale_reminder, remove_expired_sale
from steam_api import get_prices, store_url
from itad import get_steam_lows
from notifier import send_alerts, edit_alert

SLEEP_TIME = 3600  # 1 hour

MODE_TARGET = "1"   # notify when price drops to the user's threshold
MODE_SALE = "2"     # notify for any discount
MODE_AUTO = "auto"  # background mode: price target if the game has one, otherwise any discount

def choose_mode():
    """Ask which scanning mode to use. Returns MODE_TARGET, MODE_SALE or None."""
    ui.header("Scan mode")
    ui.menu([("1", "Price target - alert when the price drops to your target"),
             ("2", "Any sale - alert whenever the game is discounted"),
             ("0", "Cancel")])
    while True:
        choice = ui.ask("Choose: ")
        if choice in (MODE_TARGET, MODE_SALE):
            return choice
        if choice == "0":
            return None
        ui.error("Please enter 1 or 2.")

def _evaluate(game, info, settings, mode, steam_low, steam_failed):
    """
    Decide what to do about one game. Returns (row, alert, ended_reminder):
    row = (price Text, discount Text, result Text) for the table,
    alert = dict to send (or None), ended_reminder = old alert to mark as ended (or None).
    """
    game_id, item_id = game['id'], str(game['app_id'])
    country_code = settings['country_code']

    if not info or info.get('final') is None:
        if steam_failed and not info:
            return (Text("-"), Text(""), Text("Steam unreachable", style="bad")), None, None
        return (ui.price_text(info), Text(""), Text("Nothing to watch", style="muted")), None, None

    current_price = info['final'] / 100
    discount = info.get('discount_percent', 0)

    # Lowest ever: IsThereAnyDeal's real Steam low if we have it, otherwise our own history
    # (checked BEFORE saving today's price, or today's price would always be "the lowest")
    local_low = get_historical_low(game_id, item_id, country_code)
    if steam_low:
        lowest_ever = discount > 0 and current_price <= steam_low['price'] + 0.001
    else:
        lowest_ever = is_lowest_ever(game_id, item_id, current_price, discount, country_code)
    save_price_history(game_id, item_id, current_price, discount, country_code)

    threshold = game.get('threshold')
    if mode == MODE_AUTO:
        mode = MODE_TARGET if threshold is not None else MODE_SALE
    min_discount = int(settings.get('min_discount_percent', 0) or 0)

    if mode == MODE_TARGET:
        if threshold is None:
            result = Text("No target set", style="muted")
            qualifies = False
        else:
            qualifies = current_price <= threshold
            result = Text(f"Target {threshold:.2f} not met", style="muted")
        reason = "target"
    else:
        reason = "sale"
        qualifies = discount > 0 and discount >= min_discount
        if qualifies and settings.get('alert_only_at_lowest') and steam_low and not lowest_ever:
            qualifies = False
            result = Text("Not the all-time low", style="muted")
        elif discount > 0 and not qualifies:
            result = Text(f"Below {min_discount}% minimum", style="muted")
        else:
            result = Text("No sale", style="muted")

    reminder = get_sale_reminder(item_id)
    if not qualifies:
        # Only call it "ended" when the deal is really over, not when a setting filtered it out
        deal_active = discount > 0 or (threshold is not None and current_price <= threshold)
        return (ui.price_text(info), ui.discount_badge(discount), result), None, \
            (reminder if not deal_active else None)

    if not should_notify(item_id, current_price):
        return (ui.price_text(info), ui.discount_badge(discount), Text("Already sent", style="muted")), None, None

    alert = {
        'game': game, 'item_id': item_id, 'name': game['name'], 'url': store_url(item_id),
        'price': info, 'reason': reason, 'threshold': threshold, 'lowest_ever': lowest_ever,
        'steam_low': steam_low, 'local_low': local_low, 'current_price': current_price,
        'loud': reason == "target" or lowest_ever, 'previous': reminder,
    }
    return (ui.price_text(info), ui.discount_badge(discount), None), alert, None

def check_games(games, settings, mode, show=True):
    """
    Check every game once: one Steam request per 100 games, alerts grouped into as few
    Discord messages as possible, and earlier alerts edited when a sale ends or gets cheaper.
    Returns a summary dict: checked, alerts, failed (bool), reason.
    """
    ids = [str(g['app_id']) for g in games]
    prices, steam_failed = get_prices(ids, settings['country_code'], settings['language'])
    lows = get_steam_lows(ids, settings.get('itad_api_key'), settings['country_code'])

    rows, alerts, ended = [], [], []
    for game in games:
        item_id = str(game['app_id'])
        try:
            row, alert, ended_reminder = _evaluate(game, prices.get(item_id), settings, mode,
                                                   lows.get(item_id), steam_failed)
        except Exception as e:
            logging.exception(f"Error checking {game['name']}: {e}")
            row, alert, ended_reminder = (Text("-"), Text(""), Text(f"Error: {e}", style="bad")), None, None
        rows.append((game, row, alert))
        if alert:
            alerts.append(alert)
        if ended_reminder:
            ended.append((item_id, ended_reminder))

    sent = send_alerts(alerts, settings) if alerts else 0
    for alert in alerts:
        if alert.get('message_id'):
            previous = alert.get('previous')
            if previous and previous.get('message_id'):
                edit_alert(settings, previous['message_id'], previous.get('embed_index'),
                           f"Now even cheaper: {alert['price']['final_formatted']} - see the newer alert")
            save_sale_reminder(alert['item_id'], alert['name'], alert['current_price'],
                               alert['price'].get('discount_percent', 0),
                               alert['message_id'], alert['embed_index'])
    for item_id, reminder in ended:
        if reminder.get('message_id'):
            edit_alert(settings, reminder['message_id'], reminder.get('embed_index'), "Sale ended")
        remove_expired_sale(item_id)

    if show:
        table = ui.table("Game", ("Price", {"no_wrap": True}), ("", {"no_wrap": True}), "Result")
        for game, (price, badge, result), alert in rows:
            if alert:
                if alert.get('message_id'):
                    label = "Alert sent" + (" · lowest ever" if alert['lowest_ever'] else "")
                    result = Text(label, style="gold" if alert['lowest_ever'] else "good")
                else:
                    result = Text("Alert FAILED - retry next check", style="bad")
            name = Text(game['name'], style="name")
            info = prices.get(str(game['app_id'])) or {}
            if info.get('discount_end'):
                name.append(f"\nends {format_sale_end(info['discount_end'])}", style="muted")
            table.add_row(name, price, badge, result)
        ui.console.print(table)

    failed_alerts = len(alerts) - sent
    reason = ("Steam could not be reached" if steam_failed else
              f"{failed_alerts} Discord alert(s) failed" if failed_alerts else "")
    return {'checked': len(games), 'alerts': sent, 'failed': bool(reason), 'reason': reason}

def check_interval(settings):
    """Seconds between checks: the user's setting (minutes), never faster than every 10 minutes."""
    try:
        return max(10, int(settings.get('check_interval_minutes', SLEEP_TIME // 60))) * 60
    except (TypeError, ValueError):
        return SLEEP_TIME

def scan_loop(games, settings, mode):
    """Check the games on a timer until the user presses Ctrl+C."""
    interval = check_interval(settings)
    ui.header("Scanning", f"every {interval // 60} min")
    ui.note(f"Watching {len(games)} game(s). Press Ctrl+C to stop and go back to the menu.\n")
    try:
        while True:
            summary = check_games(games, settings, mode)
            ui.note(f"{time.strftime('%H:%M')}  Checked {summary['checked']} game(s), "
                    f"sent {summary['alerts']} alert(s). Next check in {interval // 60} minutes.")
            time.sleep(interval)
    except KeyboardInterrupt:
        ui.note("\nScanning stopped.")

def _pick_games(games, prompt):
    """Show the game list and parse '1,3,5' or 'all'. Returns the chosen games or []."""
    table = ui.table(("#", {"style": "accent", "justify": "right"}), "Game")
    for index, game in enumerate(games, start=1):
        table.add_row(str(index), game['name'])
    ui.console.print(table)
    answer = ui.ask(prompt)
    if answer.lower() == "all":
        return list(games)
    numbers = [int(n) for n in answer.replace(" ", "").split(",") if n.isdigit()]
    if not numbers or numbers == [0]:
        return []
    if any(n < 1 or n > len(games) for n in numbers):
        ui.error("Some of those numbers aren't in the list.")
        ui.pause()
        return []
    return [games[n - 1] for n in dict.fromkeys(numbers)]

def scan_for_sales(settings):
    """Scan a single game for sales in a loop."""
    games = get_games_with_details()
    if not games:
        ui.warn("No saved games yet - add one first.")
        ui.pause()
        return
    ui.header("Scan one game")
    chosen = _pick_games(games, "Game number (0 to cancel): ")[:1]
    if chosen:
        mode = choose_mode()
        if mode:
            scan_loop(chosen, settings, mode)

def scan_multiple_games(settings):
    """Scan several games for sales in a loop."""
    games = get_games_with_details()
    if not games:
        ui.warn("No saved games yet - add one first.")
        ui.pause()
        return
    ui.header("Scan several games")
    chosen = _pick_games(games, "Game numbers, e.g. 1,3,5 or 'all' (0 to cancel): ")
    if chosen:
        mode = choose_mode()
        if mode:
            scan_loop(chosen, settings, mode)
