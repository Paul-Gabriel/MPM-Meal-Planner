"""Configuration management for Meal Planner application."""
import os
from typing import Final
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, using defaults

# API Configuration
SPOONACULAR_API_KEY: Final[str] = os.getenv('SPOONACULAR_API_KEY', '5ff4f96c305e44fd8a8bb9d94278e058')

# Application Settings
APP_HOST: Final[str] = os.getenv('APP_HOST', '0.0.0.0')
APP_PORT: Final[int] = int(os.getenv('APP_PORT', '8000'))
DEBUG: Final[bool] = os.getenv('DEBUG', 'False').lower() == 'true'

# Date Format
DATE_FORMAT: Final[str] = "%d-%m-%Y"

# Pantry Alerts Configuration
DAYS_BEFORE_EXPIRY: Final[int] = int(os.getenv('DAYS_BEFORE_EXPIRY', '5'))
LOW_STOCK_THRESHOLD: Final[dict[str, int]] = {
    "g": int(os.getenv('LOW_STOCK_THRESHOLD_G', '200')),
    "ml": int(os.getenv('LOW_STOCK_THRESHOLD_ML', '500')),
    "pcs": int(os.getenv('LOW_STOCK_THRESHOLD_PCS', '3')),
    "cloves": int(os.getenv('LOW_STOCK_THRESHOLD_CLOVES', '2'))
}

# File Paths
BASE_DIR: Final[Path] = Path(__file__).parent.parent
DATA_DIR: Final[Path] = BASE_DIR / 'data'
STATIC_DIR: Final[Path] = BASE_DIR / 'static'
TEMPLATES_DIR: Final[Path] = BASE_DIR / 'templates'

