import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

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

# Date selection with validation
st.sidebar.subheader("Selección de Fechas")

# Helper function to get the last trading day
@st.cache_data
def get_last_trading_day(reference_date):
  """
  Adjusts the reference_date to the last available trading day.
  """
  for i in range(7):
      adjusted_date = reference_date - timedelta(days=i)
      if adjusted_date.weekday() < 5:  # Monday to Friday are trading days
          return adjusted_date
  return reference_date

# Current date in Buenos Aires timezone
buenos_aires = pytz.timezone('America/Argentina/Buenos_Aires')
now_ba = datetime.now(buenos_aires).date()

# Selected intraday date
selected_intraday_date = st.sidebar.date_input(
  "Fecha del análisis intradía:",
  value=get_last_trading_day(now_ba)
)

# Ensure the selected intraday date is not in the future
if selected_intraday_date > now_ba:
  st.sidebar.error("La fecha seleccionada no puede ser en el futuro.")
  selected_intraday_date = get_last_trading_day(now_ba)

# Selected previous close date
selected_previous_date = st.sidebar.date_input(
  "Fecha del cierre anterior:",
  value=get_last_trading_day(selected_intraday_date - timedelta(days=1))
)

# Checkbox to extend analysis to the last 30 days
extend_analysis = st.sidebar.checkbox("Extender análisis a los últimos 30 días")

# Display selected dates
st.sidebar.markdown(f"**Fecha Intradía Seleccionada:** {selected_intraday_date}")
st.sidebar.markdown(f"**Fecha de Cierre Anterior:** {selected_previous_date}")

# Function to fetch intraday data
@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday_data(ticker, intraday_date, interval="1m"):
  """
  Fetches the 1-minute interval intraday data for the selected date.
  """
  try:
      start = datetime.combine(intraday_date, datetime.min.time())
      end = start + timedelta(days=1)
      data = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
      if data.empty:
          return pd.DataFrame()
      return data
  except Exception as e:
      return pd.DataFrame()

# Function to fetch previous close
@st.cache_data(ttl=300, show_spinner=False)
def fetch_previous_close(ticker, previous_date):
  """
  Fetches the daily close price of the user-selected previous trading date.
  """
  try:
      data = yf.download(ticker, start=previous_date - timedelta(days=5), end=previous_date + timedelta(days=1), progress=False)
      if data.empty:
          return None, None
      # Filter to get the closest trading day on or before the previous_date
      data = data[data.index.date <= previous_date]
      if data.empty:
          return None, None
      previous_close = data['Adj Close'].iloc[-1]
      actual_previous_date = data.index.date[-1]
      return previous_close, actual_previous_date
  except Exception as e:
      return None, None

# Function to analyze volatility
def analyze_volatility(intraday_data, previous_close):
  """
  Analyzes how many times the price crosses from above to below the previous close and vice versa.
  """
  intraday_data = intraday_data.copy()
  intraday_data['Above_Previous_Close'] = intraday_data['Adj Close'] > previous_close
  intraday_data['Cross'] = intraday_data['Above_Previous_Close'].astype(int).diff().fillna(0)
  pos_to_neg = (intraday_data['Cross'] == -1).sum()  # Above to Below
  neg_to_pos = (intraday_data['Cross'] == 1).sum()   # Below to Above
  total_crossings = pos_to_neg + neg_to_pos
  return total_crossings, pos_to_neg, neg_to_pos

