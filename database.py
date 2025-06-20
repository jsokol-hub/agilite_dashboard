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
        """Establish connection to PostgreSQL database"""
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
        """Close database connection"""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connection closed")

    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        try:
            if not self.connect():
                raise Exception("Database not connected")
            return self.connection.execute(text(query), params)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            # In case of a failed query, the transaction is rolled back.
            self.connection.rollback()
            raise

    def get_latest_products(self):
        """Get products from the most recent completed scraping session."""
        try:
            session_query = f"""
            SELECT session_start, session_end
            FROM {SCRAPING_SESSIONS_TABLE}
            WHERE status ILIKE 'completed'
            ORDER BY session_start DESC
            LIMIT 1;
            """
            latest_session_result = self.execute_query(session_query)
            latest_session = latest_session_result.mappings().first()

            if not latest_session:
                logger.warning("No completed scraping session found.")
                return pd.DataFrame()

            start_ts = latest_session['session_start']
            end_ts = latest_session['session_end']
            
            # If for some reason the completed session has no end time, we'll avoid an error.
            if not start_ts or not end_ts:
                 logger.error("Latest completed session is missing start or end time.")
                 return pd.DataFrame()

            query = f"""
            SELECT p.*
            FROM {PRODUCTS_TABLE} p
            WHERE p.processing_timestamp >= %(start)s AND p.processing_timestamp <= %(end)s;
            """
            params = {'start': start_ts, 'end': end_ts}

            df = pd.read_sql(query, self.engine, params=params)
            logger.info(f"Loaded {len(df)} products from latest completed session ({start_ts} to {end_ts}).")
            return df
        except Exception as e:
            logger.error(f"Error loading latest products: {e}")
            return pd.DataFrame()

    def get_stock_history(self):
        """
        Generate stock history by aggregating product data for each completed scraping session.
        """
        try:
            query = f"""
            WITH category_counts_per_session AS (
                SELECT
                    ss.id as session_id,
                    p.category,
                    COUNT(p.id) as count
                FROM
                    {SCRAPING_SESSIONS_TABLE} ss
                JOIN
                    {PRODUCTS_TABLE} p ON p.processing_timestamp >= ss.session_start AND p.processing_timestamp <= ss.session_end
                WHERE
                    ss.status ILIKE 'completed' AND p.stock_status = 'In Stock' AND p.category IS NOT NULL
                GROUP BY
                    ss.id, p.category
            ),
            session_aggregates AS (
                SELECT
                    session_id,
                    json_object_agg(category, count) as category_counts,
                    SUM(count) as total_in_stock
                FROM category_counts_per_session
                GROUP BY session_id
            )
            SELECT
                ss.session_start as date,
                sa.total_in_stock as in_stock,
                sa.category_counts
            FROM
                {SCRAPING_SESSIONS_TABLE} ss
            JOIN
                session_aggregates sa ON ss.id = sa.session_id
            WHERE
                ss.status ILIKE 'completed'
            ORDER BY
                ss.session_start;
            """
            df = pd.read_sql(query, self.engine)

            history = df.to_dict('records')
            logger.info(f"Generated {len(history)} session-based stock history records.")
            return history
        except Exception as e:
            logger.error(f"Error generating stock history: {e}")
            return []

    def get_latest_scraping_session(self):
        """Get the most recent scraping session from the database."""
        try:
            query = f"""
            SELECT *
            FROM {SCRAPING_SESSIONS_TABLE}
            ORDER BY session_start DESC
            LIMIT 1;
            """
            result = self.execute_query(query)
            session = result.mappings().first() # .mappings() allows dict-like access

            if session:
                logger.info(f"Loaded latest scraping session: {session['id']}")
                return dict(session)
            return {}
        except Exception as e:
            logger.error(f"Error loading latest scraping session: {e}")
            return {}

# Global database manager instance
db_manager = DatabaseManager() 