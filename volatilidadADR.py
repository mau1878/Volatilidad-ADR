import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import pandas_market_calendars as mcal

# Set page configuration
st.set_page_config(page_title="Análisis de Volatilidad Intradía", layout="wide")

# Title of the app
st.title("Análisis de Volatilidad Intradía - Resolución de 1 Minuto")

# Define ticker sets
ADR_TICKERS = [
'BBAR', 'BMA', 'CEPU', 'CRESY', 'EDN', 'GGAL', 'IRS', 'LOMA',
'PAM', 'SUPV', 'TEO', 'TGS', 'YPF'
]

MERVAL_TICKERS = [
"GGAL.BA", "YPFD.BA", "PAMP.BA", "TXAR.BA", "ALUA.BA", "CRES.BA",
"SUPV.BA", "CEPU.BA", "BMA.BA", "TGSU2.BA", "TRAN.BA", "EDN.BA",
"LOMA.BA", "MIRG.BA", "DGCU2.BA", "BBAR.BA", "MOLI.BA", "TGNO4.BA",
"CGPA2.BA", "COME.BA", "IRSA.BA", "BYMA.BA", "TECO2.BA", "METR.BA",
"CECO2.BA", "BHIP.BA", "AGRO.BA", "LEDE.BA", "CVH.BA", "HAVA.BA",
"AUSO.BA", "VALO.BA", "SEMI.BA", "INVJ.BA", "CTIO.BA", "MORI.BA",
"HARG.BA", "GCLA.BA", "SAMI.BA", "BOLT.BA", "MOLA.BA", "CAPX.BA",
"OEST.BA", "LONG.BA", "GCDI.BA", "GBAN.BA", "CELU.BA", "FERR.BA",
"CADO.BA", "GAMI.BA", "PATA.BA", "CARC.BA", "BPAT.BA", "INTR.BA",
"GARO.BA", "FIPL.BA", "GRIM.BA", "DYCA.BA", "POLL.BA", "DOME.BA",
"ROSE.BA", "MTR.BA"
]

# Sidebar for user inputs
st.sidebar.header("Configuración del Análisis")

# Ticker set selection
ticker_set_option = st.sidebar.radio(
"Selecciona el conjunto de tickers para analizar:",
("ADRs", "Acciones del Merval")
)

# Assign selected tickers based on user choice
if ticker_set_option == "ADRs":
tickers = ADR_TICKERS
st.sidebar.markdown("**Conjunto de Tickers Seleccionado:** ADRs")
else:
tickers = MERVAL_TICKERS
st.sidebar.markdown("**Conjunto de Tickers Seleccionado:** Acciones del Merval")

# Function to get trading days based on ticker set
@st.cache_data
def get_trading_days(start_date, end_date, ticker_set):
  if ticker_set == "ADRs":
      nyse = mcal.get_calendar('NYSE')
      trading_days = nyse.valid_days(start_date=start_date, end_date=end_date).tz_localize(None).to_pydatetime()
  else:
      # Para Merval, asumimos días hábiles de lunes a viernes
      trading_days = pd.bdate_range(start=start_date, end=end_date, freq='C').to_pydatetime()
  return trading_days

# Helper function to get the last trading day using the appropriate calendar
@st.cache_data
def get_last_trading_day(reference_date, ticker_set):
  start = reference_date - timedelta(days=7)
  trading_days = get_trading_days(start_date=start, end_date=reference_date, ticker_set=ticker_set)
  if trading_days.size > 0:
      return trading_days[-1].date()
  else:
      return reference_date

# Current date in Buenos Aires timezone
buenos_aires = pytz.timezone('America/Argentina/Buenos_Aires')
now_ba = datetime.now(buenos_aires).date()

# Selected intraday date
selected_intraday_date = st.sidebar.date_input(
"Fecha del análisis intradía:",
value=get_last_trading_day(now_ba, ticker_set_option)
)

# Ensure the selected intraday date is not in the future
if selected_intraday_date > now_ba:
st.sidebar.error("La fecha seleccionada no puede ser en el futuro.")
selected_intraday_date = get_last_trading_day(now_ba, ticker_set_option)

