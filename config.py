import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HIGGSFIELD_API_KEY = os.getenv("HIGGSFIELD_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql://")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "550421233"))

# Relay для сервисов, у которых нет прямого доступа к api.telegram.org (например VPS в РФ)
RELAY_SECRET = os.getenv("RELAY_SECRET", "")
SOLVA_TELEGRAM_BOT_TOKEN = os.getenv("SOLVA_TELEGRAM_BOT_TOKEN", "")
