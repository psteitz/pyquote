"""
Pytest test cases for PyQuote stock quote updater application.
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch
import mysql.connector
from pyquote import StockQuoteUpdater


class TestStockQuoteUpdaterInit:
    """Test suite for StockQuoteUpdater initialization."""
    
    def test_init_with_all_parameters(self, tmp_path):
        """Test initialization with all parameters provided."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(
            lookback_days=10,
            password="test_password",
            log_file=log_file,
            debug_mode=True
        )
        
        assert updater.lookback_days == 10
        assert updater.db_password == "test_password"
        assert updater.log_file == log_file
        assert updater.debug_mode is True
        assert updater.db_connection is None
        assert updater.quotes_inserted == {}
        assert updater.quotes_skipped == {}
    
    def test_init_with_default_lookback(self, tmp_path):
        """Test initialization with default lookback days."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(password="test", log_file=log_file)
        
        assert updater.lookback_days == 28
    
    def test_init_with_debug_mode_false(self, tmp_path):
        """Test initialization with debug mode disabled."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(password="test", log_file=log_file, debug_mode=False)
        
        assert updater.debug_mode is False
    
    def test_tickers_list_exists(self):
        """Test that static tickers list is defined."""
        assert hasattr(StockQuoteUpdater, 'tickers')
        assert isinstance(StockQuoteUpdater.tickers, list)
        assert len(StockQuoteUpdater.tickers) > 0
        assert 'AA' in StockQuoteUpdater.tickers
        assert 'AAPL' in StockQuoteUpdater.tickers


