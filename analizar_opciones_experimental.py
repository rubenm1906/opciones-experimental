import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests
from tabulate import tabulate
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración predeterminada
DEFAULT_CONFIG = {
    "MIN_RENTABILIDAD_ANUAL": float(os.getenv("MIN_RENTABILIDAD_ANUAL", "45.0")),
    "MAX_DIAS_VENCIMIENTO": int(os.getenv("MAX_DIAS_VENCIMIENTO", "45")),
    "MIN_DIFERENCIA_PORCENTUAL": float(os.getenv("MIN_DIFERENCIA_PORCENTUAL", "5.0")),
    "MIN_VOLATILIDAD_IMPLICITA": float(os.getenv("MIN_VOLATILIDAD_IMPLICITA", "35.0")),
    "MIN_VOLUMEN": int(os.getenv("MIN_VOLUMEN", "1")),
    "MIN_OPEN_INTEREST": int(os.getenv("MIN_OPEN_INTEREST", "1")),
    "FILTRO_TIPO_OPCION": os.getenv("FILTRO_TIPO_OPCION", "OTM"),
    "TOP_CONTRATOS": int(os.getenv("TOP_CONTRATOS", "5")),
    "FORCE_DISCORD_NOTIFICATION": os.getenv("FORCE_DISCORD_NOTIFICATION", "false").lower() == "true",
    "MIN_BID": float(os.getenv("MIN_BID", "0.99")),
    "ALERTA_RENTABILIDAD_ANUAL": float(os.getenv("ALERTA_RENTABILIDAD_ANUAL", "50.0")),
    "ALERTA_VOLATILIDAD_MINIMA": float(os.getenv("ALERTA_VOLATILIDAD_MINIMA", "50.0")),
}

# Configuración de grupos
GROUPS_CONFIG = {
    "7magnificas": {
        "tickers": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA"],
        "description": "Magnificas",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_7MAGNIFICAS", "URL_POR_DEFECTO")
    },
    "indices": {
        "tickers": ["SPY", "QQQ", "IWM", "DIA"],
        "description": "Índices",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_INDICES", "URL_POR_DEFECTO")
    },
    "shortlist": {
        "tickers": ["EPAM", "NFE", "GLNG", "GLOB", "ASTS",],
        "description": "Shortlist",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_SHORTLIST", "URL_POR_DEFECTO")
    }
}

