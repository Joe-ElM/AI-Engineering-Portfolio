import matplotlib.pyplot as plt
import os
from datetime import datetime
from typing import Optional
from langchain.tools import tool
import pandas as pd
import yfinance as yf

@tool
def create_hist_prices(start_date: str = '2020-01-01', end_date: Optional[str] = None):
    """
    Fetches historical stock price data for all S&P 500 companies from Yahoo Finance.
    
    Use this when the user wants to:
    - Get historical data for multiple S&P 500 stocks
    - Analyze market trends across the index
    - Build a dataset for further analysis
    
    Args:
        start_date (str): Start date in 'YYYY-MM-DD' format (default: '2020-01-01')
        end_date (str, optional): End date in 'YYYY-MM-DD' format (default: today)
    
    Returns:
        pd.DataFrame: MultiIndex DataFrame with stock prices for S&P 500 companies
        str: Error message if the operation fails
    """
    
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    # Get S&P 500 tickers
    try:
        sp500_tickers = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        sp500_tickers = [ticker for ticker in sp500_tickers if '.B' not in ticker]
    except:
        return "Failed to get S&P 500 tickers"
    
    # Download data
    try:
        data = yf.download(sp500_tickers, start=start_date, end=end_date, progress=False)
        if data.empty:
            return "No data downloaded"
        
        # Keep only tickers with enough data points
        ticker_counts = data.count()
        valid_tickers = ticker_counts[ticker_counts >= 100].index
        data = data[valid_tickers]
        
        return data
    except:
        return "Failed to download data"
    
    
    # ==============================================================
    # ==============================================================
    
import matplotlib.pyplot as plt
import yfinance as yf
import os
import time
from datetime import datetime
from typing import Optional
from langchain.tools import tool