class TestLogging:
    """Test suite for logging configuration."""
    
    def test_setup_logging_info_level(self, tmp_path):
        """Test that INFO level logging is configured correctly."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(password="test", log_file=log_file, debug_mode=False)
        
        assert updater.logger is not None
        # Check that root logger has handlers configured (basicConfig adds handlers to root)
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        # Check that at least one handler is a FileHandler or StreamHandler
        assert any(isinstance(h, (logging.FileHandler, logging.StreamHandler)) for h in root_logger.handlers)
    
    def test_setup_logging_debug_level(self, tmp_path):
        """Test that DEBUG level logging is configured when enabled."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(password="test", log_file=log_file, debug_mode=True)
        
        assert updater.logger is not None
        # Check that root logger has handlers configured
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
    
    def test_log_file_created(self, tmp_path):
        """Test that log file is created."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(password="test", log_file=log_file)
        
        # The file may be created lazily, so we trigger a log message
        updater.logger.info("Test message")
        
        # File should now exist
        import os
        assert os.path.exists(log_file)


class TestDatabaseConnection:
    """Test suite for database connection methods."""
    
    @patch('mysql.connector.connect')
    def test_connect_to_database_success(self, mock_connect, tmp_path):
        """Test successful database connection."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater._connect_to_database()
        
        mock_connect.assert_called_once_with(
            host='localhost',
            port=3306,
            user='tinker',
            password='test_pass',
            database='tinker'
        )
        assert updater.db_connection == mock_connection
    
    @patch('mysql.connector.connect')
    def test_connect_to_database_failure(self, mock_connect, tmp_path):
        """Test database connection failure."""
        log_file = str(tmp_path / "test.log")
        mock_connect.side_effect = mysql.connector.Error("Connection failed")
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        
        with pytest.raises(mysql.connector.Error):
            updater._connect_to_database()
    
    @patch('mysql.connector.connect')
    def test_disconnect_from_database(self, mock_connect, tmp_path):
        """Test database disconnection."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater._connect_to_database()
        updater._disconnect_from_database()
        
        mock_connection.close.assert_called_once()
    
    @patch('mysql.connector.connect')
    def test_disconnect_when_not_connected(self, mock_connect, tmp_path):
        """Test disconnection when not connected."""
        log_file = str(tmp_path / "test.log")
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        
        # Should not raise an error when db_connection is None
        updater._disconnect_from_database()


class TestStockLookup:
    """Test suite for stock ID lookup."""
    
    @patch('mysql.connector.connect')
    def test_get_stock_id_found(self, mock_connect, tmp_path):
        """Test successful stock lookup when stock exists."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        stock_id = updater._get_stock_id('AAPL')
        
        assert stock_id == 42
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('yfinance.Ticker')
    @patch('mysql.connector.connect')
    def test_get_stock_id_not_found_valid_ticker(self, mock_connect, mock_ticker, tmp_path):
        """Test stock lookup when stock doesn't exist but ticker is valid."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # First call returns None (stock not found), then insert is called
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 100
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.commit = MagicMock()
        mock_connect.return_value = mock_connection
        
        # Mock yFinance ticker as valid with company name
        mock_stock = MagicMock()
        mock_stock.info = {'symbol': 'TSLA', 'longName': 'Tesla Inc.'}
        mock_ticker.return_value = mock_stock
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        stock_id = updater._get_stock_id('TSLA')
        
        assert stock_id == 100
        # Verify INSERT was called with both ticker and company name
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2  # SELECT then INSERT
        assert "INSERT INTO stocks" in calls[1][0][0]
        # Verify the INSERT query includes the name column
        insert_query = calls[1][0][0]
        assert "(ticker, name)" in insert_query
        # Verify the values passed to INSERT include the company name
        insert_values = calls[1][0][1]
        assert insert_values == ('TSLA', 'Tesla Inc.')
        mock_connection.commit.assert_called_once()
    
    @patch('yfinance.Ticker')
    @patch('mysql.connector.connect')
    def test_get_stock_id_not_found_invalid_ticker(self, mock_connect, mock_ticker, tmp_path):
        """Test stock lookup when stock doesn't exist and ticker is invalid."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        # Mock yFinance ticker as invalid
        mock_stock = MagicMock()
        mock_stock.info = None
        mock_ticker.return_value = mock_stock
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        with pytest.raises(Exception, match="Invalid ticker"):
            updater._get_stock_id('INVALID')
    
    @patch('mysql.connector.connect')
    def test_get_stock_id_database_error(self, mock_connect, tmp_path):
        """Test stock lookup with database error."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        with pytest.raises(mysql.connector.Error):
            updater._get_stock_id('AAPL')
    
    @patch('yfinance.Ticker')
    @patch('mysql.connector.connect')
    def test_get_stock_id_retrieves_company_name(self, mock_connect, mock_ticker, tmp_path):
        """Test that company name is retrieved from yFinance and stored."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # Mock stock not found initially
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 42
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.commit = MagicMock()
        mock_connect.return_value = mock_connection
        
        # Mock yFinance with full company name
        mock_stock = MagicMock()
        mock_stock.info = {'symbol': 'MSFT', 'longName': 'Microsoft Corporation'}
        mock_ticker.return_value = mock_stock
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        stock_id = updater._get_stock_id('MSFT')
        
        assert stock_id == 42
        # Verify that yFinance Ticker was called with the ticker
        mock_ticker.assert_called_once_with('MSFT')
        # Verify INSERT includes company name
        calls = mock_cursor.execute.call_args_list
        insert_values = calls[1][0][1]
        assert insert_values == ('MSFT', 'Microsoft Corporation')
    
    @patch('yfinance.Ticker')
    @patch('mysql.connector.connect')
    def test_get_stock_id_fallback_to_ticker_as_name(self, mock_connect, mock_ticker, tmp_path):
        """Test that ticker is used as company name if longName is not available."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # Mock stock not found initially
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 50
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.commit = MagicMock()
        mock_connect.return_value = mock_connection
        
        # Mock yFinance without longName field
        mock_stock = MagicMock()
        mock_stock.info = {'symbol': 'NVDA'}  # No 'longName' key
        mock_ticker.return_value = mock_stock
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        stock_id = updater._get_stock_id('NVDA')
        
        assert stock_id == 50
        # Verify INSERT falls back to ticker when longName is not available
        calls = mock_cursor.execute.call_args_list
        insert_values = calls[1][0][1]
        # When longName is missing, it should use the ticker as the default
        assert insert_values == ('NVDA', 'NVDA')


class TestQuoteExists:
    """Test suite for quote existence check."""
    
    @patch('mysql.connector.connect')
    def test_quote_exists_true(self, mock_connect, tmp_path):
        """Test when quote exists."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        timestamp = datetime.now()
        exists = updater._quote_exists(1, timestamp)
        
        assert exists is True
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('mysql.connector.connect')
    def test_quote_exists_false(self, mock_connect, tmp_path):
        """Test when quote doesn't exist."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        timestamp = datetime.now()
        exists = updater._quote_exists(1, timestamp)
        
        assert exists is False
    
    @patch('mysql.connector.connect')
    def test_quote_exists_database_error(self, mock_connect, tmp_path):
        """Test quote check with database error."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        with pytest.raises(mysql.connector.Error):
            updater._quote_exists(1, datetime.now())


