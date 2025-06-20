import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration for the scraper's data
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'gis'),  # Default to 'gis' as seen in logs
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'schema': os.getenv('DB_SCHEMA', 'agilite') # Schema used by the scraper
}

# Connection string for SQLAlchemy
DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# Table names with schema
# Assuming other tables might be needed later
PRODUCTS_TABLE = f"{DB_CONFIG['schema']}.products"
PRODUCT_IMAGES_TABLE = f"{DB_CONFIG['schema']}.product_images"
PRODUCT_VARIANTS_TABLE = f"{DB_CONFIG['schema']}.product_variants"
SCRAPING_SESSIONS_TABLE = f"{DB_CONFIG['schema']}.scraping_sessions" 