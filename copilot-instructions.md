# PyQuote - Stock Quote Updater

## Overview

PyQuote is a Python application that fetches intraday minute-level stock quotes from the yFinance API and stores them in a MySQL database. The application processes quotes in 7-day chunks to comply with yFinance's API limitations and automatically updates the stock's `lastUpdate` timestamp in the database.

## Instructions for GitHub Copilot

When working with this codebase, please follow these guidelines:

### Code Understanding

1. **Architecture**: The application uses a single `StockQuoteUpdater` class with a static list of ticker symbols. Each ticker is processed independently through the `_fetch_quotes()` method.

2. **Data Flow**:
   - User provides command-line arguments (password, log file path, optional days and debug mode)
   - StockQuoteUpdater connects to MySQL database
   - For each ticker in the `tickers` list:
     - Fetch stock ID from stocks table
     - Retrieve quote data from yFinance in 7-day chunks
     - Check if each quote exists in the database
     - Insert new quotes and skip duplicates
     - Update the stock's lastUpdate field
   - Log summary of inserted/skipped quotes
   - Disconnect from database

3. **API Constraints**: 
   - yFinance restricts 1-minute data to 8 days per request
   - Solution: Fetch data in 7-day chunks and loop through all chunks
   - The lookback is capped at 28 days (max 4 chunks)

4. **Database Operations**:
   - All database queries use parameterized queries for security
   - Connection is maintained throughout execution and closed in finally block
   - Timestamps are converted to datetime objects for database storage
   - Prices are formatted to 2 decimal places as strings

5. **Logging Strategy**:
   - INFO level: General flow and summary statistics
   - DEBUG level: Operation latency tracking (when `-i` flag is used)
   - Both console and file logging are enabled simultaneously

### When Modifying Code

1. **Adding New Methods**: Ensure they follow the naming convention `_method_name()` for private methods and include docstrings with parameter and return type documentation.

2. **Database Changes**: 
   - All database operations should include try/except blocks for `mysql.connector.Error`
   - Use parameterized queries with `%s` placeholders to prevent SQL injection
   - Always call `self.db_connection.commit()` after INSERT/UPDATE operations
   - Close cursors after use with `cursor.close()`

3. **Timing/Latency Code**:
   - Use `start_time = time.time()` at the beginning of a method
   - Use `elapsed_ms = (time.time() - start_time) * 1000` to get milliseconds
   - Log with `self.logger.debug(f"method_name latency: {elapsed_ms:.2f}ms")`

4. **Command-Line Arguments**:
   - Use `argparse.ArgumentParser` for all CLI argument parsing
   - Mark required arguments with `required=True`
   - Use both short (`-x`) and long (`--long-name`) option names
   - Provide helpful epilog with usage examples

5. **Error Handling**:
   - Database errors should be caught and logged, then re-raised
   - Invalid arguments should use `parser.error()` which automatically shows help
   - External API errors (yFinance) should be caught and logged
   - Never silently fail - always log before exiting

### Common Patterns in This Codebase

1. **Method Signature Pattern**:
   ```python
   def _method_name(self, param: Type) -> ReturnType:
       """
       Description of what method does.
       
       Args:
           param: Description of parameter
           
       Returns:
           Description of return value
       """
   ```

2. **Database Operation Pattern**:
   ```python
   start_time = time.time()
   try:
       cursor = self.db_connection.cursor()
       query = "SQL_QUERY"
       cursor.execute(query, (param,))
       result = cursor.fetchone()  # or fetchall()
       cursor.close()
       
       elapsed_ms = (time.time() - start_time) * 1000
       self.logger.debug(f"operation latency: {elapsed_ms:.2f}ms")
       
       return result
   except mysql.connector.Error as e:
       self.logger.error(f"Database error: {e}")
       raise
   ```

3. **Data Processing Pattern**:
   ```python
   for timestamp, row in data.iterrows():
       value = row['ColumnName']
       # Handle potential Series objects
       if hasattr(value, 'values'):
           value = value.values[0]
       processed_value = transform(value)
   ```

### Key Implementation Details

