import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# List of tickers
tickers = ['BBAR', 'BMA', 'CEPU', 'CRESY', 'EDN', 'GGAL', 'IRS', 'LOMA', 'PAM', 'SUPV', 'TEO', 'TGS', 'YPF']

st.title("Análisis de Volatilidad Intradía - Resolución de 1 Minuto")

# Date selection
st.subheader("Selecciona las fechas para el análisis")
selected_intraday_date = st.date_input("Fecha del análisis intradía (Hoy):", value=datetime.now().date())
selected_previous_date = st.date_input("Fecha del cierre anterior:", value=(datetime.now().date() - timedelta(days=1)))

# Option to extend analysis to last 30 trading days
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

def get_last_30_trading_days():
    """Get the last 30 trading days from the current date."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=45)  # Consider extra days for weekends/holidays

    # Download historical data to determine trading days
    ticker = tickers[0]  # Using one ticker as a reference for market days
    data = yf.download(ticker, start=start_date, end=end_date)
    trading_days = pd.Series(data.index.date).unique()

    # Return the last 30 trading days
    return trading_days[-30:]

def analyze_volatility(ticker, intraday_data, previous_close):
    """Analyze how many times the price crosses from positive to negative and vice versa."""
    intraday_data['Above_Previous_Close'] = intraday_data['Adj Close'] > previous_close
    intraday_data['Cross'] = intraday_data['Above_Previous_Close'].astype(int).diff().fillna(0)
    pos_to_neg = (intraday_data['Cross'] == -1).sum()  # positive -> negative
    neg_to_pos = (intraday_data['Cross'] == 1).sum()   # negative -> positive
    total_crossings = pos_to_neg + neg_to_pos
    return total_crossings, pos_to_neg, neg_to_pos

def analyze_last_30_trading_days(ticker):
    """Analyze volatility for the last 30 trading days and calculate average and median crossings."""
    total_crossings_list = []
    pos_to_neg_list = []
    neg_to_pos_list = []
    trading_days = get_last_30_trading_days()

    for trading_day in trading_days:
        intraday_data = fetch_intraday_data(ticker, trading_day)
        previous_close, previous_date = fetch_previous_close(ticker, trading_day - timedelta(days=1))
        
        if not intraday_data.empty and previous_close is not None:
            total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(ticker, intraday_data, previous_close)
            total_crossings_list.append(total_crossings)
            pos_to_neg_list.append(pos_to_neg)
            neg_to_pos_list.append(neg_to_pos)
    
    if total_crossings_list:
        average_crossings = sum(total_crossings_list) / len(total_crossings_list)
        median_crossings = pd.Series(total_crossings_list).median()
        avg_pos_to_neg = sum(pos_to_neg_list) / len(pos_to_neg_list)
        avg_neg_to_pos = sum(neg_to_pos_list) / len(neg_to_pos_list)
    else:
        average_crossings = median_crossings = avg_pos_to_neg = avg_neg_to_pos = 0
    
    return average_crossings, median_crossings, avg_pos_to_neg, avg_neg_to_pos

# Initialize empty list to hold results
results = []

# Loop through each ticker to fetch data and analyze volatility
for ticker in tickers:
    try:
        st.write(f"Procesando ticker: {ticker}")
        if extend_analysis:
            # Analyze last 30 trading days
            avg_crossings, median_crossings, avg_pos_to_neg, avg_neg_to_pos = analyze_last_30_trading_days(ticker)
            results.append({
                'Ticker': ticker,
                'Cruces Promedio (30 días)': avg_crossings,
                'Cruces Medianos (30 días)': median_crossings,
                'Promedio Cruces Pos->Neg (30 días)': avg_pos_to_neg,
                'Promedio Cruces Neg->Pos (30 días)': avg_neg_to_pos
            })
        else:
            # Analyze selected date
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
                'Cruces Pos->Neg': pos_to_neg,
                'Cruces Neg->Pos': neg_to_pos
            })
    
    except Exception as e:
        st.error(f"Error procesando datos para {ticker}: {e}")

# Convert results to DataFrame and display the table
df_results = pd.DataFrame(results)

if extend_analysis:
    st.subheader("Promedio y Mediana de Cruces en los Últimos 30 Días (Días de Trading)")
    st.dataframe(df_results)
else:
    st.subheader("Resultados de Volatilidad Intradía (1 Minuto)")
    st.dataframe(df_results)

# Display bar plot for total crossings
if not df_results.empty:
    if extend_analysis:
        st.subheader("Cruces Promedio en los Últimos 30 Días (Días de Trading)")
        st.bar_chart(df_results.set_index('Ticker')['Cruces Promedio (30 días)'])
    else:
        st.subheader("Número de Cruces de Precios Intradía (Pos->Neg y Neg->Pos)")
        st.bar_chart(df_results.set_index('Ticker')['Cruces Totales'])
