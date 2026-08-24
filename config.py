import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Tashabbus identifikatorlari
INITIATIVE_ID = os.getenv("INITIATIVE_ID", "6d1035da-d586-49aa-b344-c80bd5878c0d")
TARGET_INITIATIVE_ID = INITIATIVE_ID
BOARD_ID = os.getenv("BOARD_ID", "55")
TARGET_BOARD_ID = BOARD_ID

# Qisqa sonli loyiha kodi (OpenBudget SMS va rasmiy bot uchun)
SHORT_CODE = os.getenv("SHORT_CODE", "055531010012")

OPENBUDGET_BASE_URL = os.getenv("OPENBUDGET_BASE_URL", "https://new.openbudget.uz")

TARGET_INITIATIVE_URL = f"{OPENBUDGET_BASE_URL}/uz/initiative-budget/active-initiatives/{BOARD_ID}/{INITIATIVE_ID}"
OFFICIAL_BOT_URL = f"https://t.me/OchiqBudjetUzBot?start={SHORT_CODE}"