1. **yFinance Data Handling**: The Close price comes as a float and must be formatted to string. Handle potential Series objects with `hasattr(value, 'values')` check.

2. **Datetime Handling**: Convert yFinance index to Python datetime with `timestamp.to_pydatetime()`

3. **Connection Lifecycle**: Always use try/finally blocks to ensure `_disconnect_from_database()` is called.

4. **Price Storage**: Prices are stored as strings (varchar) not decimals, so format as `f"{float(price):.2f}"` before insertion.

### Files to Know

- `pyquote.py` - Main application file containing the StockQuoteUpdater class and main() entry point
- `requirements.txt` - Python dependencies (yfinance==1.0, mysql-connector-python==9.5.0)
- `test_pyquote.py` - Comprehensive pytest test suite with unit and integration tests
- `copilot-instructions.md` - This file

### Testing

The project includes a comprehensive test suite using pytest with the following coverage:

#### Test Structure

Tests are organized into logical test classes:

1. **TestStockQuoteUpdaterInit** - Initialization tests for various parameter combinations
2. **TestLogging** - Logging configuration at INFO and DEBUG levels
3. **TestDatabaseConnection** - Database connection/disconnection and error handling
4. **TestStockLookup** - Stock ID lookup with success and failure cases
5. **TestQuoteExists** - Quote existence checks
6. **TestInsertQuote** - Quote insertion with error handling
7. **TestUpdateStockLastUpdate** - Updates to stock lastUpdate field
8. **TestArgumentParsing** - Command-line argument parsing and validation
9. **TestFetchQuotes** - Quote fetching and processing with mocked yFinance data
10. **TestRun** - Main run() method lifecycle and exception handling
11. **TestPriceFormatting** - Price formatting to 2 decimal places
12. **TestDateRangeCalculation** - Date range calculation based on lookback days
13. **TestChunking** - Verification of 7-day chunking logic
14. **TestIntegration** - Integration tests with real database (automatically skips if DB unavailable)

#### Running Tests

```bash
# Run all tests
pytest test_pyquote.py -v

# Run specific test class
pytest test_pyquote.py::TestLogging -v

# Run specific test
pytest test_pyquote.py::TestArgumentParsing::test_main_with_required_args -v

# Run with coverage report
pytest test_pyquote.py --cov=pyquote --cov-report=html

# Run excluding integration tests
pytest test_pyquote.py -v -k "not TestIntegration"

# Run only integration tests
pytest test_pyquote.py::TestIntegration -v
```

#### Mocking Strategy

- **Database operations** - All database interactions are mocked using `unittest.mock.MagicMock` except in integration tests
- **yFinance API** - Mocked with pandas DataFrames containing test data
- **Command-line arguments** - Patched using `patch('sys.argv', [...])`
- **Time functions** - Can be mocked for testing timestamp-dependent code

#### Integration Tests

The TestIntegration class includes tests that run against the actual local MySQL database:

- Automatically detects if database is available on localhost:3306
- Skips gracefully if database is unavailable (no test failure)
- Tests actual connection, table verification, and disconnection
- Uses credentials: user='tinker', password='hammmekhcC>>200lbs', database='tinker'

#### Test Coverage Areas

**Unit Tests** cover:
- Class initialization with various parameter combinations
- Logging setup at different levels
- Database connection success and error scenarios
- Stock lookup (found, not found, error)
- Quote existence checking
- Quote insertion
- Stock lastUpdate field updates
- Command-line argument parsing and validation
- Price formatting
- Date range calculation
- 7-day chunking logic
- Exception handling in main run() method

**Integration Tests** verify:
- Actual database connectivity
- Stocks table existence and data
- Quotes table existence
- Connection lifecycle management

#### Best Practices for Test Modifications

1. **When adding new methods to StockQuoteUpdater**: Create corresponding test class following the naming pattern `Test<MethodName>`
2. **When adding database operations**: Include both success and error test cases with mocked connections
3. **When adding command-line arguments**: Add tests to TestArgumentParsing for both valid and invalid values
4. **When modifying database schema**: Update integration tests to verify new columns/tables
5. **Mock all external dependencies** - Database, API calls, file I/O (except in integration tests)
6. **Use tmp_path fixture** - For any tests that need to write files (like log files)
7. **Test boundary conditions** - Zero values, negative values, max values, empty results

