import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# List of tickers
tickers = ['BBAR', 'BMA', 'CEPU', 'CRESY', 'EDN', 'GGAL', 'IRS', 'LOMA', 'PAM', 'SUPV', 'TEO', 'TGS', 'YPF']

st.title("Análisis de Volatilidad Intradía")

# Date selection
st.subheader("Selecciona las fechas para el análisis")
selected_intraday_date = st.date_input("Fecha del análisis intradía (Hoy):", value=datetime.now().date())
selected_previous_date = st.date_input("Fecha del cierre anterior:", value=(datetime.now().date() - timedelta(days=1)))

@st.cache_data
def fetch_intraday_data(ticker, intraday_date, interval="5m"):
    """Fetch the 5-minute interval intraday data for the selected date."""
    try:
        data = yf.download(ticker, start=intraday_date, end=intraday_date + timedelta(days=1), interval=interval)
        if data.empty:
            st.warning(f"No se encontraron datos intradía para {ticker} el {intraday_date}.")
            return pd.DataFrame()
        return data
    except Exception as e:
        st.error(f"Error al obtener datos intradía para {ticker}: {e}")
        return pd.DataFrame()

@st.cache_data
def fetch_previous_close(ticker, previous_date):
    """Fetch the daily close price of the user-selected previous trading date."""
    try:
        data = yf.download(ticker, start=previous_date - timedelta(days=1), end=previous_date + timedelta(days=1))
        if data.empty:
            st.warning(f"No se encontraron datos para {ticker} el {previous_date}.")
            return None, None
        
        # Get the close price for the selected previous date
        previous_close = data['Adj Close'].loc[data.index.date == previous_date].iloc[-1]
        return previous_close, previous_date
    except Exception as e:
        st.error(f"Error al obtener datos de cierre anterior para {ticker}: {e}")
        return None, None

def analyze_volatility(ticker, intraday_data, previous_close):
    """Analyze how many times the price crosses from positive to negative and vice versa."""
    # Compare each 5-minute price to the previous day's close
    intraday_data['Above_Previous_Close'] = intraday_data['Adj Close'] > previous_close
    
    # Identify where crossings occurred: from positive to negative and vice versa
    intraday_data['Cross'] = intraday_data['Above_Previous_Close'] != intraday_data['Above_Previous_Close'].shift(1)
    
    # Count the number of crossings
    total_crossings = intraday_data['Cross'].sum()
    
    # Calculate how many transitions were from positive to negative and vice versa
    pos_to_neg = ((intraday_data['Above_Previous_Close'].shift(1) == True) & (intraday_data['Above_Previous_Close'] == False)).sum()
    neg_to_pos = ((intraday_data['Above_Previous_Close'].shift(1) == False) & (intraday_data['Above_Previous_Close'] == True)).sum()
    
    return total_crossings, pos_to_neg, neg_to_pos

# Initialize empty list to hold results
results = []

# Loop through each ticker to fetch data and analyze volatility
for ticker in tickers:
    try:
        intraday_data = fetch_intraday_data(ticker, selected_intraday_date)
        previous_close, previous_date = fetch_previous_close(ticker, selected_previous_date)

        if intraday_data.empty or previous_close is None:
            continue
        
        total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(ticker, intraday_data, previous_close)
        
        results.append({
            'Ticker': ticker,
            'Fecha Hoy': selected_intraday_date,
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
