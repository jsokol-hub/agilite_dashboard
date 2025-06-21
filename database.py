import pandas as pd
from sqlalchemy import create_engine, text
from config import DATABASE_URL, PRODUCTS_TABLE, SCRAPING_SESSIONS_TABLE
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.connection = None

    def connect(self):
        """Establish connection to the PostgreSQL database."""
        if self.connection and not self.connection.closed:
            return True
        try:
            self.engine = create_engine(DATABASE_URL)
            self.connection = self.engine.connect()
            logger.info("Successfully connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            return False

    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connection closed")

    def execute_query(self, query, params=None):
        """Execute a query and return the results."""
        try:
            if not self.connect():
                raise Exception("Database not connected")
            return self.connection.execute(text(query), params)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            self.connection.rollback()
            raise

    def get_latest_products(self):
        """
        Get the 100 most recent products. A simple and reliable query.
        """
        try:
            query = f"SELECT * FROM {PRODUCTS_TABLE} ORDER BY processing_timestamp DESC LIMIT 100;"
            df = pd.read_sql(query, self.engine)
            logger.info(f"Loaded {len(df)} latest products.")
            return df
        except Exception as e:
            logger.error(f"Error in get_latest_products: {e}")
            return pd.DataFrame()

    def get_stock_history_raw_data(self):
        """
        Get raw data needed for history charts. The aggregation will be done in Python.
        """
        try:
            query = f"SELECT processing_timestamp, stock_status, category FROM {PRODUCTS_TABLE} WHERE category IS NOT NULL;"
            df = pd.read_sql(query, self.engine)
            logger.info(f"Fetched {len(df)} raw records for stock history.")
            return df
        except Exception as e:
            logger.error(f"Error in get_stock_history_raw_data: {e}")
            return pd.DataFrame()

    def get_latest_scraping_session(self):
        """Get the most recent scraping session from the database."""
        try:
            query = f"SELECT * FROM {SCRAPING_SESSIONS_TABLE} ORDER BY session_start DESC LIMIT 1;"
            result = self.execute_query(query)
            session = result.mappings().first()
            if session:
                return dict(session)
            return {}
        except Exception as e:
            logger.error(f"Error loading latest scraping session: {e}")
            return {}

    def get_product_changelog(self):
        """
        Retrieves the complete history of all products to identify changes
        in stock status over time. This is used to calculate demand.
        """
        try:
            # Using title as the identifier. A stable product_id would be ideal.
            query = f"""
            SELECT 
                title, 
                url,
                category,
                stock_status, 
                processing_timestamp 
            FROM {PRODUCTS_TABLE}
            ORDER BY title, processing_timestamp;
            """
            df = pd.read_sql(query, self.engine)
            logger.info(f"Fetched {len(df)} records for product changelog analysis.")
            return df
        except Exception as e:
            logger.error(f"Error in get_product_changelog: {e}")
            return pd.DataFrame()

# Global database manager instance
db_manager = DatabaseManager() 