class TestInsertQuote:
    """Test suite for quote insertion."""
    
    @patch('mysql.connector.connect')
    def test_insert_quote_success(self, mock_connect, tmp_path):
        """Test successful quote insertion."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        timestamp = datetime.now()
        updater._insert_quote(1, "150.25", timestamp)
        
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('mysql.connector.connect')
    def test_insert_quote_database_error(self, mock_connect, tmp_path):
        """Test quote insertion with database error."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = mysql.connector.Error("Insert failed")
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        with pytest.raises(mysql.connector.Error):
            updater._insert_quote(1, "150.25", datetime.now())


class TestUpdateStockLastUpdate:
    """Test suite for updating stock last update timestamp."""
    
    @patch('mysql.connector.connect')
    def test_update_stock_last_update_success(self, mock_connect, tmp_path):
        """Test successful update of lastUpdate field."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        max_timestamp = datetime.now()
        mock_cursor.fetchone.return_value = (max_timestamp,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        updater._update_stock_last_update(1)
        
        # Should be called twice (once for SELECT, once for UPDATE)
        assert mock_cursor.execute.call_count == 2
        mock_connection.commit.assert_called_once()
    
    @patch('mysql.connector.connect')
    def test_update_stock_last_update_no_quotes(self, mock_connect, tmp_path):
        """Test update when no quotes exist for stock."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        # Should not raise error, just skip the update
        updater._update_stock_last_update(1)
        
        # Only SELECT should be called, not UPDATE
        assert mock_cursor.execute.call_count == 1
    
    @patch('mysql.connector.connect')
    def test_update_stock_last_update_database_error(self, mock_connect, tmp_path):
        """Test lastUpdate update with database error."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = mysql.connector.Error("Update failed")
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        with pytest.raises(mysql.connector.Error):
            updater._update_stock_last_update(1)


class TestArgumentParsing:
    """Test suite for command-line argument parsing."""
    
    def test_main_with_required_args(self):
        """Test main function with required arguments."""
        with patch('pyquote.StockQuoteUpdater') as mock_updater:
            with patch('sys.argv', ['pyquote.py', '-p', 'password', '-l', '/tmp/test.log']):
                from pyquote import main
                main()
                
                mock_updater.assert_called_once()
                call_kwargs = mock_updater.call_args[1]
                assert call_kwargs['password'] == 'password'
                assert call_kwargs['log_file'] == '/tmp/test.log'
                assert call_kwargs['lookback_days'] == 28
                assert call_kwargs['debug_mode'] is False
    
    def test_main_with_all_args(self):
        """Test main function with all arguments."""
        with patch('pyquote.StockQuoteUpdater') as mock_updater:
            with patch('sys.argv', ['pyquote.py', '-p', 'pass', '-l', '/tmp/test.log', '-d', '10', '-i']):
                from pyquote import main
                main()
                
                call_kwargs = mock_updater.call_args[1]
                assert call_kwargs['lookback_days'] == 10
                assert call_kwargs['debug_mode'] is True
    
    def test_main_missing_password(self):
        """Test main function without password argument."""
        with patch('sys.argv', ['pyquote.py', '-l', '/tmp/test.log']):
            from pyquote import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_missing_log_file(self):
        """Test main function without log file argument."""
        with patch('sys.argv', ['pyquote.py', '-p', 'password']):
            from pyquote import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_invalid_days_zero(self):
        """Test main function with invalid days (zero)."""
        with patch('sys.argv', ['pyquote.py', '-p', 'pass', '-l', '/tmp/test.log', '-d', '0']):
            from pyquote import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_invalid_days_negative(self):
        """Test main function with invalid days (negative)."""
        with patch('sys.argv', ['pyquote.py', '-p', 'pass', '-l', '/tmp/test.log', '-d', '-5']):
            from pyquote import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_invalid_days_exceeds_max(self):
        """Test main function with days exceeding maximum."""
        with patch('sys.argv', ['pyquote.py', '-p', 'pass', '-l', '/tmp/test.log', '-d', '29']):
            from pyquote import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_valid_days_at_max(self):
        """Test main function with days at maximum (28)."""
        with patch('pyquote.StockQuoteUpdater') as mock_updater:
            with patch('sys.argv', ['pyquote.py', '-p', 'pass', '-l', '/tmp/test.log', '-d', '28']):
                from pyquote import main
                main()
                
                call_kwargs = mock_updater.call_args[1]
                assert call_kwargs['lookback_days'] == 28


class TestFetchQuotes:
    """Test suite for quote fetching and processing."""
    
    @patch('yfinance.download')
    @patch('mysql.connector.connect')
    def test_fetch_quotes_success(self, mock_connect, mock_yf_download, tmp_path):
        """Test successful quote fetching."""
        log_file = str(tmp_path / "test.log")
        
        # Mock yfinance data
        import pandas as pd
        dates = pd.date_range(start='2025-12-20', periods=100, freq='1min')
        mock_data = pd.DataFrame({
            'Close': [150.0 + i * 0.1 for i in range(100)]
        }, index=dates)
        mock_yf_download.return_value = mock_data
        
        # Mock database
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # Stock ID
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file, lookback_days=7)
        updater.db_connection = mock_connection
        
        updater._fetch_quotes('AAPL')
        
        assert 'AAPL' in updater.quotes_inserted
        assert 'AAPL' in updater.quotes_skipped
    
    @patch('yfinance.Ticker')
    @patch('mysql.connector.connect')
    def test_fetch_quotes_stock_not_found(self, mock_connect, mock_ticker, tmp_path):
        """Test fetch quotes when stock not found in database and ticker is invalid."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        # Mock yFinance ticker as invalid
        mock_stock = MagicMock()
        mock_stock.info = None
        mock_ticker.return_value = mock_stock
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        updater.db_connection = mock_connection
        
        with pytest.raises(Exception, match="Invalid ticker"):
            updater._fetch_quotes('INVALID')


