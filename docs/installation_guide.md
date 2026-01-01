# Installation Guide

## System Requirements

### Software Requirements

- **Python**: Version 3.9 or higher
- **Operating System**: Windows, macOS, or Linux
- **Package Manager**: pip (included with Python)
- **Virtual Environment**: Recommended but optional

### Hardware Requirements

- **RAM**: Minimum 4 GB, recommended 8 GB
- **Disk Space**: Minimum 500 MB for application and dependencies, plus 50-100 MB per ticker for cached data
- **Network**: Internet connection required for initial data download and updates

## Installation Steps

### 1. Clone or Download the Repository

```bash
# Option A: Clone with git
git clone <repository-url>
cd bollinger-bands

# Option B: Download and extract ZIP
# Download from repository, extract, and navigate to directory
cd bollinger-bands
```

### 2. Create Virtual Environment (Recommended)

Creating a virtual environment isolates the project dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

Your command prompt should now show `(.venv)` indicating the virtual environment is active.

### 3. Install Dependencies

The project uses `pyproject.toml` for dependency management:

```bash
# Install the package in editable mode
pip install -e .
```

This command will automatically install all required dependencies:
- pandas (≥1.3.0)
- matplotlib (≥3.4.0)
- yfinance (≥0.1.67)
- plotly (≥5.3.1)
- dash (≥2.0.0)
- dash-bootstrap-components (≥2.0.4)
- dash-bootstrap-templates (≥2.1.0)
- pyyaml (≥6.0)

### 4. Verify Installation

Verify that the package is correctly installed:

```bash
# Test imports
python -c "from bollinger_bands.data import DataFetcher, DataStorageManager; print('✓ Import successful')"

# Check installed version
pip show bollinger-bands
```

### 5. Configure Tickers

The application uses a YAML configuration file for ticker management:

```bash
# View the default configuration
cat config/tickers.yaml

# Edit if you want to add or remove tickers
nano config/tickers.yaml  # or use your preferred editor
```

Default configuration includes:
- EEM (Emerging Markets)
- URTH (Global Markets)
- GDX (Basic Materials)
- GDXJ (Basic Materials Junior)
- LTAM.L (Latin America)
- IBB (Healthcare)
- XBI (Healthcare Extended)
- IOGP.L (Oil & Gas)
- WENS.AS (Energy Sector)

### 6. Create Data Directory

Create the directory structure for cached data:

```bash
# Create data directory
mkdir -p data/raw
```

### 7. Initial Data Download

Perform the initial data download using the CLI tool:

```bash
# Download data for all configured tickers
python manage_data.py update

# This will take 30-60 seconds on first run
# Subsequent updates will be much faster (1-3 seconds)
```

You can monitor the download progress in the terminal output.

### 8. Verify Data Download

Check that data was successfully downloaded:

```bash
# View data status
python manage_data.py info

# Expected output:
# ============================================================================
# All Ticker Data Information
# ============================================================================
# ticker    name                   status  start_date  end_date    row_count
# EEM       Emerging Markets       OK      2000-01-02  2024-12-29  6234
# ...
```

### 9. Launch Application

Start the web application:

```bash
# Navigate to examples directory
cd examples

# Launch application
python app.py
```

or 

```bash
python -m bollinger_bands
```

The application will start and display:
```
Dash is running on http://127.0.0.1:8050/
```

Open your web browser and navigate to `http://localhost:8050` to access the application.

## Project Structure

After installation, your project should have the following structure:

```
bollinger-bands/
├── config/
│   └── tickers.yaml           # Ticker configuration
├── data/
│   └── raw/                   # Cached data (created during installation)
│       ├── EEM.csv
│       ├── URTH.csv
│       └── ...
├── examples/
│   └── app.py                 # Main application
├── src/
│   └── bollinger_bands/       # Package source code
│       ├── data/
│       │   ├── fetcher.py
│       │   └── storage_manager.py
│       ├── indicators/
│       ├── strategies/
│       └── visualization/
├── tests/                     # Unit tests
├── manage_data.py            # CLI tool
├── pyproject.toml            # Project configuration
└── README.md                 # Project documentation
```

## Configuration Options

### Ticker Configuration