def get_option_data_yahoo(ticker):
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        options_data = []
        current_price = stock.info.get('regularMarketPrice', stock.info.get('previousClose', 0))
        if current_price <= 0:
            raise ValueError(f"Precio actual de {ticker} no válido: ${current_price}")
        logger.info(f"Precio actual de {ticker}: ${current_price:.2f}")
        print(f"Precio actual de {ticker}: ${current_price:.2f}")

        for expiration in expirations:
            if not expiration:
                continue
            expiration_date = datetime.strptime(expiration, '%Y-%m-%d')
            days_to_expiration = (expiration_date - datetime.now()).days
            if days_to_expiration <= 0 or days_to_expiration > DEFAULT_CONFIG["MAX_DIAS_VENCIMIENTO"]:
                logger.debug(f"Expiración {expiration} descartada: {days_to_expiration} días")
                continue

            opt = stock.option_chain(expiration)
            chain = opt.puts
            for _, row in chain.iterrows():
                strike = row['strike']
                bid = row.get('bid', 0)
                if bid < DEFAULT_CONFIG["MIN_BID"]:
                    logger.debug(f"Opción descartada: bid ${bid:.2f} < {DEFAULT_CONFIG['MIN_BID']}")
                    continue

                implied_volatility = row.get('impliedVolatility', 0) * 100
                if implied_volatility < DEFAULT_CONFIG["MIN_VOLATILIDAD_IMPLICITA"]:
                    logger.debug(f"Opción descartada: volatilidad implícita {implied_volatility:.2f}% < {DEFAULT_CONFIG['MIN_VOLATILIDAD_IMPLICITA']}%")
                    continue

                last_price = row.get('lastPrice', 0)
                if last_price <= 0:
                    logger.debug(f"Opción descartada: último precio ${last_price:.2f} <= 0")
                    continue

                volume = row.get('volume', 0) or 0
                if volume < DEFAULT_CONFIG["MIN_VOLUMEN"]:
                    logger.debug(f"Opción descartada: volumen {volume} < {DEFAULT_CONFIG['MIN_VOLUMEN']}")
                    continue

                open_interest = row.get('openInterest', 0) or 0
                if open_interest < DEFAULT_CONFIG["MIN_OPEN_INTEREST"]:
                    logger.debug(f"Opción descartada: interés abierto {open_interest} < {DEFAULT_CONFIG['MIN_OPEN_INTEREST']}")
                    continue

                if DEFAULT_CONFIG["FILTRO_TIPO_OPCION"] == "OTM":
                    if strike >= current_price:
                        logger.debug(f"Opción descartada: put OTM, strike ${strike:.2f} >= precio actual ${current_price:.2f}")
                        continue
                elif DEFAULT_CONFIG["FILTRO_TIPO_OPCION"] == "ITM":
                    if strike < current_price:
                        logger.debug(f"Opción descartada: put ITM, strike ${strike:.2f} < precio actual ${current_price:.2f}")
                        continue

                break_even = strike - last_price
                percent_diff = ((current_price - break_even) / current_price) * 100
                if percent_diff < DEFAULT_CONFIG["MIN_DIFERENCIA_PORCENTUAL"]:
                    logger.debug(f"Opción descartada: diferencia porcentual {percent_diff:.2f}% < {DEFAULT_CONFIG['MIN_DIFERENCIA_PORCENTUAL']}%")
                    continue

                rentabilidad_diaria = (last_price * 100) / current_price
                rentabilidad_anual = rentabilidad_diaria * (365 / days_to_expiration)
                if rentabilidad_anual < DEFAULT_CONFIG["MIN_RENTABILIDAD_ANUAL"]:
                    logger.debug(f"Opción descartada: rentabilidad anualizada {rentabilidad_anual:.2f}% < {DEFAULT_CONFIG['MIN_RENTABILIDAD_ANUAL']}%")
                    continue

                options_data.append({
                    "ticker": ticker,
                    "type": "put",
                    "strike": strike,
                    "expiration": expiration,
                    "days_to_expiration": days_to_expiration,
                    "bid": bid,
                    "last_price": last_price,
                    "implied_volatility": implied_volatility,
                    "volume": volume,
                    "open_interest": open_interest,
                    "rentabilidad_diaria": rentabilidad_diaria,
                    "rentabilidad_anual": rentabilidad_anual,
                    "break_even": break_even,
                    "percent_diff": percent_diff,
                    "source": "Yahoo"
                })
        logger.info(f"Se encontraron {len(options_data)} opciones para {ticker} después de aplicar filtros")
        print(f"Se encontraron {len(options_data)} opciones para {ticker} después de aplicar filtros")
        return options_data
    except Exception as e:
        logger.error(f"Error obteniendo datos de Yahoo para {ticker}: {e}")
        print(f"Error obteniendo datos de Yahoo para {ticker}: {e}")
        return []

def get_option_data_finnhub(ticker):
    return []

def combine_options_data(yahoo_data, finnhub_data):
    combined = yahoo_data + finnhub_data
    return combined

def analyze_ticker(ticker):
    logger.info(f"Analizando {ticker}...")
    print(f"\n{'='*50}\nAnalizando ticker: {ticker}\n{'='*50}\n")
    yahoo_data = get_option_data_yahoo(ticker)
    finnhub_data = get_option_data_finnhub(ticker)
    logger.info(f"{len(yahoo_data)} opciones de Yahoo para {ticker}")
    logger.info(f"{len(finnhub_data)} opciones de Finnhub para {ticker}")
    logger.info(f"Combinadas {len(yahoo_data + finnhub_data)} opciones para {ticker}")
    print(f"{len(yahoo_data)} opciones de Yahoo para {ticker}")
    print(f"{len(finnhub_data)} opciones de Finnhub para {ticker}")
    print(f"Combinadas {len(yahoo_data + finnhub_data)} opciones para {ticker}")
    return combine_options_data(yahoo_data, finnhub_data)