#### Common Test Patterns

```python
# Database mock pattern
@patch('mysql.connector.connect')
def test_something(self, mock_connect, tmp_path):
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (expected_result,)
    mock_connection.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_connection
    
    updater = StockQuoteUpdater(password="test", log_file=str(tmp_path / "test.log"))
    updater.db_connection = mock_connection
    
    # Test code here

# yFinance mock pattern
@patch('yfinance.download')
def test_fetch_quotes(self, mock_yf_download, tmp_path):
    import pandas as pd
    dates = pd.date_range(start='2025-12-20', periods=10, freq='1min')
    mock_data = pd.DataFrame({'Close': [150.0 + i*0.1 for i in range(10)]}, index=dates)
    mock_yf_download.return_value = mock_data
    
    # Test code here

# Command-line argument pattern
@patch('sys.argv', ['pyquote.py', '-p', 'password', '-l', '/tmp/test.log'])
def test_args(self):
    from pyquote import main
    # Call main and verify behavior
```

---

## Requirements

- Python 3.x
- MySQL Server running locally on port 3306
- yFinance 1.0
- mysql-connector-python 9.5.0
- pytest 9.0.2 (for testing)

### Database Setup

The application requires:
- A MySQL database named `tinker`
- A user `tinker` with full privileges on the `tinker` database
- A `stocks` table with columns: `id` (int unsigned), `ticker` (varchar(45)), `lastUpdate` (datetime)
- A `quotes` table with columns: `stock` (int unsigned, foreign key), `price` (varchar(45)), `timestamp` (datetime)

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Command Format

```bash
python pyquote.py -p PASSWORD -l LOG_FILE [-d DAYS] [-i]
```

### Required Arguments

- `-p, --password PASSWORD` - Database password for the `tinker` user (REQUIRED)
- `-l, --log-file LOG_FILE` - Path to output log file (REQUIRED)

### Optional Arguments

- `-d, --days DAYS` - Number of days to look back for quotes (default: 28, max: 28)
- `-i, --info` - Enable DEBUG logging to track operation latency (default: disabled)

### Examples

#### Basic usage with default settings (28 days lookback)
```bash
python pyquote.py -p "hammmekhcC>>200lbs" -l /home/psteitz/stockUpdate.log
```

#### Custom lookback period (10 days)
```bash
python pyquote.py -p "hammmekhcC>>200lbs" -l /home/psteitz/stockUpdate.log -d 10
```

#### With DEBUG logging enabled
```bash
python pyquote.py -p "hammmekhcC>>200lbs" -l /home/psteitz/stockUpdate.log -i
```

#### Using long-form arguments
```bash
python pyquote.py --password "hammmekhcC>>200lbs" --log-file /var/log/quotes.log --days 20
```

#### Combination of short and long arguments
```bash
python pyquote.py -p "password" --log-file /home/user/quotes.log -d 15 -i
```

## Features

### Stock Processing

The application processes the following stocks:
AA, AAL, AAPL, ACET, ADBE, ADP, AMAT, AMD, AMZN, AXP, BABA, BAC, BKNG, C, CCL, CALA, CMCSA, COF, CRM, CSCO, CVX, CX, DAL, DIS, F, FOXA, GE, GS, HAL, HBAN, HD, IJK, INTC, JBLU, JD, JNJ, JPM, KHC, KO, LCID, LOW, LUV, M, MA, MNKD, MMM, MRK, MRNA, MS, MSFT, NFLX, NOK, NVDA, NXE, PBR, PCTY, PFE, PINS, PYPL, QCOM, QQQ, RIOT, RIVN, SABR, SBUX, SEDG, SFM, SHOP, SPY, SQQQ, T, TSLA, TSN, UAL, UBER, V, VGLT, VTI, VXX, WFC, XOMA, XRX, WMT, WRN, YELP, ZM

### Data Handling

