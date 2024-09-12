import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# List of tickers
tickers = ['BBAR', 'BMA', 'CEPU', 'CRESY', 'EDN', 'GGAL', 'IRS', 'LOMA', 'PAM', 'SUPV', 'TEO', 'TGS', 'YPF']

st.title("Análisis de Volatilidad Intradía")

# Date selectors for user to pick the dates
today = datetime.now().date()
start_date = st.date_input("Seleccione la Fecha de Cierre Anterior:", today - timedelta(days=5))
end_date = st.date_input("Seleccione la Fecha de Datos Intradía:", today)

@st.cache_data
def fetch_intraday_data(ticker, interval="5m", date=None):
    """Fetch intraday data for the selected date."""
    try:
        # Fetch 1-day intraday data for the selected end date
        data = yf.download(ticker, start=date, end=date + timedelta(days=1), interval=interval)
        if data.empty:
            st.warning(f"No se encontraron datos intradía para {ticker} en la fecha {date}.")
            return pd.DataFrame()
        return data
    except Exception as e:
        st.error(f"Error al obtener datos intradía para {ticker}: {e}")
        return pd.DataFrame()

@st.cache_data
def fetch_previous_close(ticker, previous_date):
    """Fetch the daily close price for the selected previous trading day."""
    try:
        # Fetch the daily data for the previous date selected by the user
        data = yf.download(ticker, start=previous_date - timedelta(days=2), end=previous_date + timedelta(days=1))

        if data.empty:
            st.warning(f"No se encontraron datos de cierre para {ticker} en la fecha {previous_date}.")
            return None, None

        # Get the close price for the previous day
        previous_close = data['Adj Close'].iloc[-1]
        previous_date = data.index[-1].date()  # Get the exact date of the last close
        return previous_close, previous_date
    except Exception as e:
        st.error(f"Error al obtener el cierre anterior para {ticker}: {e}")
        return None, None

def analyze_volatility(ticker, intraday_data, previous_close):
    """Analyze how many times the price crosses from positive to negative and vice versa."""
    intraday_data['Cross'] = (intraday_data['Adj Close'] > previous_close).astype(int).diff().fillna(0)

    # Count positive-to-negative and negative-to-positive transitions
    pos_to_neg = (intraday_data['Cross'] == -1).sum()
    neg_to_pos = (intraday_data['Cross'] == 1).sum()
    
    total_crossings = pos_to_neg + neg_to_pos
    return total_crossings, pos_to_neg, neg_to_pos

# Initialize empty list to hold results
results = []

# Loop through each ticker to fetch data and analyze volatility
for ticker in tickers:
    try:
        st.write(f"Procesando ticker: {ticker}")
        intraday_data = fetch_intraday_data(ticker, date=end_date)
        previous_close, previous_date_fetched = fetch_previous_close(ticker, start_date)

        if intraday_data.empty or previous_close is None:
            continue
        
        # Get the selected end date (intraday data date)
        intraday_date = intraday_data.index[-1].date()
        
        total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(ticker, intraday_data, previous_close)
        
        results.append({
            'Ticker': ticker,
            'Fecha Hoy (Datos Intradía)': intraday_date,
            'Fecha Cierre Anterior': previous_date_fetched,
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
