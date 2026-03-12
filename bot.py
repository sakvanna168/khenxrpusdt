import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv
import schedule

# Load Environment Variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SYMBOL = os.getenv("SYMBOL", "XRPUSDT")
TIMEFRAME = os.getenv("TIMEFRAME", "15m")

# No initialization needed
# Global state to prevent duplicate signals
last_signal = None 

def calculate_rsi(data, window=14):
    """Calculates RSI using standard pandas."""
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    
    ema_up = up.ewm(com=window - 1, adjust=False).mean()
    ema_down = down.ewm(com=window - 1, adjust=False).mean()
    
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculates MACD Line, Signal Line, and Histogram."""
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_histogram = macd_line - signal_line
    return macd_line, signal_line, macd_histogram

def calculate_atr(df, window=14):
    """Calculates Average True Range for volatility filtering and Stop Loss."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    atr = true_range.rolling(window=window).mean()
    return atr

def send_telegram_message(message: str):
    """Sends a message to the configured Telegram Chat ID."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not found in .env. Skipping message.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def get_historical_data(symbol, interval, limit=100):
    """Fetches historical klines. Tries Binance first, falls back to Bybit if blocked."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Try Binance Futures First
    try:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        klines = response.json()
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
    except Exception as e:
        print(f"Binance API failed ({e}). Falling back to Bybit...")
        # Fallback to Bybit if Binance is blocked in user's region
        try:
            url = "https://api.bytick.com/v5/market/kline"
            # Bybit uses minutes as integers, e.g., '15' instead of '15m'
            bybit_interval = interval.replace('m', '') 
            params = {"category": "linear", "symbol": symbol, "interval": bybit_interval, "limit": limit}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data['retCode'] != 0:
                print(f"Bybit API error: {data['retMsg']}")
                return None
            
            klines = data['result']['list']
            # Bybit returns data from newest to oldest. Reverse it to match Binance (oldest first).
            klines.reverse()
            
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        except Exception as bybit_e:
            print(f"Bybit API also failed: {bybit_e}")
            return None

    try:
        # Common conversion for both Binance and Bybit dataframes
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
        return df
    except Exception as e:
        print(f"Failed to process dataframe: {e}")
        return None

def analyze_and_signal():
    """Main strategy logic to evaluate the market and send signals."""
    global last_signal
    
    print(f"Fetching data for {SYMBOL} on {TIMEFRAME} timeframe...")
    df = get_historical_data(SYMBOL, TIMEFRAME, limit=100)
    
    if df is None or df.empty:
        print("Failed to get data.")
        return

    # Calculate Indicators without pandas-ta
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean() # Baseline Trend Filter
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['RSI_14'] = calculate_rsi(df['close'], window=14)
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['close'])
    df['ATR_14'] = calculate_atr(df, window=14)
    
    df.dropna(inplace=True)
    
    # Get the latest closed candle (index -2 to avoid the currently open, unfinished candle)
    latest = df.iloc[-2]
    previous = df.iloc[-3]
    
    current_price = latest['close']
    ema_200 = latest['EMA_200']
    rsi_14 = latest['RSI_14']
    macd = latest['MACD_Line']
    macd_signal = latest['MACD_Signal']
    atr = latest['ATR_14']
    
    prev_macd = previous['MACD_Line']
    prev_macd_signal = previous['MACD_Signal']
    
    print(f"[{latest['timestamp']}] {SYMBOL} | Close: {current_price} | EMA200: {ema_200:.4f} | RSI: {rsi_14:.2f} | MACD: {macd:.4f} | ATR: {atr:.4f}")

    # --- STRATEGY LOGIC (Advanced filtering) ---
    signal = None
    
    # 1. Trend Filter: Is price above or below 200 EMA?
    uptrend = current_price > ema_200
    downtrend = current_price < ema_200
    
    # 2. Volatility Filter: Is the market moving? (ATR > 0.1% of price roughly)
    # This prevents trading in flat, choppy markets where indicators fail
    min_volatility = current_price * 0.001 
    enough_volatility = atr > min_volatility
    
    # Long Condition: MACD crosses ABOVE Signal Line AND Price is ABOVE 200 EMA AND RSI is not overbought AND Volatility is good
    if prev_macd <= prev_macd_signal and macd > macd_signal and uptrend and rsi_14 < 70 and enough_volatility:
        signal = "BUY"
        
    # Short Condition: MACD crosses BELOW Signal Line AND Price is BELOW 200 EMA AND RSI is not oversold AND Volatility is good
    elif prev_macd >= prev_macd_signal and macd < macd_signal and downtrend and rsi_14 > 30 and enough_volatility:
        signal = "SELL"
    
    if signal and signal != last_signal:
        if signal == "BUY":
            # Dynamic Stop Loss using 1.5x ATR
            stop_loss = current_price - (atr * 1.5)
            # Take profit using 2x Reward/Risk
            take_profit = current_price + ((current_price - stop_loss) * 2)
            emoji = "🟢"
        else: # SELL
            # Dynamic Stop Loss using 1.5x ATR
            stop_loss = current_price + (atr * 1.5)
            # Take profit using 2x Reward/Risk
            take_profit = current_price - ((stop_loss - current_price) * 2)
            emoji = "🔴"
            
        message = (
            f"{emoji} <b>{signal} SIGNAL: {SYMBOL}</b> {emoji}\n\n"
            f"<b>Entry Price:</b> {current_price:.4f}\n"
            f"<b>Stop Loss:</b> {stop_loss:.4f} (Dynamic ATR)\n"
            f"<b>Take Profit:</b> {take_profit:.4f}\n\n"
            f"<i>Indicator Stats:</i>\n"
            f"MACD Cross Confirmed\n"
            f"Trend Check: EMA 200 Confirmed\n"
            f"RSI (14): {rsi_14:.2f}\n"
            f"Timeframe: {TIMEFRAME}"
        )
        
        send_telegram_message(message)
        last_signal = signal
        print(f"--- TRIGGERED {signal} SIGNAL ---")

def main():
    print(f"Started XRPUSDT Signal Bot. Monitoring every {TIMEFRAME}...")
    
    minutes = int(TIMEFRAME.replace('m', ''))
    
    analyze_and_signal()
    
    schedule.every(minutes).minutes.do(analyze_and_signal)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBot stopped by user.")

if __name__ == "__main__":
    main()