@tool
def plot_price_series(
    ticker: str = 'AAPL',
    field: str = 'Adj Close',
    start_date: str = '2020-01-01',
    end_date: Optional[str] = None,
    interval: str = '1d'
):
    """
    Downloads and plots stock price data for a single ticker from Yahoo Finance.
    
    Use this when the user wants to:
    - See a price chart for a specific stock
    - Visualize stock performance over time
    - Compare different price fields (Open, High, Low, Close, etc.)
    
    Args:
        ticker (str): Stock symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
        field (str): Price field to plot ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume')
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str, optional): End date in 'YYYY-MM-DD' format (default: today)
        interval (str): Data interval ('1d', '1wk', '1mo', etc.)
    
    Returns:
        str: Success message with file path or error message
"""
    
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    # Basic date validation
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if start > end:
            return "Start date must be before end date"
    except:
        return "Invalid date format. Use YYYY-MM-DD"
    
    # Download data
    try:
        time.sleep(1)  # Rate limit protection
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False, auto_adjust=False)
        if data.empty:
            return f"No data found for {ticker}"
        
        if field not in data.columns:
            return f"Field '{field}' not available. Options: {list(data.columns)}"
            
    except Exception as e:
        return f"Error downloading data: {str(e)}"
    
    # Create plot
    try:
        plt.figure(figsize=(12, 6))
        plt.plot(data.index, data[field], linewidth=1.5)
        plt.title(f"{ticker} {field}")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot
        os.makedirs("static/plots", exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S") 
        filename = f"{ticker}_{field.replace(' ', '_')}_{timestamp}.png"
        filepath = f"static/plots/{filename}"
        plt.savefig(filepath)
        plt.close()
        
        return f"Chart saved to {filepath}"
        
    except Exception as e:
        plt.close()
        return f"Error creating plot: {str(e)}"
    
    # ======================================================
    
    
import matplotlib.pyplot as plt
import pandas as pd
import os
from datetime import datetime
from typing import Optional
from langchain.tools import tool

@tool
def plot_price_from_local_data(
    ticker: str = 'AAPL',
    field: str = 'Adj Close',
    start_date: str = '2023-01-01',
    end_date: Optional[str] = None
):
    """
    Plots stock price data from local CSV file containing historical S&P 500 data.
    
    Use this when:
    - Yahoo Finance is not working or rate limited
    - User wants to plot data from your local dataset
    - Need reliable access to historical stock data
    
    Args:
        ticker (str): Stock symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
        field (str): Price field ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume')
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str, optional): End date in 'YYYY-MM-DD' format (default: today)
    
    Returns:
        str: Success message with file path or error message
    """
    
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    csv_path = "data/hist_prices.csv"
    
    # Load local data
    try:
        df = pd.read_csv(csv_path, header=[0, 1], index_col=0, parse_dates=True)
        
        if (field, ticker) not in df.columns:
            available_tickers = df.columns.get_level_values(1).unique()[:10]
            return f"Ticker '{ticker}' not found. Available: {list(available_tickers)}"
        
        # Get data for specific ticker and field
        series = df[(field, ticker)].dropna()
        
        # Filter by date range
        series = series[(series.index >= start_date) & (series.index <= end_date)]
        
        if series.empty:
            return f"No data for {ticker} between {start_date} and {end_date}"
            
    except Exception as e:
        return f"Error loading local data: {str(e)}"
    
    # Create plot
    try:
        plt.figure(figsize=(12, 6))
        plt.plot(series.index, series.values, linewidth=1.5)
        plt.title(f"{ticker} {field}")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot with unique timestamp
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{ticker}_{field.replace(' ', '_')}_{timestamp}.png"
        filepath = f"data/{filename}"
        plt.savefig(filepath)
        plt.close()
        
        return f"Chart created successfully."
        
    except Exception as e:
        plt.close()
        return f"Error creating plot: {str(e)}"
    
    
    # ===========================================
    # added on 02.06.2025
    
@tool
def plot_rolling_average(
    ticker: str = 'AAPL',
    field: str = 'Adj Close',
    start_date: str = '2023-01-01',
    end_date: Optional[str] = None,
    window: int = 20
):
    """
    Plots stock PRICE LINE CHART with moving average overlay from local CSV data.
    
    Use this when user asks for:
    - moving average, trend line, or smoothed prices
    - price chart with MA overlay
    - technical analysis with trend indicators
    - "show prices with X-day average"
    
    Creates a dual-line chart showing both raw prices and their moving average.
    
    Args:
        ticker (str): Stock symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
        field (str): Price field ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume')
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str, optional): End date in 'YYYY-MM-DD' format (default: today)
        window (int): Rolling window size in days (default: 20)
    
    Returns:
        str: Success message with file path or error message
    """
    
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    csv_path = "data/hist_prices.csv"
    
    # Load local data
    try:
        df = pd.read_csv(csv_path, header=[0, 1], index_col=0, parse_dates=True)
        
        if (field, ticker) not in df.columns:
            available_tickers = df.columns.get_level_values(1).unique()[:10]
            return f"Ticker '{ticker}' not found. Available: {list(available_tickers)}"
        
        # Get data for specific ticker and field
        series = df[(field, ticker)].dropna()
        
        # Filter by date range
        series = series[(series.index >= start_date) & (series.index <= end_date)]
        
        if series.empty:
            return f"No data for {ticker} between {start_date} and {end_date}"
        
        if len(series) < window:
            return f"Not enough data points ({len(series)}) for {window}-day rolling average"
            
    except Exception as e:
        return f"Error loading local data: {str(e)}"
    
    # Calculate rolling average
    try:
        rolling_avg = series.rolling(window=window, min_periods=1).mean()
        
    except Exception as e:
        return f"Error calculating rolling average: {str(e)}"
    
    # Create plot
    try:
        plt.figure(figsize=(12, 6))
        plt.plot(series.index, series.values, linewidth=1, alpha=0.7, label=f'{ticker} {field}', color='#1f77b4')
        plt.plot(rolling_avg.index, rolling_avg.values, linewidth=2, label=f'{window}-day Moving Average', color='#ff7f0e')
        plt.title(f"{ticker} {field} with {window}-Day Rolling Average")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot with unique timestamp
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{ticker}_{field.replace(' ', '_')}_MA{window}_{timestamp}.png"
        filepath = f"data/{filename}"
        plt.savefig(filepath)
        plt.close()
        
        return f"Rolling average chart created successfully."
        
    except Exception as e:
        plt.close()
        return f"Error creating plot: {str(e)}"


@tool
def plot_volatility_histogram(
    ticker: str = 'AAPL',
    field: str = 'Adj Close',
    start_date: str = '2023-01-01',
    end_date: Optional[str] = None,
    window: int = 30
):
    """
    Creates a HISTOGRAM showing the frequency distribution of stock volatility levels.
    
    Use this when user asks for:
    - volatility histogram, distribution, or frequency analysis
    - risk analysis or risk patterns
    - how often a stock experiences different volatility levels
    - volatility statistics or volatility spread
    
    This function calculates daily price volatility over rolling windows and displays
    it as a histogram (bar chart) showing how frequently different risk levels occur.
    
    Args:
        ticker (str): Stock symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
        field (str): Price field ('Open', 'High', 'Low', 'Close', 'Adj Close')
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str, optional): End date in 'YYYY-MM-DD' format (default: today)
        window (int): Rolling window for volatility calculation (default: 30 days)
    
    Returns:
        str: Success message with file path or error message
    """
    
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    csv_path = "data/hist_prices.csv"
    
    # Load local data
    try:
        df = pd.read_csv(csv_path, header=[0, 1], index_col=0, parse_dates=True)
        
        if (field, ticker) not in df.columns:
            available_tickers = df.columns.get_level_values(1).unique()[:10]
            return f"Ticker '{ticker}' not found. Available: {list(available_tickers)}"
        
        # Get data for specific ticker and field
        series = df[(field, ticker)].dropna()
        
        # Filter by date range
        series = series[(series.index >= start_date) & (series.index <= end_date)]
        
        if series.empty:
            return f"No data for {ticker} between {start_date} and {end_date}"
        
        if len(series) < window + 1:
            return f"Not enough data points ({len(series)}) for {window}-day volatility calculation"
            
    except Exception as e:
        return f"Error loading local data: {str(e)}"
    
    # Calculate daily returns and rolling volatility
    try:
        returns = series.pct_change().dropna()
        rolling_volatility = returns.rolling(window=window).std() * (252**0.5)  # Annualized
        rolling_volatility = rolling_volatility.dropna()
        
        if rolling_volatility.empty:
            return f"Could not calculate volatility for {ticker}"
            
    except Exception as e:
        return f"Error calculating volatility: {str(e)}"
    
    # Create histogram plot
    try:
        plt.figure(figsize=(10, 6))
        # Convert to percentage for display
        volatility_pct = rolling_volatility * 100
        
        plt.hist(volatility_pct.values, bins=20, alpha=0.7, color='#1f77b4', edgecolor='black')
        plt.title(f"{ticker} {window}-Day Rolling Volatility Distribution\n({start_date} to {end_date})")
        plt.xlabel("Annualized Volatility (%)")
        plt.ylabel("Frequency")
        plt.grid(True, alpha=0.3)
        
        # Add statistics
        mean_vol = volatility_pct.mean()
        median_vol = volatility_pct.median()
        plt.axvline(mean_vol, color='red', linestyle='--', label=f'Mean: {mean_vol:.2f}%')
        plt.axvline(median_vol, color='orange', linestyle='--', label=f'Median: {median_vol:.2f}%')
        plt.legend()
        plt.tight_layout()
        
        # Save plot
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{ticker}_volatility_hist_{window}d_{timestamp}.png"
        filepath = f"data/{filename}"
        plt.savefig(filepath)
        plt.close()
        
        return f"Volatility histogram created successfully."
        
    except Exception as e:
        plt.close()
        return f"Error creating plot: {str(e)}"