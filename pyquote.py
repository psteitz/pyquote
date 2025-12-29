#!/usr/bin/env python3
"""
Stock quote updater using yFinance API and MySQL database.
Retrieves intraday minute quotes for stocks and stores them in a database.
"""

import sys
import logging
import argparse
import time
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf
import mysql.connector


class StockQuoteUpdater:
    """Class to fetch and store stock quotes from yFinance to MySQL database."""
    
    # Static list of ticker symbols to fetch quotes for
    tickers = [ "AA", "AAL", "AAPL", "ACET", "ADBE", "ADP", "AMAT", "AMD", "AMZN","ARM", "AVGO", "AXP",
        "BABA", "BAC", "BKNG", "C", "CCL", "CALA", "CAT", "CMCSA", "COF", "CRM", "CSCO", "CVX", "CX",
        "DAL", "DIS", "F", "FOXA", "GE", "GS", "HAL", "HBAN", "HD","IBM", "IJK", "INTC", "JBLU", "JD", "JNJ", "JPM",
        "KHC", "KO", "LCID", "LITE", "LOW", "LUV", "M", "MA", "MNKD", "MMM", "MRK", "MRNA", "MS", "MSFT","MU",
        "NFLX", "NKE", "NOK", "NOW", "NVDA", "NXE", "PBR", "PCTY","PEP", "PFE", "PINS","PLTR", "PYPL", "QCOM", "QQQ",
        "RIOT", "RIVN", "RPGL", "SABR", "SBUX", "SEDG", "SFM", "SHOP", "SIDU", "SPGI", "SPY", "SQQQ", "T","TGT", "TSLA","TSM",
        "TSN", "UAL", "UNH", "UBER", "V", "VGLT", "VTI", "VXX", "WFC", "XOM", "XOMA", "XRX", "WMT", "WRN", "YELP", "ZM"]
    
    def __init__(self, lookback_days: int = 28, password: str = None, log_file: str = None, debug_mode: bool = False):
        """
        Initialize the StockQuoteUpdater.
        
        Args:
            lookback_days: Number of days to look back for quotes (default: 28)
            password: Database password (required)
            log_file: Path to log file (required)
            debug_mode: Enable DEBUG logging (default: False)
        """
        self.lookback_days = lookback_days
        self.db_password = password
        self.log_file = log_file
        self.debug_mode = debug_mode
        self.logger = self._setup_logging()
        self.db_connection = None
        self.quotes_inserted = {}
        self.quotes_skipped = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        log_level = logging.DEBUG if self.debug_mode else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def _connect_to_database(self) -> None:
        """Connect to the MySQL database."""
        try:
            self.db_connection = mysql.connector.connect(
                host='localhost',
                port=3306,
                user='tinker',
                password=self.db_password,
                database='tinker'
            )
            self.logger.info("Connected to MySQL database successfully.")
        except mysql.connector.Error as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _disconnect_from_database(self) -> None:
        """Disconnect from the MySQL database."""
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            self.logger.info("Disconnected from MySQL database.")
    
    def _get_stock_id(self, ticker: str) -> int:
        """
        Look up stock ID by ticker symbol. If not found, validates ticker with yFinance,
        retrieves the company name, and inserts a new record if valid.
        
        Args:
            ticker: The stock ticker symbol
            
        Returns:
            The stock ID
            
        Raises:
            Exception: If stock is not found and ticker is invalid
        """
        try:
            cursor = self.db_connection.cursor()
            query = "SELECT id FROM stocks WHERE ticker = %s"
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()
            
            if result is not None:
                cursor.close()
                return result[0]
            
            # Stock not in database, validate ticker with yFinance
            self.logger.debug(f"Validating ticker '{ticker}' with yFinance API")
            stock_data = yf.Ticker(ticker)
            
            # Check if ticker is valid by attempting to fetch info
            if stock_data.info is None or stock_data.info.get('symbol') is None:
                cursor.close()
                raise Exception(f"Invalid ticker '{ticker}': not found in yFinance API")
            
            # Retrieve company name from yFinance info
            company_name = stock_data.info.get('longName', ticker)
            self.logger.debug(f"Retrieved company name for '{ticker}': {company_name}")
            
            # Insert new stock record with ticker and company name
            insert_query = "INSERT INTO stocks (ticker, name) VALUES (%s, %s)"
            cursor.execute(insert_query, (ticker, company_name))
            self.db_connection.commit()
            
            new_id = cursor.lastrowid
            cursor.close()
            self.logger.info(f"Inserted new stock record for ticker '{ticker}' (name: {company_name}) with ID {new_id}")
            
            return new_id
            
        except mysql.connector.Error as e:
            self.logger.error(f"Database error while processing stock {ticker}: {e}")
            raise
    
    def _quote_exists(self, stock_id: int, timestamp: datetime) -> bool:
        """
        Check if a quote already exists for the given stock and timestamp.
        
        Args:
            stock_id: The stock ID
            timestamp: The quote timestamp
            
        Returns:
            True if quote exists, False otherwise
        """
        start_time = time.time()
        try:
            cursor = self.db_connection.cursor()
            query = "SELECT id FROM quotes WHERE stock = %s AND timestamp = %s"
            cursor.execute(query, (stock_id, timestamp))
            result = cursor.fetchone()
            cursor.close()
            
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.debug(f"_quote_exists latency: {elapsed_ms:.2f}ms")
            
            return result is not None
        except mysql.connector.Error as e:
            self.logger.error(f"Database error while checking quote existence: {e}")
            raise
    
    def _insert_quote(self, stock_id: int, price: str, timestamp: datetime) -> None:
        """
        Insert a new quote into the database.
        
        Args:
            stock_id: The stock ID
            price: The quote price as a string
            timestamp: The quote timestamp
        """
        start_time = time.time()
        try:
            cursor = self.db_connection.cursor()
            query = "INSERT INTO quotes (stock, price, timestamp) VALUES (%s, %s, %s)"
            cursor.execute(query, (stock_id, price, timestamp))
            self.db_connection.commit()
            cursor.close()
            
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.debug(f"_insert_quote latency: {elapsed_ms:.2f}ms")
        except mysql.connector.Error as e:
            self.logger.error(f"Database error while inserting quote: {e}")
            raise
    
    def _update_stock_last_update(self, stock_id: int) -> None:
        """
        Update the lastUpdate field in stocks table to the most recent quote timestamp.
        
        Args:
            stock_id: The stock ID
        """
        start_time = time.time()
        try:
            cursor = self.db_connection.cursor()
            # Get the most recent quote timestamp for this stock
            query = "SELECT MAX(timestamp) FROM quotes WHERE stock = %s"
            cursor.execute(query, (stock_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0] is not None:
                max_timestamp = result[0]
                # Update the lastUpdate field in stocks table
                cursor = self.db_connection.cursor()
                update_query = "UPDATE stocks SET lastUpdate = %s WHERE id = %s"
                cursor.execute(update_query, (max_timestamp, stock_id))
                self.db_connection.commit()
                cursor.close()
            
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.debug(f"_update_stock_last_update latency: {elapsed_ms:.2f}ms")
        except mysql.connector.Error as e:
            self.logger.error(f"Database error while updating stock lastUpdate: {e}")
            raise
    
    def _fetch_quotes(self, ticker: str) -> None:
        """
        Fetch and process quotes for a single stock ticker in 7-day chunks.
        
        Args:
            ticker: The stock ticker symbol
        """
        method_start = time.time()
        try:
            self.logger.info(f"Fetching quotes for {ticker}...")
            
            # Get stock ID from database
            stock_id = self._get_stock_id(ticker)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            inserted_count = 0
            skipped_count = 0
            
            # Fetch data in 7-day chunks
            current_start = start_date
            chunk_size = 7
            
            while current_start < end_date:
                current_end = min(current_start + timedelta(days=chunk_size), end_date)
                
                self.logger.debug(f"Fetching {ticker} from {current_start.date()} to {current_end.date()}")
                
                # Fetch intraday minute quotes for this chunk
                data = yf.download(ticker, start=current_start, end=current_end, interval='1m', progress=False)
                
                if not data.empty:
                    # Process each minute's data
                    for timestamp, row in data.iterrows():
                        quote_timestamp = timestamp.to_pydatetime()
                        close_price = row['Close']
                        # Handle case where Close might be a Series
                        if hasattr(close_price, 'values'):
                            close_price = close_price.values[0]
                        price = f"{float(close_price):.2f}"
                        
                        # Check if quote already exists
                        if self._quote_exists(stock_id, quote_timestamp):
                            skipped_count += 1
                        else:
                            self._insert_quote(stock_id, price, quote_timestamp)
                            inserted_count += 1
                
                # Move to next chunk
                current_start = current_end
            
            self.quotes_inserted[ticker] = inserted_count
            self.quotes_skipped[ticker] = skipped_count
            
            # Update the lastUpdate field for this stock
            self._update_stock_last_update(stock_id)
            
            elapsed_ms = (time.time() - method_start) * 1000
            self.logger.debug(f"_fetch_quotes latency for {ticker}: {elapsed_ms:.2f}ms")
            self.logger.info(f"{ticker}: Inserted {inserted_count} quotes, Skipped {skipped_count} (already present)")
            
        except Exception as e:
            self.logger.error(f"Error processing ticker {ticker}: {e}")
            raise
    
    def run(self) -> None:
        """Main execution method to fetch and store all stock quotes."""
        try:
            self._connect_to_database()
            
            self.logger.info(f"Starting stock quote update with {self.lookback_days}-day lookback")
            
            # Process each ticker
            for ticker in self.tickers:
                self._fetch_quotes(ticker)
            
            # Log summary
            self.logger.info("=" * 50)
            self.logger.info("Stock Update Summary")
            self.logger.info("=" * 50)
            for ticker in self.tickers:
                inserted = self.quotes_inserted.get(ticker, 0)
                skipped = self.quotes_skipped.get(ticker, 0)
                self.logger.info(f"{ticker}: {inserted} inserted, {skipped} skipped")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"Fatal error during stock update: {e}")
            sys.exit(1)
        finally:
            self._disconnect_from_database()


