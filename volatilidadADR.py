   import streamlit as st
   import yfinance as yf
   import pandas as pd
   from datetime import datetime, timedelta
   import pytz
   import pandas_market_calendars as mcal
   import holidays
   from pandas.tseries.offsets import CustomBusinessDay

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

   # Define los días festivos de Argentina
   argentina_holidays = holidays.Argentina()

   # Define un día hábil personalizado que excluya los días festivos de Argentina
   arg_custom_bday = CustomBusinessDay(holidays=argentina_holidays)

   # Function to get trading days based on ticker set
   @st.cache_data
   def get_trading_days(start_date, end_date, ticker_set):
       if ticker_set == "ADRs":
           nyse = mcal.get_calendar('NYSE')
           trading_days = nyse.valid_days(start_date=start_date, end_date=end_date).tz_localize(None).to_pydatetime()
       else:
           # Para Merval, utilizamos el calendario de días hábiles personalizados
           trading_days = pd.date_range(start=start_date, end=end_date, freq=arg_custom_bday).to_pydatetime()
       return trading_days

   # Helper function to get the last trading day using the appropriate calendar
   @st.cache_data
   def get_last_trading_day(reference_date, ticker_set):
       # Buscamos hasta 10 días atrás para asegurarnos de encontrar el último día hábil
       start = reference_date - timedelta(days=10)
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
           ticker = ticker.upper()  # Convert to uppercase
           start = datetime.combine(intraday_date, datetime.min.time())
           end = start + timedelta(days=1)
           data = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
           if data.empty:
               return pd.DataFrame()
           return data
       except Exception as e:
           st.error(f"Error fetching intraday data para {ticker}: {e}")
           return pd.DataFrame()

   # Function to fetch previous close
   @st.cache_data(ttl=300, show_spinner=False)
   def fetch_previous_close(ticker, previous_date, ticker_set):
       try:
           ticker = ticker.upper()  # Convert to uppercase
           trading_days = get_trading_days(start_date=previous_date - timedelta(days=10), end_date=previous_date, ticker_set=ticker_set)
           
           trading_days = sorted(trading_days)
           
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
           st.error(f"Error fetching previous close para {ticker}: {e}")
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

       # Convertir end_date a datetime para la comparación
       end_datetime = datetime.combine(end_date, datetime.min.time())

       # Filtrar trading_days que sean <= end_date
       trading_days = [day for day in trading_days if day <= end_datetime]

       # Tomar los últimos 20 días de negociación dentro de los últimos 30 días calendario
       trading_days_sorted = sorted(trading_days)
       selected_trading_days = trading_days_sorted[-20:]

       # Construir el dataframe de comparación
       summary_data = pd.DataFrame(columns=["Fecha", "Variación %"])
       for date in selected_trading_days:
           try:
               date_close, _ = fetch_previous_close(ticker, date, ticker_set)
               if date_close is None:
                   continue  # Si no hay cierre para esta fecha, saltar
               
               # Encontrar el siguiente día hábil después de 'date'
               next_trading_day = get_last_trading_day(date + timedelta(days=1), ticker_set)
               if next_trading_day <= date:
                   continue  # Evitar ciclos infinitos en caso de error
               
               next_day_close, _ = fetch_previous_close(ticker, next_trading_day, ticker_set)
               
               if next_day_close is not None:
                   variation = (next_day_close / date_close - 1) * 100
                   summary_data = summary_data.append({"Fecha": next_trading_day, "Variación %": variation}, ignore_index=True)
           except Exception as e:
               st.error(f"Error analizando variación del {ticker} en {date}: {e}")
               continue
       return summary_data

   # Confirm analysis button action
   if confirm:
       intraday_summary = pd.DataFrame(columns=["Ticker", "Cruces", "Cruces Bajista -> Alcista", "Cruces Alcista -> Bajista"])
       for ticker in tickers:
           intraday_data = fetch_intraday_data(ticker, selected_intraday_date)
           if intraday_data.empty:
               st.warning(f"No hay datos disponibles para {ticker} en {selected_intraday_date}.")
               continue
           
           previous_close, actual_previous_date = fetch_previous_close(ticker, selected_previous_date, ticker_set_option)
           if previous_close is None:
               st.warning(f"No hay datos de cierre anterior para {ticker} en {selected_previous_date}.")
               continue

           # Analyze intraday volatility
           total_crossings, pos_to_neg, neg_to_pos = analyze_volatility(intraday_data, previous_close)
           intraday_summary = pd.concat([intraday_summary, pd.DataFrame({
               "Ticker": [ticker],
               "Cruces": [total_crossings],
               "Cruces Bajista -> Alcista": [neg_to_pos],
               "Cruces Alcista -> Bajista": [pos_to_neg]
           })], ignore_index=True)  

           # Display the results
           st.subheader(f"Resultados para {ticker}")
           st.write(f"Datos intradía disponibles para el {selected_intraday_date}")
           st.write(f"Cierre anterior: {previous_close} (fecha real: {actual_previous_date})")
           st.write(f"Cruces totales: {total_crossings}")
           st.write(f"Cruces bajista -> alcista: {neg_to_pos}")
           st.write(f"Cruces alcista -> bajista: {pos_to_neg}")

           # Plot the data if available
           if not intraday_data.empty:
               st.line_chart(intraday_data['Adj Close'])

       st.subheader("Resumen de Cruces")
       st.dataframe(intraday_summary)

       # If selected, analyze the last 30 days for the tickers
       if extend_analysis:
           for ticker in tickers:
               st.subheader(f"Análisis de los últimos 30 días para {ticker}")
               last_30_days_summary = analyze_last_30_days(ticker, selected_intraday_date, ticker_set_option)
               st.write(last_30_days_summary)
               st.line_chart(last_30_days_summary.set_index('Fecha')['Variación %'])
