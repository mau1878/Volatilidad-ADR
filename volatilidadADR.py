import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# List of tickers
tickers = ['BBAR', 'BMA', 'CEPU', 'CRESY', 'EDN', 'GGAL', 'IRS', 'LOMA', 'PAM', 'SUPV', 'TEO', 'TGS', 'YPF']

st.title("Análisis de Volatilidad Intradía")

@st.cache_data
def fetch_intraday_data(ticker, interval="5m"):
    """Fetch the latest 5-minute interval intraday data."""
    try:
        data = yf.download(ticker, period="1d", interval=interval)
        if data.empty:
            st.warning(f"No se encontraron datos intradía para {ticker}.")
            return pd.DataFrame()
        return data
    except Exception as e:
        st.error(f"Error al obtener datos intradía para {ticker}: {e}")
        return pd.DataFrame()

@st.cache_data
def fetch_previous_close(ticker):
    """Fetch the daily close price of the previous trading date."""
    try:
        today = datetime.now().date()
        previous_trading_day = today - timedelta(days=1)

        # Fetch daily data for the previous 2 days to get the closing price
        data = yf.download(ticker, start=previous_trading_day - timedelta(days=2), end=previous_trading_day + timedelta(days=1))

        if data.empty:
            st.warning(f"No se encontraron datos para {ticker}.")
            return None, None
        
        # Get the close price for the last day before today
        previous_close = data['Adj Close'].iloc[-1]
        previous_date = data.index[-1].date()  # Get the date of the last close
        return previous_close, previous_date
    except Exception as e:
        st.error(f"Error al obtener datos de cierre anterior para {ticker}: {e}")
        return None, None

def analyze_volatility(ticker, intraday_data, previous_close):
    """Analyze how many times the price crosses from positive to negative and vice versa."""
    intraday_data['Cross'] = (intraday_data['Adj Close'] > previous_close).astype(int).diff().fillna(0)

    # Count positive-to-negative and negative-to-positive transitions
    pos_to_neg = ((intraday_data['Cross'] == -1).sum())
    neg_to_pos = ((intraday_data['Cross'] == 1).sum())
    
    total_crossings = pos_to_neg + neg_to_pos
    return total_crossings, pos_to_neg, neg_to_pos

# Initialize empty list to hold results
results = []

# Loop through each ticker to fetch data and analyze volatility
for ticker in tickers:
    try:
        st.write(f"Procesando ticker: {ticker}")
        intraday_data = fetch_intraday_data(ticker)
        previous_close, previous_date = fetch_previous_close(ticker)

        if intraday_data.empty or previous_close is None:
            continue
        
        # Get today's date from intraday data
        today_date = intraday_data.index[-1].date()
        
        total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(ticker, intraday_data, previous_close)
        
        results.append({
            'Ticker': ticker,
            'Fecha Hoy': today_date,
            'Fecha Cierre Anterior': previous_date,
            'Cruces Totales': total_crossings,
            'Positivo a Negativo': pos_to_neg,
            'Negativo a Positivo': neg_to_pos
        })
    
    except Exception as e:
        st.error(f"Error procesando datos para {ticker}: {e}")

# Convert results to DataFrame and display the table
df_results = pd.DataFrame(results)
st.subheader("Resultados de Volatilidad Intradía")
st.dataframe(df_results)

# Display bar plot for total crossings
if not df_results.empty:
    st.subheader("Número de Cruces de Precios Intradía (Positivo a Negativo y Viceversa)")
    st.bar_chart(df_results.set_index('Ticker')['Cruces Totales'])
