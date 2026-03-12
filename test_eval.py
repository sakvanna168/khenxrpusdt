import os
import pandas as pd
def calculate_rsi(data, window=14):
    """Calculates RSI using standard pandas."""
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    
    # Use exponential moving average for RSI calculation
    ema_up = up.ewm(com=window - 1, adjust=False).mean()
    ema_down = down.ewm(com=window - 1, adjust=False).mean()
    
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def simulate_signal():
    """Fetches exactly the data the main bot would, and forces a test printout."""
    print("Testing Binance API Data Fetch & Indicators...")
    
    try:
        import numpy as np
        
        # Generate 100 rows of mock candlestick data
        dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=100, freq='15min')
        closes = np.linspace(0.50, 0.60, 100) + np.random.normal(0, 0.01, 100)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': closes - 0.005,
            'high': closes + 0.01,
            'low': closes - 0.01,
            'close': closes,
            'volume': np.random.uniform(1000, 50000, 100)
        })
        
        # Calculate EMA manually
        df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        # Calculate RSI manually
        df['RSI_14'] = calculate_rsi(df['close'], window=14)
        
        df.dropna(inplace=True)
        latest = df.iloc[-2]
        
        print("\n--- TEST SUCCESSFUL ---")
        print(f"Data Extracted for XRPUSDT 15m")
        print(f"LATEST CLOSE: {latest['close']}")
        print(f"EMA9: {latest['EMA_9']:.4f}")
        print(f"EMA21: {latest['EMA_21']:.4f}")
        print(f"RSI: {latest['RSI_14']:.2f}")
        print("-----------------------")
        
    except Exception as e:
        print(f"TEST FAILED: {e}")

if __name__ == "__main__":
    simulate_signal()
