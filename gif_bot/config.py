import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
TEMP_DIR = os.path.join(BASE_DIR, "temp_gifs")

# Ensure directories exist
os.makedirs(FONTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Available fonts (must exist in /fonts/)
FONTS = {
    "IRANSans": os.path.join(FONTS_DIR, "IRANSans.ttf"),
    "aviny": os.path.join(FONTS_DIR, "aviny.ttf"),
    "ZahraRoosta": os.path.join(FONTS_DIR, "ZahraRoosta.ttf"),
    "Vazir": os.path.join(FONTS_DIR, "Vazir.ttf"),
}

# Text colors
TEXT_COLORS = {
    "white": "white",
    "black": "black",
    "red": "red",
    "blue": "blue",
    "yellow": "yellow",
}

# Speed multipliers -> setpts expression
SPEED_MAP = {
    "x0.5": "2.0",   # slower: PTS * 2
    "x1":   "1.0",   # normal
    "x2":   "0.5",   # faster: PTS * 0.5
    "x4":   "0.25",  # fastest
}

# Max file size for download (20 MB)
MAX_FILE_SIZE = 20 * 1024 * 1024

# Bot watermark text
WATERMARK = "@itgifbot"
