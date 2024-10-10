# Function to analyze last 30 days
def analyze_last_30_days(ticker, end_date):
  nyse = mcal.get_calendar('NYSE')
  end_date_ts = pd.Timestamp(end_date)  # Convert end_date to Timestamp
  trading_days = nyse.valid_days(start_date=end_date - timedelta(days=30), end_date=end_date).tz_localize(None)

  total_crossings_list = []
  pos_to_neg_list = []
  neg_to_pos_list = []
  daily_data = []

  days_checked = 0
  trading_days_needed = 20  # Limit to 20 trading days

  for current_date in trading_days[::-1]:
      if days_checked >= trading_days_needed:
          break

      if current_date > end_date_ts:  # Correct comparison
          continue

      previous_date = trading_days[trading_days < current_date][-1]

      intraday_data = fetch_intraday_data(ticker, current_date)
      previous_close_result = fetch_previous_close(ticker, previous_date)

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

      days_checked += 1

  if days_checked < trading_days_needed:
      st.warning(f"No se encontraron suficientes días de negociación para {ticker}. Se encontraron {days_checked} días.")
      return None

  if total_crossings_list:
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
  else:
      return None