# Selected previous close date
selected_previous_date = st.sidebar.date_input(
"Fecha del cierre anterior:",
value=get_last_trading_day(selected_intraday_date - timedelta(days=1), ticker_set_option)
)

# Checkbox to extend analysis to the last 30 days
extend_analysis = st.sidebar.checkbox("Extender análisis a los últimos 30 días")

# Display selected dates
st.sidebar.markdown(f"**Fecha Intradía Seleccionada:** {selected_intraday_date}")
st.sidebar.markdown(f"**Fecha de Cierre Anterior:** {selected_previous_date}")

# Add confirm button
confirm = st.sidebar.button("Confirmar")

# Function to fetch intraday data
@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday_data(ticker, intraday_date, interval="1m"):
  try:
      start = datetime.combine(intraday_date, datetime.min.time())
      end = start + timedelta(days=1)
      data = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
      if data.empty:
          return pd.DataFrame()
      return data
  except Exception as e:
      st.error(f"Error fetching intraday data for {ticker}: {e}")
      return pd.DataFrame()

# Function to fetch previous close
@st.cache_data(ttl=300, show_spinner=False)
def fetch_previous_close(ticker, previous_date, ticker_set):
  try:
      if ticker_set == "ADRs":
          nyse = mcal.get_calendar('NYSE')
          trading_days = get_trading_days(start_date=previous_date - timedelta(days=10), end_date=previous_date, ticker_set=ticker_set)
      else:
          trading_days = get_trading_days(start_date=previous_date - timedelta(days=10), end_date=previous_date, ticker_set=ticker_set)
      
      if len(trading_days) == 0:
          return None, None
      
      closest_date = trading_days[-1]
      data = yf.download(ticker, start=closest_date, end=closest_date + timedelta(days=1), progress=False)
      if data.empty:
          return None, None
      previous_close = data['Adj Close'].iloc[-1]
      actual_previous_date = data.index[-1].date()
      return previous_close, actual_previous_date
  except Exception as e:
      st.error(f"Error fetching previous close for {ticker}: {e}")
      return None, None

# Function to analyze volatility
def analyze_volatility(intraday_data, previous_close):
  intraday_data = intraday_data.copy()
  intraday_data['Above_Previous_Close'] = intraday_data['Adj Close'] > previous_close
  intraday_data['Cross'] = intraday_data['Above_Previous_Close'].astype(int).diff().fillna(0)
  pos_to_neg = (intraday_data['Cross'] == -1).sum()  # Above to Below
  neg_to_pos = (intraday_data['Cross'] == 1).sum()   # Below to Above
  total_crossings = pos_to_neg + neg_to_pos
  return total_crossings, pos_to_neg, neg_to_pos