- **Chunk Processing**: Fetches data in 7-day chunks to stay within yFinance's 8-day API limit
- **Duplicate Prevention**: Checks if a quote already exists before inserting, skipping duplicates
- **Last Update Tracking**: Automatically updates the `lastUpdate` field in the stocks table to the most recent quote timestamp
- **Price Format**: Stores prices as strings with 2 decimal places

### Logging

The application logs:
- Connection status and errors
- Processing summary for each stock (inserted/skipped counts)
- Overall execution summary
- Optional DEBUG logs for operation latency (when `-i` flag is used)

#### Log Format
```
2025-12-28 15:30:45,123 - INFO - Connected to MySQL database successfully.
2025-12-28 15:30:46,456 - INFO - Fetching quotes for AA...
2025-12-28 15:30:52,789 - INFO - AA: Inserted 150 quotes, Skipped 45 (already present)
```

#### DEBUG Logs (with `-i` flag)
```
2025-12-28 15:30:50,123 - DEBUG - _quote_exists latency: 2.34ms
2025-12-28 15:30:50,125 - DEBUG - _insert_quote latency: 3.45ms
2025-12-28 15:30:52,789 - DEBUG - _fetch_quotes latency for AA: 6500.12ms
```

## API Limitations

- yFinance allows a maximum of 8 days of 1-minute granularity data per request
- For safety, the application is limited to a maximum of 28 days lookback
- Requesting more than 28 days will result in an error

## Error Handling

The application will:
- Exit with an error if a required argument is missing (missing `-p` or `-l`)
- Exit with an error if a stock ticker is not found in the database and is not a valid yFinance ticker
- Automatically insert new stock records for valid tickers not yet in the database
- Log database connection errors and continue attempting to process other stocks (depending on error type)
- Display validation errors for invalid argument values

Example error messages:
```
Error: days must be a positive integer
Error: days must be less than or equal to 28
Invalid ticker 'XYZ': not found in yFinance API
```

## Troubleshooting

### "Data too long for column 'price'"
- Ensure the `price` column in the `quotes` table is at least `varchar(45)`
- Prices are formatted to 2 decimal places

### "unsupported format string passed to Series.__format__"
- This indicates an issue with yFinance data processing
- Check that yFinance version 1.0 is installed correctly

### "Yahoo error = '1m data not available'"
- The requested date range exceeds yFinance's 8-day limit for 1-minute data
- The application automatically handles this by fetching in 7-day chunks
- If this error persists, check your internet connection and yFinance API status

### Connection Refused on Port 3306
- Ensure MySQL server is running locally
- Verify the database credentials are correct
- Check that the `tinker` user has proper permissions on the `tinker` database

## Performance Tips

1. Run during off-market hours to avoid high API load
2. Use shorter lookback periods (e.g., `-d 7`) for frequent updates
3. Enable DEBUG logging (`-i`) only when troubleshooting, as it adds overhead
4. Consider batching multiple runs with different lookback periods

## Development Notes

### Class Structure

The `StockQuoteUpdater` class is the main component with the following key methods:

- `__init__()` - Initialize with lookback days, password, log file, and debug mode
- `run()` - Main execution method that orchestrates the entire update process
- `_fetch_quotes()` - Fetch and process quotes for a single ticker
- `_quote_exists()` - Check if a quote already exists in the database
- `_insert_quote()` - Insert a new quote into the database
- `_update_stock_last_update()` - Update the stock's lastUpdate timestamp
- `_connect_to_database()` - Establish MySQL connection
- `_disconnect_from_database()` - Close MySQL connection
- `_setup_logging()` - Configure logging to file and console

### Static Members

- `tickers` - List of stock symbols to process (currently 75 stocks)

## License

This project is licensed under the Apache License 2.0. See below for the full license text.

### Apache License 2.0

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright [2025] [PyQuote Contributors]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

#### Summary

You are free to:
- **Use** this software for any purpose
- **Copy** and distribute this software
- **Modify** this software and create derivative works

Under the conditions that you:
- Include a copy of the license and copyright notice
- State significant changes made to the software
- Provide a copy of the license with any distribution

This is a permissive license with minimal restrictions. Commercial use is permitted.

For more information, visit: https://opensource.org/licenses/Apache-2.0