# Function to analyze last 30 days
def analyze_last_30_days(ticker, end_date):
  """
  Analyzes volatility for the last 30 trading days and calculates average and median crossings.
  """
  total_crossings_list = []
  pos_to_neg_list = []
  neg_to_pos_list = []
  daily_data = []

  current_date = end_date
  days_checked = 0
  trading_days_needed = 30

  while days_checked < trading_days_needed:
      previous_date = get_last_trading_day(current_date - timedelta(days=1))
      intraday_data = fetch_intraday_data(ticker, current_date)
      previous_close_result = fetch_previous_close(ticker, previous_date)

      if intraday_data.empty or previous_close_result[0] is None:
          current_date -= timedelta(days=1)
          continue

      previous_close, actual_previous_date = previous_close_result
      total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(intraday_data, previous_close)

      total_crossings_list.append(total_crossings)
      pos_to_neg_list.append(pos_to_neg)
      neg_to_pos_list.append(neg_to_pos)
      daily_data.append({
          'Fecha': current_date,
          'Cruces Totales': total_crossings,
          'Cruces Pos->Neg': pos_to_neg,
          'Cruces Neg->Pos': neg_to_pos
      })

      days_checked += 1
      current_date -= timedelta(days=1)

  if total_crossings_list:
      average_crossings = sum(total_crossings_list) / len(total_crossings_list)
      median_crossings = pd.Series(total_crossings_list).median()
      avg_pos_to_neg = sum(pos_to_neg_list) / len(pos_to_neg_list)
      avg_neg_to_pos = sum(neg_to_pos_list) / len(neg_to_pos_list)

      df_daily = pd.DataFrame(daily_data)

      # Identify extreme crossing days
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
  else:
      return None

# Initialize results list
results = []

# Header for results
if extend_analysis:
  st.subheader("Análisis Detallado de Cruces en los Últimos 30 Días")
else:
  st.subheader("Resultados de Volatilidad Intradía (1 Minuto)")

# Processing tickers with a single message and progress bar
with st.spinner('Procesando tickers...'):
  progress_bar = st.progress(0)
  total_tickers = len(tickers)
  for idx, ticker in enumerate(tickers):
      try:
          if extend_analysis:
              analysis = analyze_last_30_days(ticker, selected_intraday_date)

              if analysis is None:
                  st.warning(f"No se pudo realizar el análisis para {ticker}.")
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
              # Fetch intraday data
              intraday_data = fetch_intraday_data(ticker, selected_intraday_date)
              if intraday_data.empty:
                  st.warning(f"No hay datos intradía disponibles para {ticker} en {selected_intraday_date}.")
                  continue

              # Fetch previous close
              previous_close_result = fetch_previous_close(ticker, selected_previous_date)
              if previous_close_result[0] is None:
                  st.warning(f"No se pudo obtener el cierre anterior para {ticker}.")
                  continue

              previous_close, actual_previous_date = previous_close_result

              # Analyze volatility
              total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(intraday_data, previous_close)

              # Append results
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

  progress_bar.empty()  # Remove progress bar after completion

# Convert results to DataFrame
df_results = pd.DataFrame(results)

# Display results and charts
if extend_analysis:
  if not df_results.empty:
      st.dataframe(df_results)
      
      # Visualization: Promedio Cruces Totales (30 días)
      st.subheader("Promedio de Cruces Totales en los Últimos 30 Días")
      fig1 = df_results[['Ticker', 'Promedio Cruces Totales (30 días)']].set_index('Ticker')
      st.bar_chart(fig1)

      # Visualization: Promedio Cruces Pos->Neg y Neg->Pos (30 días)
      st.subheader("Promedio de Cruces Pos->Neg y Neg->Pos en los Últimos 30 Días")
      fig2 = df_results.set_index('Ticker')[['Promedio Cruces Pos->Neg (30 días)', 'Promedio Cruces Neg->Pos (30 días)']]
      st.bar_chart(fig2)
  else:
      st.warning("No se encontraron resultados para la extensión de análisis.")
else:
  if not df_results.empty:
      st.dataframe(df_results)
      
      # Visualization: Cruces Totales
      st.subheader("Número de Cruces de Precios Intradía (Totales)")
      fig = df_results[['Ticker', 'Cruces Totales']].set_index('Ticker')
      st.bar_chart(fig)
  else:
      st.warning("No se encontraron resultados para el análisis intradía.")

# Footer
st.markdown("---")
st.markdown("Desarrollado por [Tu Nombre](https://tuweb.com)")