# Function to analyze last 30 days
def analyze_last_30_days(ticker, end_date, ticker_set):
  start_date = end_date - timedelta(days=30)
  trading_days = get_trading_days(start_date=start_date, end_date=end_date, ticker_set=ticker_set)

  # Filtrar trading_days que sean <= end_date
  trading_days = [day for day in trading_days if day <= end_date]

  # Tomar los últimos 20 días de negociación dentro de los últimos 30 días calendario
  trading_days_sorted = sorted(trading_days)
  selected_trading_days = trading_days_sorted[-20:]

  if len(selected_trading_days) < 20:
      st.warning(f"No se encontraron suficientes días de negociación para {ticker}. Se encontraron {len(selected_trading_days)} días.")
      return None

  total_crossings_list = []
  pos_to_neg_list = []
  neg_to_pos_list = []
  daily_data = []

  for current_date in selected_trading_days:
      try:
          intraday_data = fetch_intraday_data(ticker, current_date)
          previous_close_result = fetch_previous_close(ticker, current_date - timedelta(days=1), ticker_set)

          if intraday_data.empty or previous_close_result[0] is None:
              st.warning(f"No se pudo obtener información completa para {ticker} en {current_date}. Saltando este día.")
              continue

          previous_close, actual_previous_date = previous_close_result
          total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(intraday_data, previous_close)

          total_crossings_list.append(total_crossings)
          pos_to_neg_list.append(pos_to_neg)
          neg_to_pos_list.append(neg_to_pos)
          daily_data.append({
              'Fecha': current_date.date(),  # Convert to date
              'Cruces Totales': total_crossings,
              'Cruces Pos->Neg': pos_to_neg,
              'Cruces Neg->Pos': neg_to_pos
          })
      except Exception as e:
          st.error(f"Error al procesar {ticker} en {current_date.date()}: {e}")

  if not total_crossings_list:
      return None

  average_crossings = sum(total_crossings_list) / len(total_crossings_list)
  median_crossings = pd.Series(total_crossings_list).median()
  avg_pos_to_neg = sum(pos_to_neg_list) / len(pos_to_neg_list)
  avg_neg_to_pos = sum(neg_to_pos_list) / len(neg_to_pos_list)

  df_daily = pd.DataFrame(daily_data)

  most_total_crossings = df_daily.loc[df_daily['Cruces Totales'].idxmax()]
  least_total_crossings = df_daily.loc[df_daily['Cruces Totales'].idxmin()]
  most_pos_to_neg = df_daily.loc[df_daily['Cruces Pos->Neg'].idxmax()]
  least_pos_to_neg = df_daily.loc[df_daily['Cruces Pos->Neg'].idxmin()]
  most_neg_to_pos = df_daily.loc[df_daily['Cruces Neg->Pos'].idxmax()]
  least_neg_to_pos = df_daily.loc[df_daily['Cruces Neg->Pos'].idxmin()]

  return {
      'Promedio Cruces Totales': average_crossings,
      'Mediana Cruces Totales': median_crossings,
      'Promedio Cruces Pos->Neg': avg_pos_to_neg,
      'Promedio Cruces Neg->Pos': avg_neg_to_pos,
      'Fecha con Más Cruces Totales': most_total_crossings['Fecha'],
      'Máximo Cruces Totales': most_total_crossings['Cruces Totales'],
      'Fecha con Menos Cruces Totales': least_total_crossings['Fecha'],
      'Mínimo Cruces Totales': least_total_crossings['Cruces Totales'],
      'Fecha con Más Cruces Pos->Neg': most_pos_to_neg['Fecha'],
      'Máximo Cruces Pos->Neg': most_pos_to_neg['Cruces Pos->Neg'],
      'Fecha con Menos Cruces Pos->Neg': least_pos_to_neg['Fecha'],
      'Mínimo Cruces Pos->Neg': least_pos_to_neg['Cruces Pos->Neg'],
      'Fecha con Más Cruces Neg->Pos': most_neg_to_pos['Fecha'],
      'Máximo Cruces Neg->Pos': most_neg_to_pos['Cruces Neg->Pos'],
      'Fecha con Menos Cruces Neg->Pos': least_neg_to_pos['Fecha'],
      'Mínimo Cruces Neg->Pos': least_neg_to_pos['Cruces Neg->Pos']
  }

# Main processing code
if confirm:
results = []

if extend_analysis:
    st.subheader("Análisis Detallado de Cruces en los Últimos 30 Días")
else:
    st.subheader("Resultados de Volatilidad Intradía (1 Minuto)")

