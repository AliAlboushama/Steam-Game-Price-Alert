import os

# Data files live next to the scripts (or in STEAM_ALERT_DATA_DIR), not in whatever
# folder the bot happens to be started from
DATA_DIR = os.environ.get("STEAM_ALERT_DATA_DIR") or os.path.dirname(os.path.abspath(__file__))

def data_path(filename):
    """Return the full path for a data file, creating the data folder if needed."""
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, filename)
