# scraper.py
# This script fetches live data from the NSE website using a library,
# and then stores it in your PostgreSQL database.

import os
import psycopg2
from stock_nse_india import Nse
from dotenv import load_dotenv

# Load environment variables (useful for local testing, Render uses its own system)
load_dotenv()

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        # Render provides the database URL in an environment variable
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        print("Database connection successful.")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

def setup_database(conn):
    """Creates the necessary tables in the database if they don't already exist."""
    with conn.cursor() as cur:
        # Table for NIFTY, SENSEX, etc.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS indices (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                current_value NUMERIC(12, 2),
                change NUMERIC(12, 2),
                percent_change NUMERIC(5, 2),
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Table for Top Gainers and Top Losers
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_movers (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(50) NOT NULL,
                price NUMERIC(12, 2),
                percent_change NUMERIC(5, 2),
                mover_type VARCHAR(10) NOT NULL, -- 'GAINER' or 'LOSER'
                UNIQUE (ticker, mover_type)
            );
        """)
        # Table for Sectoral Performance
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sectoral_performance (
                id SERIAL PRIMARY KEY,
                sector_name VARCHAR(100) UNIQUE NOT NULL,
                percent_change NUMERIC(5, 2),
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Table for Volume Shockers
        cur.execute("""
            CREATE TABLE IF NOT EXISTS volume_shockers (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(50) UNIQUE NOT NULL,
                volume_change_percent NUMERIC(10, 2),
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()
    print("Database tables are set up.")

def update_data(conn, nse):
    """Fetches all data and updates the database."""
    with conn.cursor() as cur:
        print("Fetching and updating data...")

        # 1. Update Market Movers (Gainers & Losers)
        try:
            top_gainers = nse.get_top_gainers()
            for gainer in top_gainers[:5]: # Get top 5
                cur.execute("""
                    INSERT INTO market_movers (ticker, price, percent_change, mover_type)
                    VALUES (%s, %s, %s, 'GAINER')
                    ON CONFLICT (ticker, mover_type) DO UPDATE
                    SET price = EXCLUDED.price, percent_change = EXCLUDED.percent_change;
                """, (gainer['symbol'], gainer['lastPrice'], gainer['pChange']))
            
            top_losers = nse.get_top_losers()
            for loser in top_losers[:5]: # Get top 5
                cur.execute("""
                    INSERT INTO market_movers (ticker, price, percent_change, mover_type)
                    VALUES (%s, %s, %s, 'LOSER')
                    ON CONFLICT (ticker, mover_type) DO UPDATE
                    SET price = EXCLUDED.price, percent_change = EXCLUDED.percent_change;
                """, (loser['symbol'], loser['lastPrice'], loser['pChange']))
            print("- Market Movers updated.")
        except Exception as e:
            print(f"Error updating Market Movers: {e}")

        # 2. Update Sectoral Performance
        try:
            sector_data = nse.get_sectoral_indices()
            for sector, data in sector_data.items():
                cur.execute("""
                    INSERT INTO sectoral_performance (sector_name, percent_change)
                    VALUES (%s, %s)
                    ON CONFLICT (sector_name) DO UPDATE
                    SET percent_change = EXCLUDED.percent_change, last_updated = CURRENT_TIMESTAMP;
                """, (sector, data['pChange']))
            print("- Sectoral Performance updated.")
        except Exception as e:
            print(f"Error updating Sectoral Performance: {e}")

    conn.commit()
    print("All data updates committed.")


# --- Main execution block ---
if __name__ == "__main__":
    print("Starting data scraper script...")
    
    # Initialize the NSE library
    nse = Nse()
    
    # Get database connection
    connection = get_db_connection()
    
    if connection:
        try:
            # First, ensure the database schema is ready
            setup_database(connection)
            
            # Fetch the latest data and update the database
            update_data(connection, nse)
            
            print("Script finished successfully.")
            
        except Exception as e:
            print(f"A critical error occurred: {e}")
        finally:
            # Always make sure to close the connection
            connection.close()
            print("Database connection closed.")


