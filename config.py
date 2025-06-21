import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- Database Configuration ---
# Construct the database URL from environment variables.
# This follows the format: postgresql://user:password@host:port/dbname
DB_USER = os.environ.get("DB_USER", "default_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "default_password")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "default_db")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "agilite")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Table Names ---
# Define table names using the specified schema to avoid ambiguity.
PRODUCTS_TABLE = f"{DB_SCHEMA}.products"
SCRAPING_SESSIONS_TABLE = f"{DB_SCHEMA}.scraping_sessions"

# --- Dash Application Settings ---
DASH_DEBUG = os.environ.get("DASH_DEBUG", "True").lower() in ("true", "1", "t")

# --- Database Connection Test ---
# This dictionary is used by test_connection.py to verify settings.
DB_CONFIG = {
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT,
    'dbname': DB_NAME,
    'schema': DB_SCHEMA
}

# Table names with schema
# Assuming other tables might be needed later
PRODUCT_IMAGES_TABLE = f"{DB_CONFIG['schema']}.product_images"
PRODUCT_VARIANTS_TABLE = f"{DB_CONFIG['schema']}.product_variants" 