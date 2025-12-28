# PyQuote - Accumulates intraday stock quotes

A Python application that fetches intraday minute-level stock quotes from the yFinance API and stores them in a MySQL database. This application can be used to accumulate a historical database of minute quotes for a designated list of stocks.

## Features

✨ **Key Features:**

- 📊 Fetches intraday minute-level stock quotes for stocks provided in a static list
- 🔄 Automatically handles yFinance API limitations with 7-day chunking
- 💾 Stores quotes in MySQL tables
- 📝 Comprehensive logging with optional DEBUG mode for performance monitoring
- ⚙️ Flexible command-line interface with required and optional parameters
- 🔐 Secure database operations with parameterized queries
- 📈 Tracks stock update timestamps automatically
- 🧪 Comprehensive test suite with unit and integration tests

## Requirements

- Python 3.8+
- MySQL Server 5.7+ running locally on port 3306
- yFinance 1.0
- mysql-connector-python 9.5.0
- pytest 9.0+ (for running tests)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/pyquote.git
cd pyquote
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Database

Create a MySQL database and user with the following structure:

```sql
-- Create database
CREATE DATABASE tinker;

-- Create user with full privileges
CREATE USER 'tinker'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON tinker.* TO 'tinker'@'localhost';
FLUSH PRIVILEGES;

-- Replace 'password' with a real password.  
-- This needs to be supplied as a command-line argument.

-- Create tables
USE tinker;

CREATE TABLE stocks (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    ticker VARCHAR(45) UNIQUE NOT NULL,
    lastUpdate DATETIME
);

CREATE TABLE quotes (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    stock INT UNSIGNED NOT NULL,
    price VARCHAR(45) NOT NULL,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (stock) REFERENCES stocks(id),
    UNIQUE KEY unique_stock_timestamp (stock, timestamp)
);

-- Insert stocks to be tracked
-- These also need to go in the static 'tickers' list in the code
-- Note: You do not need to pre-populate the stocks table
-- The application will automatically validate and insert new stock tickers using yFinance
-- However, you can optionally pre-insert stocks if desired:
INSERT INTO stocks (ticker) VALUES 
('AAPL'), ('MSFT'), ('GOOGL'), ('AMZN'), ('TSLA'),
('META'), ('NVDA'), ('JPM'), ('V'), ('WMT');
-- ... add more stocks as needed
```

## Usage

### Basic Command Format

```bash
python pyquote.py [-h] [-d DAYS] -p PASSWORD -l LOG_FILE [-i]
```

### Required Arguments

- `-p, --password PASSWORD` - Database password for the `tinker` user
- `-l, --log-file LOG_FILE` - Path to output log file

### Optional Arguments

- `-d, --days DAYS` - Number of days to look back for quotes (default: 28, max: 28)
- `-i, --info` - Enable DEBUG logging to track operation latency

### Examples

**Fetch quotes for default 28 days:**
```bash
python pyquote.py -p "hammmekhcC>>200lbs" -l /home/user/stockUpdate.log
```

**Fetch quotes for 10 days with DEBUG logging:**
```bash
python pyquote.py -p "hammmekhcC>>200lbs" -l /var/log/quotes.log -d 10 -i
```

**Using long-form arguments:**
```bash
python pyquote.py --password "mypassword" --log-file /tmp/quotes.log --days 15
```

**Schedule with cron (daily at 8 PM):**
```bash
0 20 * * * cd /home/psteitz/pyquote && source .venv/bin/activate && python pyquote.py -p "hammmekhcC>>200lbs" -l /home/psteitz/stockUpdate.log -d 7
```

## Architecture

### Class Structure

The application uses a single `StockQuoteUpdater` class with the following methods:

- `__init()` - Initialize with configuration
- `run()` - Main execution orchestrator
- `_fetch_quotes()` - Fetch and process quotes in 7-day chunks
- `_get_stock_id()` - Look up stock by ticker; auto-validates and inserts new stocks
- `_quote_exists()` - Check for duplicate quotes
- `_insert_quote()` - Store quote in database
- `_update_stock_last_update()` - Update stock metadata
- `_connect_to_database()` - Establish MySQL connection
- `_disconnect_from_database()` - Close connection
- `_setup_logging()` - Configure logging

### Data Flow

```
Command-line Arguments
        ↓
StockQuoteUpdater Initialization
        ↓
Database Connection
        ↓
For each stock ticker:
  ├─ Check if stock exists in database
  ├─ If not found, validate ticker with yFinance API
  ├─ If valid, insert new stock record
  ├─ Fetch quotes in 7-day chunks from yFinance
  ├─ Check for duplicate quotes
  ├─ Insert new quotes
  └─ Update stock's lastUpdate timestamp
        ↓
Log Summary Statistics
        ↓
Database Disconnection
```

## Testing

### Running Tests

```bash
# Run all tests
pytest test_pyquote.py -v

# Run specific test class
pytest test_pyquote.py::TestArgumentParsing -v

# Run with coverage report
pytest test_pyquote.py --cov=pyquote --cov-report=html

# Run only unit tests (skip integration tests)
pytest test_pyquote.py -k "not TestIntegration" -v

# Run only integration tests
pytest test_pyquote.py::TestIntegration -v
```

