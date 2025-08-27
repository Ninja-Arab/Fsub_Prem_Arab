import logging
import os
from datetime import datetime
from config import LOG_FILE

# Buat direktori logs jika belum ada
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def log_activity(user_id, action, details=""):
    """Log aktivitas pengguna"""
    logging.info(f"User {user_id}: {action} | {details}")

def log_system(message):
    """Log sistem"""
    logging.info(f"SYSTEM: {message}")

def log_error(error):
    """Log error"""
    logging.error(f"ERROR: {error}")