def main():
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description='Fetch and store stock quotes from yFinance to MySQL database',
        usage='%(prog)s [-h] [-d DAYS] -p PASSWORD -l LOG_FILE [-i]',
        epilog='''
Examples:
  %(prog)s -p "mypassword" -l /home/user/quotes.log
  %(prog)s --password "mypassword" --log-file /var/log/quotes.log --days 28
  %(prog)s -p "mypassword" -l /tmp/stock.log -d 10 -i
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-d', '--days',
        type=int,
        default=28,
        help='Number of days to look back for quotes (default: 28, max: 28)'
    )
    parser.add_argument(
        '-p', '--password',
        type=str,
        required=True,
        help='Database password (REQUIRED)'
    )
    parser.add_argument(
        '-l', '--log-file',
        type=str,
        required=True,
        help='Path to log file (REQUIRED)'
    )
    parser.add_argument(
        '-i', '--info',
        action='store_true',
        help='Enable DEBUG logging to track latency of database operations'
    )
    
    args = parser.parse_args()
    
    # Validate days argument
    if args.days <= 0:
        parser.error("Error: days must be a positive integer")
    
    if args.days > 28:
        parser.error("Error: days must be less than or equal to 28")
    
    updater = StockQuoteUpdater(lookback_days=args.days, password=args.password, log_file=args.log_file, debug_mode=args.info)
    updater.run()


if __name__ == '__main__':
    main()