### Test Coverage

- **14 test classes** covering initialization, logging, database operations, argument parsing, and more
- **Unit tests** with mocked external dependencies
- **Integration tests** that run against real MySQL database (auto-skips if unavailable)
- **Edge case coverage** for boundary conditions and error scenarios

## API Limitations

⚠️ **Important:** yFinance restricts 1-minute granularity data to 8 days per request

**Solution:** The application automatically:
- Splits large lookback periods into 7-day chunks
- Limits maximum lookback to 28 days (4 chunks)
- Maintains data consistency with duplicate prevention

## Troubleshooting

### "Connection Refused on Port 3306"
- Ensure MySQL server is running: `sudo systemctl status mysql`
- Verify credentials are correct
- Check that user has database permissions

### "Invalid ticker 'XYZ': not found in yFinance API"
- The ticker symbol is not recognized by yFinance
- Verify the ticker symbol is correct
- Check that the company/stock is still trading

### "Data too long for column 'price'"
- Ensure `price` column is `varchar(45)` or larger
- Prices are formatted to 2 decimal places

### "Yahoo error = '1m data not available'"
- Usually occurs on weekends/holidays when markets are closed
- Check your internet connection
- Verify yFinance API is accessible

## Performance Tips

1. 🕐 Run during off-market hours to avoid API rate limiting
2. 📉 Use shorter lookback periods (e.g., `-d 7`) for frequent updates
3. 🔍 Enable DEBUG logging (`-i`) only during troubleshooting
4. 📅 Consider batching multiple runs with different date ranges
5. 🚀 Use a cronjob for automated daily updates

## Database Schema

### stocks table
| Column | Type | Notes |
|--------|------|-------|
| id | INT UNSIGNED | Primary key, auto-increment |
| ticker | VARCHAR(45) | Stock ticker symbol (unique) |
| lastUpdate | DATETIME | Last quote timestamp for this stock |

### quotes table
| Column | Type | Notes |
|--------|------|-------|
| id | INT UNSIGNED | Primary key, auto-increment |
| stock | INT UNSIGNED | Foreign key to stocks.id |
| price | VARCHAR(45) | Quote price (string, 2 decimals) |
| timestamp | DATETIME | Quote timestamp (minute) |
| | | Unique constraint on (stock, timestamp) |

## Development

### Project Structure

```
pyquote/
├── pyquote.py                  # Main application
├── test_pyquote.py             # Test suite
├── requirements.txt            # Python dependencies
├── copilot-instructions.md     # Copilot guidelines
├── LICENSE                     # Apache 2.0 License
└── README.md                   # This file
```

### Code Style

- Follow PEP 8 conventions
- Include docstrings for all methods
- Use type hints where applicable
- Write tests for new features

### Adding New Features

1. Create feature branch: `git checkout -b feature/feature-name`
2. Add tests in `test_pyquote.py`
3. Implement feature in `pyquote.py`
4. Ensure all tests pass: `pytest test_pyquote.py -v`
5. Submit pull request with description

## Supported Stocks

The application processes 75 stocks including:

AA, AAL, AAPL, ACET, ADBE, ADP, AMAT, AMD, AMZN, AXP, BABA, BAC, BKNG, C, CCL, CALA, CMCSA, COF, CRM, CSCO, CVX, CX, DAL, DIS, F, FOXA, GE, GS, HAL, HBAN, HD, IJK, INTC, JBLU, JD, JNJ, JPM, KHC, KO, LCID, LOW, LUV, M, MA, MNKD, MMM, MRK, MRNA, MS, MSFT, NFLX, NOK, NVDA, NXE, PBR, PCTY, PFE, PINS, PYPL, QCOM, QQQ, RIOT, RIVN, SABR, SBUX, SEDG, SFM, SHOP, SPY, SQQQ, T, TSLA, TSN, UAL, UBER, V, VGLT, VTI, VXX, WFC, XOMA, XRX, WMT, WRN, YELP, ZM

Edit the `tickers` list in `pyquote.py` to customize.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

### Apache License 2.0 Summary

✅ You can:
- Use commercially
- Modify the code
- Distribute the software

⚠️ You must:
- Include a copy of the license
- State significant changes
- Provide a copy of the license with distributions

## Support

For issues and questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review [copilot-instructions.md](copilot-instructions.md) for detailed technical documentation
3. Open an issue on GitHub with:
   - Clear description of the problem
   - Steps to reproduce
   - Error messages/logs
   - Python and MySQL versions

## Changelog

### Version 1.0.0 (2025-12-28)

- ✨ Initial release
- 📊 Fetch intraday minute quotes from yFinance
- 💾 Store quotes in MySQL with duplicate prevention
- 📝 Comprehensive logging with DEBUG mode
- 🧪 Full test suite with integration tests
- 📚 Complete documentation and API guidelines

## Acknowledgments

- [yFinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance API wrapper
- [MySQL Connector/Python](https://dev.mysql.com/doc/connector-python/en/) - MySQL database driver
- [pytest](https://pytest.org/) - Testing framework

## AI Assistance

This project was developed with the assistance of Claude AI (Anthropic). The code generation, testing, documentation, and iterative debugging were performed using Claude's code generation and analysis capabilities.