def send_discord_notification(tickers_identificados, webhook_url):
    if not webhook_url or webhook_url == "URL_POR_DEFECTO":
        logger.error(f"Error: Webhook inválido: {webhook_url}")
        print(f"Error: Webhook inválido: {webhook_url}")
        return
    try:
        ticker_list = ", ".join(tickers_identificados) if tickers_identificados else "Ninguno"
        message = f"Se encontraron contratos que cumplen los filtros de alerta para los siguientes tickers: {ticker_list}"
        with open("Mejores_Contratos.txt", "rb") as f:
            files = {
                "file": ("Mejores_Contratos.txt", f, "text/plain")
            }
            payload = {
                "content": message
            }
            response = requests.post(webhook_url, data=payload, files=files)
            response.raise_for_status()
        logger.info("Notificación enviada a Discord")
        print("Notificación enviada a Discord")
    except Exception as e:
        logger.error(f"Error enviando notificación a Discord: {e}")
        print(f"Error enviando notificación a Discord: {e}")

def main():
    group_type = os.getenv("GROUP_TYPE", "7magnificas")
    if group_type not in GROUPS_CONFIG:
        logger.error(f"Grupo {group_type} no encontrado")
        print(f"Grupo {group_type} no encontrado")
        return

    group_config = GROUPS_CONFIG[group_type]
    tickers = group_config["tickers"]
    description = group_config["description"]
    webhook_url = group_config["webhook"]
    logger.info(f"Webhook URL para {description}: {webhook_url}")
    print(f"Webhook URL para {description}: {webhook_url}")

    all_options = []
    errors = []
    best_contracts_by_ticker = {}  # Para guardar los contratos que cumplen las reglas de alerta
    filtered_contracts_by_ticker = {}  # Para guardar todos los contratos que cumplen los filtros iniciales
    summary_message = f"==================================================\n"
    summary_message += f"Análisis de Opciones - {description}\n"
    summary_message += f"==================================================\n\n"

    for ticker in tickers:
        try:
            options = analyze_ticker(ticker)
            if not options:
                logger.info(f"No se encontraron opciones para {ticker}")
                print(f"No se encontraron opciones para {ticker}")
                summary_message += f"==================================================\n"
                summary_message += f"Analizando ticker: {ticker}\n"
                summary_message += f"==================================================\n\n"
                summary_message += f"No se encontraron opciones para {ticker}.\n\n"
                continue

            all_options.extend(options)

            df_ticker = pd.DataFrame(options)
            if df_ticker.empty:
                logger.info(f"No hay opciones válidas para {ticker} después de aplicar filtros")
                print(f"No hay opciones válidas para {ticker} después de aplicar filtros")
                summary_message += f"==================================================\n"
                summary_message += f"Analizando ticker: {ticker}\n"
                summary_message += f"==================================================\n\n"
                summary_message += f"No hay opciones válidas para {ticker} después de aplicar filtros.\n\n"
                continue

            # Ordenar todas las opciones filtradas por rentabilidad anual (descendente), días al vencimiento (ascendente), diferencia porcentual (descendente)
            df_ticker = df_ticker.sort_values(
                by=["rentabilidad_anual", "days_to_expiration", "percent_diff"],
                ascending=[False, True, False]
            )

            # Guardar todas las opciones que cumplen los filtros iniciales (para mostrarlas)
            filtered_contracts = df_ticker.head(DEFAULT_CONFIG["TOP_CONTRATOS"])
            filtered_contracts_by_ticker[ticker] = filtered_contracts

            # Filtrar por reglas de alerta (solo para notificación a Discord)
            best_contracts = df_ticker[
                (df_ticker["rentabilidad_anual"] >= DEFAULT_CONFIG["ALERTA_RENTABILIDAD_ANUAL"]) &
                (df_ticker["implied_volatility"] >= DEFAULT_CONFIG["ALERTA_VOLATILIDAD_MINIMA"])
            ].head(DEFAULT_CONFIG["TOP_CONTRATOS"])
            best_contracts_by_ticker[ticker] = best_contracts

            stock = yf.Ticker(ticker)
            current_price = stock.info.get('regularMarketPrice', stock.info.get('previousClose', 0))
            min_52_week = stock.info.get('fiftyTwoWeekLow', 0)
            max_52_week = stock.info.get('fiftyTwoWeekHigh', 0)

            ticker_message = f"==================================================\n"
            ticker_message += f"Analizando ticker: {ticker}\n"
            ticker_message += f"==================================================\n\n"
            ticker_message += f"Precio del subyacente ({ticker}): ${current_price:.2f}\n"
            ticker_message += f"Mínimo de las últimas 52 semanas: ${min_52_week:.2f}\n"
            ticker_message += f"Máximo de las últimas 52 semanas: ${max_52_week:.2f}\n"
            ticker_message += f"{len(get_option_data_yahoo(ticker))} opciones de Yahoo para {ticker}\n"
            ticker_message += f"{len(get_option_data_finnhub(ticker))} opciones de Finnhub para {ticker}\n"
            ticker_message += f"Combinadas {len(options)} opciones para {ticker}\n"
            ticker_message += f"Fuentes: Yahoo Finance\n"
            ticker_message += f"Errores: Ninguno\n"

            print(f"Precio del subyacente ({ticker}): ${current_price:.2f}")
            print(f"Mínimo de las últimas 52 semanas: ${min_52_week:.2f}")
            print(f"Máximo de las últimas 52 semanas: ${max_52_week:.2f}")
            print(f"{len(get_option_data_yahoo(ticker))} opciones de Yahoo para {ticker}")
            print(f"{len(get_option_data_finnhub(ticker))} opciones de Finnhub para {ticker}")
            print(f"Combinadas {len(options)} opciones para {ticker}")
            print(f"Fuentes: Yahoo Finance")
            print(f"Errores: Ninguno")

            if not filtered_contracts.empty:
                tipo_opcion_texto = "Out of the Money" if DEFAULT_CONFIG["FILTRO_TIPO_OPCION"] == "OTM" else "In the Money"
                ticker_message += f"\nOpciones PUT {tipo_opcion_texto} con rentabilidad anual > {DEFAULT_CONFIG['MIN_RENTABILIDAD_ANUAL']}% y diferencia % > {DEFAULT_CONFIG['MIN_DIFERENCIA_PORCENTUAL']}% (máximo {DEFAULT_CONFIG['MAX_DIAS_VENCIMIENTO']} días, volumen > {DEFAULT_CONFIG['MIN_VOLUMEN']}, volatilidad >= {DEFAULT_CONFIG['MIN_VOLATILIDAD_IMPLICITA']}%, interés abierto > {DEFAULT_CONFIG['MIN_OPEN_INTEREST']}, bid >= ${DEFAULT_CONFIG['MIN_BID']}):\n"
                print(f"\nOpciones PUT {tipo_opcion_texto} con rentabilidad anual > {DEFAULT_CONFIG['MIN_RENTABILIDAD_ANUAL']}% y diferencia % > {DEFAULT_CONFIG['MIN_DIFERENCIA_PORCENTUAL']}% (máximo {DEFAULT_CONFIG['MAX_DIAS_VENCIMIENTO']} días, volumen > {DEFAULT_CONFIG['MIN_VOLUMEN']}, volatilidad >= {DEFAULT_CONFIG['MIN_VOLATILIDAD_IMPLICITA']}%, interés abierto > {DEFAULT_CONFIG['MIN_OPEN_INTEREST']}, bid >= ${DEFAULT_CONFIG['MIN_BID']}):")

                table_data = filtered_contracts[[
                    "strike", "last_price", "bid", "expiration", "days_to_expiration",
                    "rentabilidad_diaria", "rentabilidad_anual", "break_even", "percent_diff",
                    "implied_volatility", "volume", "open_interest", "source"
                ]].copy()
                table_data.columns = [
                    "Strike", "Last Closed", "Bid", "Vencimiento", "Días Venc.",
                    "Rent. Diaria", "Rent. Anual", "Break-even", "Dif. % (Suby.-Break.)",
                    "Volatilidad Implícita", "Volumen", "Interés Abierto", "Fuente"
                ]
                table = tabulate(table_data, headers="keys", tablefmt="grid", showindex=False)
                ticker_message += f"\n{table}\n"
                print(table)
            else:
                ticker_message += f"No se encontraron contratos que cumplan los criterios para {ticker}.\n"
                print(f"No se encontraron contratos que cumplan los criterios para {ticker}.")

            summary_message += ticker_message + "\n"

        except Exception as e:
            errors.append(f"{ticker}: {str(e)}")
            logger.error(f"Error procesando {ticker}: {e}")
            print(f"Error procesando {ticker}: {e}")
            summary_message += f"==================================================\n"
            summary_message += f"Analizando ticker: {ticker}\n"
            summary_message += f"==================================================\n\n"
            summary_message += f"Error procesando {ticker}: {str(e)}\n\n"

    if all_options:
        df_all = pd.DataFrame(all_options)
        df_all.to_csv("todas_las_opciones.csv", index=False)
    else:
        logger.info("No se encontraron opciones que cumplan con los criterios para ningún ticker.")
        print("No se encontraron opciones que cumplan con los criterios para ningún ticker.")
        summary_message += "No se encontraron opciones que cumplan con los criterios para ningún ticker.\n"

    # Guardar los mejores contratos (que cumplen las reglas de alerta) en un archivo
    with open("Mejores_Contratos.txt", "w") as f:
        f.write(f"Mejores Contratos por Ticker (Mayor Rentabilidad Anual, Menor Tiempo, Mayor Diferencia %):\n{'='*50}\n")
        for ticker, best_contracts in best_contracts_by_ticker.items():
            if not best_contracts.empty:
                f.write(f"\nTicker: {ticker}\n{'-'*30}\n")
                for i, row in best_contracts.iterrows():
                    f.write(f"Contrato {i+1}:\n")
                    f.write(f"  Ticker: {ticker}\n")
                    f.write(f"  Strike: ${row['strike']:.2f}\n")
                    f.write(f"  Last Closed: ${row['last_price']:.2f}\n")
                    f.write(f"  Bid: ${row['bid']:.2f}\n")
                    f.write(f"  Vencimiento: {row['expiration']}\n")
                    f.write(f"  Días Venc.: {row['days_to_expiration']}\n")
                    f.write(f"  Rent. Diaria: {row['rentabilidad_diaria']:.2f}%\n")
                    f.write(f"  Rent. Anual: {row['rentabilidad_anual']:.2f}%\n")
                    f.write(f"  Break-even: ${row['break_even']:.2f}\n")
                    f.write(f"  Dif. % (Suby.-Break.): {row['percent_diff']:.2f}%\n")
                    f.write(f"  Volatilidad Implícita: {row['implied_volatility']:.2f}%\n")
                    f.write(f"  Volumen: {row['volume']}\n")
                    f.write(f"  Interés Abierto: {row['open_interest']}\n")
                    f.write(f"  Fuente: {row['source']}\n")
                    f.write("\n")

    # Generar mejores_contratos.csv (solo los que cumplen las reglas de alerta)
    headers_csv = [
        "Ticker", "Strike", "Last Closed", "Bid", "Vencimiento", "Días Venc.",
        "Rent. Diaria", "Rent. Anual", "Break-even", "Dif. % (Suby.-Break.)",
        "Volatilidad Implícita", "Volumen", "Interés Abierto", "Fuente"
    ]
    best_contracts_data = []
    for ticker, best_contracts in best_contracts_by_ticker.items():
        if not best_contracts.empty:
            for _, row in best_contracts.iterrows():
                best_contracts_data.append([
                    ticker,
                    f"${row['strike']:.2f}",
                    f"${row['last_price']:.2f}",
                    f"${row['bid']:.2f}",
                    row['expiration'],
                    row['days_to_expiration'],
                    f"{row['rentabilidad_diaria']:.2f}%",
                    f"{row['rentabilidad_anual']:.2f}%",
                    f"${row['break_even']:.2f}",
                    f"{row['percent_diff']:.2f}%",
                    f"{row['implied_volatility']:.2f}%",
                    row['volume'],
                    row['open_interest'],
                    row['source']
                ])
    df_best = pd.DataFrame(best_contracts_data, columns=headers_csv)
    df_best.to_csv("mejores_contratos.csv", index=False)

    summary_message += f"Errores: {', '.join(errors) if errors else 'Ninguno'}\n"
    summary_message += "Resultados guardados.\n"

    with open("resultados.txt", "w") as f:
        f.write(summary_message)

    # Enviar notificación a Discord solo si hay contratos que cumplen las reglas de alerta
    tickers_identificados = [ticker for ticker, best_contracts in best_contracts_by_ticker.items() if not best_contracts.empty]
    if DEFAULT_CONFIG["FORCE_DISCORD_NOTIFICATION"] or tickers_identificados:
        logger.debug(f"Enviando a {webhook_url} para {description}")
        print(f"Enviando notificación a Discord para {description}")
        send_discord_notification(tickers_identificados, webhook_url)

if __name__ == "__main__":
    main()
