#!/usr/bin/env python3
"""
Test script for database connection to the scraper's database.
"""
import sys
from database import db_manager
from config import DB_CONFIG, PRODUCTS_TABLE
import psycopg2

def test_db_connection():
    """
    Tests the connection to the PostgreSQL database using the credentials
    from the config module.
    """
    try:
        print("Attempting to connect to the database...")
        conn = psycopg2.connect(
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port']
        )
        print("Database connection successful!")
        
        # Check if the 'agilite' schema exists
        cur = conn.cursor()
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'agilite';")
        if cur.fetchone():
            print("Schema 'agilite' found.")
        else:
            print("Warning: Schema 'agilite' not found.")
            
        cur.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}")
        print("\nPlease check your .env file and ensure the database is running and accessible.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def test_connection():
    """Test database connection and check for necessary tables."""
    print("Testing database connection...")
    print(f"Host: {DB_CONFIG['host']}")
    print(f"Port: {DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Schema: {DB_CONFIG['schema']}")
    print("-" * 50)
    
    try:
        if not db_manager.connect():
            print("❌ Database connection failed!")
            return False
            
        print("✅ Database connection successful!")
        
        # Test basic query
        try:
            result = db_manager.execute_query("SELECT version();")
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL version: {version.split(',')[0]}")
        except Exception as e:
            print(f"❌ Error executing test query: {e}")
        
        # Test PostGIS extension
        try:
            result = db_manager.execute_query("SELECT PostGIS_Version();")
            postgis_version = result.fetchone()[0]
            print(f"✅ PostGIS version: {postgis_version}")
        except Exception:
            print("⚠️ PostGIS extension not found or not working.")
        
        # Check for products table
        try:
            result = db_manager.execute_query(f"SELECT 1 FROM {PRODUCTS_TABLE} LIMIT 1;")
            result.fetchone()
            print(f"✅ Successfully queried table: {PRODUCTS_TABLE}")
        except Exception:
            print(f"❌ Failed to query table: {PRODUCTS_TABLE}. Make sure it exists and the scraper has run.")
            return False
            
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False
    finally:
        db_manager.disconnect()
        
    return True

def test_data_operations():
    """Test that data-retrieval functions run and return expected data types."""
    print("\nTesting data operations...")
    print("-" * 50)
    success = True
    
    try:
        # Test getting latest products
        print("Testing get_latest_products()...")
        products_df = db_manager.get_latest_products()
        if products_df is not None and not products_df.empty:
            print(f"✅ OK: returned a DataFrame with {len(products_df)} records.")
        elif products_df is not None:
            print("ℹ️ OK: returned an empty DataFrame. The products table might be empty.")
        else:
            print("❌ FAILED: did not return a DataFrame.")
            success = False

        # Test getting stock history
        print("\nTesting get_stock_history()...")
        history = db_manager.get_stock_history()
        if isinstance(history, list) and history:
            print(f"✅ OK: returned a list with {len(history)} records.")
        elif isinstance(history, list):
            print("ℹ️ OK: returned an empty list. No historical data could be generated.")
        else:
            print("❌ FAILED: did not return a list.")
            success = False

        # Test getting price statistics
        print("\nTesting get_price_statistics()...")
        stats = db_manager.get_price_statistics()
        if isinstance(stats, dict) and stats:
            print(f"✅ OK: returned a dictionary with statistics: {stats}")
        elif isinstance(stats, dict):
            print("ℹ️ OK: returned an empty dictionary. The products table might be empty.")
        else:
            print("❌ FAILED: did not return a dictionary.")
            success = False
            
    except Exception as e:
        print(f"❌ An unexpected error occurred during data operations test: {e}")
        success = False
    finally:
        db_manager.disconnect()
        
    return success

if __name__ == "__main__":
    print("Agilite Dashboard - Database Connection Test")
    print("=" * 60)
    
    if test_connection():
        if test_data_operations():
            print("\n🎉 All tests passed! The dashboard should be able to connect and read data.")
        else:
            print("\n⚠️ Connection test passed, but data operations failed.")
            print("   Please check the logs above for errors. The tables might be empty or have an unexpected structure.")
    else:
        print("\n❌ Database connection failed!")
        print("   Please check your configuration in the .env file and ensure PostgreSQL is running and accessible.")
    
    print("\n" + "=" * 60) 