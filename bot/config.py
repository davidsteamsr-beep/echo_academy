import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")

# Supabase / Postgres. Example:
# postgresql+asyncpg://postgres.xxxx:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
# If empty — local SQLite fallback (dev only).
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Render / hosting
# BOT_MODE=polling  — local or simple Render (no public URL needed)
# BOT_MODE=webhook  — production on Render with HTTPS
BOT_MODE = os.getenv("BOT_MODE", "polling").strip().lower()
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "").strip().rstrip("/")  # https://your-app.onrender.com
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook").strip() or "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
PORT = int(os.getenv("PORT", "8080") or "8080")

INDIVIDUAL_PRICE = 90_000.0
GROUP_SEAT = 60_000.0
GROUP_SIZE = 3
