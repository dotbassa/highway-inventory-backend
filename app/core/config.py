import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Logging Configuration
LOG_DIR = os.getenv("LOG_DIR", "./logs")
LOG_FILE = os.getenv("LOG_FILE", "app.log")
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

# JWT Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# Photo Upload Configuration
MAX_PHOTOS_PER_REQUEST = int(os.getenv("MAX_PHOTOS_PER_REQUEST"))
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS")
MAX_PHOTO_FILE_SIZE = int(os.getenv("MAX_PHOTO_FILE_SIZE"))

# Directorios de uploads con valores por defecto
# En Docker usará /var/highway-inventory/uploads/...
# En desarrollo local usará ./uploads/...
ASSET_PHOTOS_DIR = os.getenv("ASSET_PHOTOS_DIR", "./uploads/asset_photos")
CONFLICTIVE_ASSET_PHOTOS_DIR = os.getenv(
    "CONFLICTIVE_ASSET_PHOTOS_DIR", "./uploads/conflictive_asset_photos"
)

# Resend Email Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "orgs_name Data")
