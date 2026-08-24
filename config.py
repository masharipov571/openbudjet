import os
from dotenv import load_dotenv

# Load local .env file if present
load_dotenv()

# Telegram Bot Token (Must be set via environment variable or Render Dashboard)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Strict target initiative details
INITIATIVE_ID = os.getenv("INITIATIVE_ID", "6d1035da-d586-49aa-b344-c80bd5878c0d")
TARGET_INITIATIVE_ID = INITIATIVE_ID
BOARD_ID = os.getenv("BOARD_ID", "55")
TARGET_BOARD_ID = BOARD_ID
OPENBUDGET_BASE_URL = os.getenv("OPENBUDGET_BASE_URL", "https://new.openbudget.uz")

TARGET_INITIATIVE_URL = f"{OPENBUDGET_BASE_URL}/uz/initiative-budget/active-initiatives/{BOARD_ID}/{INITIATIVE_ID}"

# OpenBudget API Endpoints
API_SEND_CODE_URL = f"{OPENBUDGET_BASE_URL}/api/v1/user/temp/vote"
API_VERIFY_CODE_URL = f"{OPENBUDGET_BASE_URL}/api/v1/user/temp/vote/verify"