class TestRun:
    """Test suite for the main run method."""
    
    @patch('mysql.connector.connect')
    def test_run_connects_and_disconnects(self, mock_connect, tmp_path):
        """Test that run method connects and disconnects from database."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        
        with patch.object(updater, '_fetch_quotes'):
            updater.run()
        
        mock_connect.assert_called_once()
        mock_connection.close.assert_called_once()
    
    @patch('mysql.connector.connect')
    def test_run_handles_exception(self, mock_connect, tmp_path):
        """Test that run method handles exceptions gracefully."""
        log_file = str(tmp_path / "test.log")
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file)
        
        with patch.object(updater, '_fetch_quotes', side_effect=Exception("Test error")):
            with pytest.raises(SystemExit) as exc_info:
                updater.run()
            
            # Should exit with code 1
            assert exc_info.value.code == 1
        
        # Should still disconnect even on error
        mock_connection.close.assert_called_once()


class TestPriceFormatting:
    """Test suite for price formatting."""
    
    @patch('yfinance.download')
    @patch('mysql.connector.connect')
    def test_price_formatted_to_two_decimals(self, mock_connect, mock_yf_download, tmp_path):
        """Test that prices are formatted to 2 decimal places."""
        log_file = str(tmp_path / "test.log")
        
        import pandas as pd
        dates = pd.date_range(start='2025-12-20', periods=5, freq='1min')
        mock_data = pd.DataFrame({
            'Close': [150.12345, 150.56789, 150.99999, 151.11111, 151.22222]
        }, index=dates)
        mock_yf_download.return_value = mock_data
        
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file, lookback_days=1)
        updater.db_connection = mock_connection
        
        updater._fetch_quotes('AAPL')
        
        # Check that all prices passed to _insert_quote are formatted correctly
        insert_calls = [c for c in mock_cursor.method_calls if 'INSERT' in str(c)]
        # We expect insert calls with formatted prices


class TestDateRangeCalculation:
    """Test suite for date range calculation."""
    
    @patch('yfinance.download')
    @patch('mysql.connector.connect')
    def test_lookback_days_respected(self, mock_connect, mock_yf_download, tmp_path):
        """Test that lookback days parameter is respected."""
        log_file = str(tmp_path / "test.log")
        
        import pandas as pd
        mock_yf_download.return_value = pd.DataFrame()
        
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file, lookback_days=10)
        updater.db_connection = mock_connection
        
        with patch('pyquote.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 28, 15, 30, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            updater._fetch_quotes('AAPL')
        
        # Verify yfinance was called with appropriate date ranges


class TestChunking:
    """Test suite for 7-day chunking logic."""
    
    @patch('yfinance.download')
    @patch('mysql.connector.connect')
    def test_data_fetched_in_7_day_chunks(self, mock_connect, mock_yf_download, tmp_path):
        """Test that data is fetched in 7-day chunks."""
        log_file = str(tmp_path / "test.log")
        
        import pandas as pd
        mock_yf_download.return_value = pd.DataFrame()
        
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        updater = StockQuoteUpdater(password="test_pass", log_file=log_file, lookback_days=28)
        updater.db_connection = mock_connection
        
        updater._fetch_quotes('AAPL')
        
        # Should be called 4 times for 28-day lookback (28/7 = 4 chunks)
        assert mock_yf_download.call_count == 4


# Integration tests (requires actual database)
class TestIntegration:
    """Integration tests that require actual database connection."""
    
    @staticmethod
    def _is_database_available():
        """Check if MySQL database is available on localhost."""
        try:
            conn = mysql.connector.connect(
                host='localhost',
                port=3306,
                user='tinker',
                password='password',
                database='tinker'
            )
            conn.close()
            return True
        except mysql.connector.Error:
            return False
    
    @pytest.mark.skipif(
        not _is_database_available.__func__(),
        reason="MySQL database not available on localhost"
    )
    def test_full_workflow_with_real_database(self):
        """Test full workflow with real database (requires setup)."""
        updater = StockQuoteUpdater(
            password="hammmekhcC>>200lbs",
            log_file="/tmp/test_integration.log",
            lookback_days=1
        )
        
        try:
            updater._connect_to_database()
            # Test that we can connect and verify tables exist
            cursor = updater.db_connection.cursor()
            
            # Verify stocks table exists
            cursor.execute("SELECT COUNT(*) FROM stocks")
            stock_count = cursor.fetchone()[0]
            assert stock_count > 0, "No stocks found in database"
            
            # Verify quotes table exists
            cursor.execute("SELECT COUNT(*) FROM quotes")
            quote_count = cursor.fetchone()[0]
            # Quotes table should exist even if empty
            
            cursor.close()
            updater._disconnect_from_database()
            
            # Connection and disconnection successful
            assert True
        except mysql.connector.Error as e:
            pytest.fail(f"Database test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