with st.spinner('Procesando tickers...'):
    progress_bar = st.progress(0)
    total_tickers = len(tickers)
    for idx, ticker in enumerate(tickers):
        try:
            if extend_analysis:
                analysis = analyze_last_30_days(ticker, selected_intraday_date, ticker_set_option)

                if analysis is None:
                    st.warning(f"No se pudo obtener suficiente información para {ticker}.")
                    continue

                results.append({
                    'Ticker': ticker,
                    'Promedio Cruces Totales (30 días)': round(analysis['Promedio Cruces Totales'], 2),
                    'Mediana Cruces Totales (30 días)': analysis['Mediana Cruces Totales'],
                    'Promedio Cruces Pos->Neg (30 días)': round(analysis['Promedio Cruces Pos->Neg'], 2),
                    'Promedio Cruces Neg->Pos (30 días)': round(analysis['Promedio Cruces Neg->Pos'], 2),
                    'Fecha con Más Cruces Totales': analysis['Fecha con Más Cruces Totales'],
                    'Máximo Cruces Totales': analysis['Máximo Cruces Totales'],
                    'Fecha con Menos Cruces Totales': analysis['Fecha con Menos Cruces Totales'],
                    'Mínimo Cruces Totales': analysis['Mínimo Cruces Totales'],
                    'Fecha con Más Cruces Pos->Neg': analysis['Fecha con Más Cruces Pos->Neg'],
                    'Máximo Cruces Pos->Neg': analysis['Máximo Cruces Pos->Neg'],
                    'Fecha con Menos Cruces Pos->Neg': analysis['Fecha con Menos Cruces Pos->Neg'],
                    'Mínimo Cruces Pos->Neg': analysis['Mínimo Cruces Pos->Neg'],
                    'Fecha con Más Cruces Neg->Pos': analysis['Fecha con Más Cruces Neg->Pos'],
                    'Máximo Cruces Neg->Pos': analysis['Máximo Cruces Neg->Pos'],
                    'Fecha con Menos Cruces Neg->Pos': analysis['Fecha con Menos Cruces Neg->Pos'],
                    'Mínimo Cruces Neg->Pos': analysis['Mínimo Cruces Neg->Pos']
                })
            else:
                intraday_data = fetch_intraday_data(ticker, selected_intraday_date)
                if intraday_data.empty:
                    st.warning(f"No hay datos intradía disponibles para {ticker} en {selected_intraday_date}.")
                    continue

                previous_close_result = fetch_previous_close(ticker, selected_previous_date, ticker_set_option)
                if previous_close_result[0] is None:
                    st.warning(f"No se pudo obtener el cierre anterior para {ticker}.")
                    continue

                previous_close, actual_previous_date = previous_close_result

                total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(intraday_data, previous_close)

                results.append({
                    'Ticker': ticker,
                    'Fecha Hoy': selected_intraday_date,
                    'Fecha Cierre Anterior': actual_previous_date,
                    'Cruces Totales': total_crossings,
                    'Cruces Pos->Neg': pos_to_neg,
                    'Cruces Neg->Pos': neg_to_pos
                })
        except Exception as e:
            st.error(f"Error al procesar {ticker}: {e}")
        finally:
            progress = (idx + 1) / total_tickers
            progress_bar.progress(progress)

    progress_bar.empty()

df_results = pd.DataFrame(results)

if extend_analysis:
    if not df_results.empty:
        df_results = df_results.sort_values(by='Promedio Cruces Totales (30 días)', ascending=False)
        st.dataframe(df_results)

        st.subheader("Promedio de Cruces Totales en los Últimos 30 Días")
        fig1 = df_results[['Ticker', 'Promedio Cruces Totales (30 días)']].set_index('Ticker')
        st.bar_chart(fig1)

        st.subheader("Promedio de Cruces Pos->Neg y Neg->Pos en los Últimos 30 Días")
        fig2 = df_results.set_index('Ticker')[['Promedio Cruces Pos->Neg (30 días)', 'Promedio Cruces Neg->Pos (30 días)']]
        fig2 = fig2.sort_values(by='Promedio Cruces Pos->Neg (30 días)', ascending=False)
        st.bar_chart(fig2)
    else:
        st.warning("No se encontraron resultados para la extensión de análisis.")
else:
    if not df_results.empty:
        df_results = df_results.sort_values(by='Cruces Totales', ascending=False)
        st.dataframe(df_results)

        st.subheader("Número de Cruces de Precios Intradía (Totales)")
        fig = df_results[['Ticker', 'Cruces Totales']].set_index('Ticker')
        st.bar_chart(fig)
    else:
        st.warning("No se encontraron resultados para el análisis intradía.")

st.markdown("---")
st.markdown("Desarrollado por MTaurus (https://x.com/MTaurus_ok)")
else:
st.info("Ajusta los parámetros en la barra lateral y presiona **Confirmar** para iniciar el análisis.")
