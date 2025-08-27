import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = list(map(int, os.getenv("OWNER_ID", "2113728627").split(",")))
PROTECTED_CHANNEL = os.getenv("PROTECTED_CHANNEL")
NOTIFICATION_CHANNEL = os.getenv("NOTIFICATION_CHANNEL")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Subscription Configuration
DEFAULT_SUB_DAYS = int(os.getenv("DEFAULT_SUB_DAYS", "30"))

# Logging Configuration
LOG_FILE = "logs/bot.log"
