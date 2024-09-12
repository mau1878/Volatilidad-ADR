import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# List of tickers
tickers = ['BBAR', 'BMA', 'CEPU', 'CRESY', 'EDN', 'GGAL', 'IRS', 'LOMA', 'PAM', 'SUPV', 'TEO', 'TGS', 'YPF']

st.title("Análisis de Volatilidad Intradía - Resolución de 1 Minuto")

# Date selection
st.subheader("Selecciona las fechas para el análisis")
selected_intraday_date = st.date_input("Fecha del análisis intradía (Hoy):", value=datetime.now().date())
selected_previous_date = st.date_input("Fecha del cierre anterior:", value=(datetime.now().date() - timedelta(days=1)))

# Option to extend analysis to last 30 days
extend_analysis = st.checkbox("Extender análisis a los últimos 30 días")

@st.cache_data
def fetch_intraday_data(ticker, intraday_date, interval="1m"):
    """Fetch the 1-minute interval intraday data for the selected date."""
    try:
        data = yf.download(ticker, start=intraday_date, end=intraday_date + timedelta(days=1), interval=interval)
        if data.empty:
            return pd.DataFrame()
        return data
    except Exception as e:
        return pd.DataFrame()

@st.cache_data
def fetch_previous_close(ticker, previous_date):
    """Fetch the daily close price of the user-selected previous trading date."""
    try:
        data = yf.download(ticker, start=previous_date - timedelta(days=1), end=previous_date + timedelta(days=1))
        if data.empty:
            return None, None
        
        # Get the close price for the selected previous date
        previous_close = data['Adj Close'].loc[data.index.date == previous_date].iloc[-1]
        return previous_close, previous_date
    except Exception as e:
        return None, None

def analyze_volatility(ticker, intraday_data, previous_close):
    """Analyze how many times the price crosses from positive to negative and vice versa."""
    intraday_data['Above_Previous_Close'] = intraday_data['Adj Close'] > previous_close
    intraday_data['Cross'] = intraday_data['Above_Previous_Close'].astype(int).diff().fillna(0)
    pos_to_neg = (intraday_data['Cross'] == -1).sum()  # positive -> negative
    neg_to_pos = (intraday_data['Cross'] == 1).sum()   # negative -> positive
    total_crossings = pos_to_neg + neg_to_pos
    return total_crossings

def analyze_last_30_days(ticker):
    """Analyze volatility for the last 30 trading days and calculate average and median crossings."""
    total_crossings_list = []
    current_date = selected_intraday_date

    for _ in range(30):
        intraday_data = fetch_intraday_data(ticker, current_date)
        previous_close, previous_date = fetch_previous_close(ticker, current_date - timedelta(days=1))
        
        if not intraday_data.empty and previous_close is not None:
            total_crossings = analyze_volatility(ticker, intraday_data, previous_close)
            total_crossings_list.append(total_crossings)
        
        # Move to the previous trading day
        current_date -= timedelta(days=1)
    
    if total_crossings_list:
        average_crossings = sum(total_crossings_list) / len(total_crossings_list)
        median_crossings = pd.Series(total_crossings_list).median()
    else:
        average_crossings = median_crossings = 0
    
    return average_crossings, median_crossings

# Initialize empty list to hold results
results = []

# Loop through each ticker to fetch data and analyze volatility
for ticker in tickers:
    try:
        st.write(f"Procesando ticker: {ticker}")
        if extend_analysis:
            # Analyze last 30 days
            average_crossings, median_crossings = analyze_last_30_days(ticker)
            results.append({
                'Ticker': ticker,
                'Cruces Promedio (30 días)': average_crossings,
                'Cruces Medianos (30 días)': median_crossings
            })
        else:
            # Analyze selected date
            intraday_data = fetch_intraday_data(ticker, selected_intraday_date)
            previous_close, previous_date = fetch_previous_close(ticker, selected_previous_date)
            
            if intraday_data.empty or previous_close is None:
                continue
            
            total_crossings = analyze_volatility(ticker, intraday_data, previous_close)
            results.append({
                'Ticker': ticker,
                'Fecha Hoy': selected_intraday_date,
                'Fecha Cierre Anterior': previous_date,
                'Cruces Totales': total_crossings
            })
    
    except Exception as e:
        st.error(f"Error procesando datos para {ticker}: {e}")

# Convert results to DataFrame and display the table
df_results = pd.DataFrame(results)

if extend_analysis:
    st.subheader("Promedio y Mediana de Cruces en los Últimos 30 Días")
    st.dataframe(df_results)
else:
    st.subheader("Resultados de Volatilidad Intradía (1 Minuto)")
    st.dataframe(df_results)

# Display bar plot for total crossings
if not df_results.empty:
    if extend_analysis:
        st.subheader("Cruces Promedio en los Últimos 30 Días")
        st.bar_chart(df_results.set_index('Ticker')['Cruces Promedio (30 días)'])
    else:
        st.subheader("Número de Cruces de Precios Intradía (Positivo a Negativo y Viceversa)")
        st.bar_chart(df_results.set_index('Ticker')['Cruces Totales'])