Edit `config/tickers.yaml` to customize ticker selection:

```yaml
tickers:
  # Add new ticker
  - symbol: SPY
    name: "S&P 500 ETF"
    enabled: true
  
  # Disable ticker without removing
  - symbol: OLD.TICKER
    name: "Old Ticker"
    enabled: false
```

### Data Settings

Configure data management behavior:

```yaml
data_settings:
  # Historical data start date
  default_start_date: "2000-01-01"
  
  # Data storage location
  data_directory: "data/raw"
  
  # Automatic updates on app startup
  auto_update_on_startup: true
  
  # Cache expiration (null = never expire)
  max_cache_days: null
```

## Troubleshooting

### Common Installation Issues

#### Issue: pip install fails with "No module named setuptools"

**Solution:**
```bash
pip install --upgrade pip setuptools wheel
pip install -e .
```

#### Issue: pyproject.toml syntax error

**Solution:**
Verify YAML syntax is correct. Common issues:
- Missing quotes around version strings
- Missing commas between dependencies
- Incorrect indentation

Check syntax:
```bash
python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb')))"
```

#### Issue: Import errors after installation

**Solution:**
```bash
# Reinstall in editable mode
pip uninstall bollinger-bands
pip install -e .

# Verify installation
python -c "import bollinger_bands; print(bollinger_bands.__file__)"
```

#### Issue: Virtual environment not activating

**Solution:**
```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows (PowerShell)
.venv\Scripts\Activate.ps1

# On Windows (Command Prompt)
.venv\Scripts\activate.bat
```

#### Issue: Data download fails

**Solution:**
```bash
# Check network connection
ping yahoo.com

# Try downloading a single ticker
python manage_data.py fetch EEM --start-date 2023-01-01

# Clear cache and retry
python manage_data.py clear --all
python manage_data.py update
```

#### Issue: Application won't start

**Solution:**
```bash
# Check if port 8050 is already in use
# On macOS/Linux:
lsof -i :8050

# On Windows:
netstat -ano | findstr :8050

# Use a different port
# In app.py, change the last line:
app.run(debug=False, port=8051)  # Use port 8051 instead
```

### Permission Issues

If you encounter permission errors:

```bash
# On macOS/Linux:
# Ensure scripts are executable
chmod +x manage_data.py

# Check file ownership
ls -la config/tickers.yaml
ls -la data/raw/

# Fix ownership if needed
chown -R $USER:$USER data/
```

### Dependencies Issues

If specific packages fail to install:

```bash
# Update pip
pip install --upgrade pip

# Install dependencies individually
pip install pandas matplotlib yfinance plotly dash dash-bootstrap-components pyyaml

# Then install package
pip install -e .
```

## Updating

### Update Application Code

```bash
# Pull latest changes (if using git)
git pull origin main

# Reinstall dependencies
pip install -e .
```

### Update Data

```bash
# Update all tickers
python manage_data.py update

# Or update via web interface
# Click "Update Data" button in the application
```

### Update Dependencies

```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Or update specific package
pip install --upgrade yfinance
```

## Uninstallation

### Remove Virtual Environment

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment directory
rm -rf .venv
```

### Remove Cached Data

```bash
# Remove all cached data
rm -rf data/raw/*.csv

# Or use CLI tool
python manage_data.py clear --all
```

### Uninstall Package

```bash
# Uninstall package
pip uninstall bollinger-bands

# Remove project directory
cd ..
rm -rf bollinger-bands/
```

## Next Steps

After successful installation:

1. **Read the User Guide**: `docs/user_guide.md` for detailed usage instructions
2. **Configure Tickers**: Edit `config/tickers.yaml` to add your preferred tickers
3. **Explore Options**: Review `docs/configuration_options.md` for parameter explanations
4. **Run Examples**: Try different configurations to understand the trading strategy
5. **Review Strategy**: Read `README.md` for background on the Cortés trading methodology

## Support

If you encounter issues not covered in this guide:

1. Check the troubleshooting section above
2. Review error messages carefully
3. Verify all dependencies are correctly installed
4. Ensure configuration files are valid YAML
5. Check that data directory has write permissions

For additional help, refer to the project documentation in the `docs/` directory.
