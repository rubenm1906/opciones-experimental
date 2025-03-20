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
    "FILTRO_TIPO_OPCION": os.getenv("FILTRO_TIPO_OPCION", "OTM"),
    "TOP_CONTRATOS": int(os.getenv("TOP_CONTRATOS", "5")),
    "FORCE_DISCORD_NOTIFICATION": os.getenv("FORCE_DISCORD_NOTIFICATION", "false").lower() == "true",
    "MIN_BID": float(os.getenv("MIN_BID", "0.99")),
}

# Configuración de grupos
GROUPS_CONFIG = {
    "7magnificas": {
        "tickers": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA"],
        "description": "Magnificas",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_7MAGNIFICAS", "URL_POR_DEFECTO")
    },
    "indices": {
        "tickers": ["SPY", "QQQ", "IWM"],
        "description": "Índices",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_INDICES", "URL_POR_DEFECTO")
    },
    "shortlist": {
        "tickers": ["NA9.DE", "TEP.PA", "GOOGL", "EPAM", "NFE", "GLNG", "GLOB", "NVDA"],
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
        logger.info(f"Precio actual de {ticker}: ${current_price:.2f}")

        for expiration in expirations:
            if not expiration:
                continue
            expiration_date = datetime.strptime(expiration, '%Y-%m-%d')
            days_to_expiration = (expiration_date - datetime.now()).days
            if days_to_expiration > DEFAULT_CONFIG["MAX_DIAS_VENCIMIENTO"]:
                logger.debug(f"Expiración {expiration} descartada: {days_to_expiration} días > {DEFAULT_CONFIG['MAX_DIAS_VENCIMIENTO']}")
                continue

            opt = stock.option_chain(expiration)
            for option_type, chain in [("call", opt.calls), ("put", opt.puts)]:
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

                    percent_diff = ((strike - current_price) / current_price * 100) if option_type == "call" else ((current_price - strike) / current_price * 100)
                    if DEFAULT_CONFIG["FILTRO_TIPO_OPCION"] == "OTM":
                        if option_type == "call" and strike <= current_price:
                            logger.debug(f"Opción descartada: call OTM, strike ${strike:.2f} <= precio actual ${current_price:.2f}")
                            continue
                        if option_type == "put" and strike >= current_price:
                            logger.debug(f"Opción descartada: put OTM, strike ${strike:.2f} >= precio actual ${current_price:.2f}")
                            continue
                    elif DEFAULT_CONFIG["FILTRO_TIPO_OPCION"] == "ITM":
                        if option_type == "call" and strike >= current_price:
                            logger.debug(f"Opción descartada: call ITM, strike ${strike:.2f} >= precio actual ${current_price:.2f}")
                            continue
                        if option_type == "put" and strike <= current_price:
                            logger.debug(f"Opción descartada: put ITM, strike ${strike:.2f} <= precio actual ${current_price:.2f}")
                            continue

                    if abs(percent_diff) < DEFAULT_CONFIG["MIN_DIFERENCIA_PORCENTUAL"]:
                        logger.debug(f"Opción descartada: diferencia porcentual {abs(percent_diff):.2f}% < {DEFAULT_CONFIG['MIN_DIFERENCIA_PORCENTUAL']}%")
                        continue

                    annualized_return = (last_price / current_price) * (365 / days_to_expiration) * 100
                    if annualized_return < DEFAULT_CONFIG["MIN_RENTABILIDAD_ANUAL"]:
                        logger.debug(f"Opción descartada: rentabilidad anualizada {annualized_return:.2f}% < {DEFAULT_CONFIG['MIN_RENTABILIDAD_ANUAL']}%")
                        continue

                    options_data.append({
                        "ticker": ticker,
                        "type": option_type,
                        "strike": strike,
                        "expiration": expiration,
                        "days_to_expiration": days_to_expiration,
                        "bid": bid,
                        "last_price": last_price,
                        "implied_volatility": implied_volatility,
                        "percent_diff": percent_diff,
                        "annualized_return": annualized_return,
                        "source": "Yahoo"
                    })
        logger.info(f"Se encontraron {len(options_data)} opciones para {ticker} después de aplicar filtros")
        return options_data
    except Exception as e:
        logger.error(f"Error obteniendo datos de Yahoo para {ticker}: {e}")
        return []

def get_option_data_finnhub(ticker):
    # Placeholder para Finnhub (requiere API key y configuración adicional)
    # Por ahora, devolvemos una lista vacía para evitar errores
    return []

def combine_options_data(yahoo_data, finnhub_data):
    combined = yahoo_data + finnhub_data
    return combined

def analyze_ticker(ticker):
    logger.info(f"Analizando {ticker}...")
    yahoo_data = get_option_data_yahoo(ticker)
    finnhub_data = get_option_data_finnhub(ticker)
    logger.info(f"{len(yahoo_data)} opciones de Yahoo para {ticker}")
    logger.info(f"{len(finnhub_data)} opciones de Finnhub para {ticker}")
    combined_data = combine_options_data(yahoo_data, finnhub_data)
    logger.info(f"Combinadas {len(combined_data)} opciones para {ticker}")
    return combined_data

def send_discord_notification(message, webhook_url):
    if not webhook_url or webhook_url == "URL_POR_DEFECTO":
        logger.error(f"Error: Webhook inválido: {webhook_url}")
        return
    try:
        data = {"content": message}
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        logger.info("Notificación enviada a Discord")
    except Exception as e:
        logger.error(f"Error enviando notificación a Discord: {e}")

def main():
    group_type = os.getenv("GROUP_TYPE", "7magnificas")
    if group_type not in GROUPS_CONFIG:
        logger.error(f"Grupo {group_type} no encontrado")
        return

    group_config = GROUPS_CONFIG[group_type]
    tickers = group_config["tickers"]
    description = group_config["description"]
    webhook_url = group_config["webhook"]
    logger.info(f"Webhook URL para {description}: {webhook_url}")

    all_options = []
    errors = []
    best_contracts_by_ticker = {}
    summary_message = f"==================================================\n"
    summary_message += f"Análisis de Opciones - {description}\n"
    summary_message += f"==================================================\n\n"

    # Procesar cada ticker individualmente
    for ticker in tickers:
        try:
            # Obtener opciones para el ticker
            options = analyze_ticker(ticker)
            if not options:
                logger.info(f"No se encontraron opciones para {ticker}")
                continue

            # Agregar las opciones al conjunto total (para todas_las_opciones.csv)
            all_options.extend(options)

            # Crear un DataFrame para las opciones del ticker
            df_ticker = pd.DataFrame(options)
            if df_ticker.empty:
                logger.info(f"No hay opciones válidas para {ticker} después de aplicar filtros")
                continue

            # Calcular los mejores contratos para este ticker
            best_contracts = df_ticker.sort_values(by="annualized_return", ascending=False).head(DEFAULT_CONFIG["TOP_CONTRATOS"])
            best_contracts_by_ticker[ticker] = best_contracts

            # Obtener información del ticker (precio, 52 semanas, etc.)
            stock = yf.Ticker(ticker)
            current_price = stock.info.get('regularMarketPrice', stock.info.get('previousClose', 0))
            min_52_week = stock.info.get('fiftyTwoWeekLow', 0)
            max_52_week = stock.info.get('fiftyTwoWeekHigh', 0)

            # Generar el mensaje para este ticker
            ticker_message = f"**{ticker}**\n"
            ticker_message += f"Precio: ${current_price:.2f}\n"
            ticker_message += f"Min 52s: ${min_52_week:.2f}\n"
            ticker_message += f"Max 52s: ${max_52_week:.2f}\n"
            ticker_message += f"{len(get_option_data_yahoo(ticker))} opciones de Yahoo para {ticker}\n"
            ticker_message += f"{len(get_option_data_finnhub(ticker))} opciones de Finnhub para {ticker}\n"
            ticker_message += f"Combinadas {len(options)} opciones para {ticker}\n"
            ticker_message += f"Fuentes: Yahoo Finance\n"

            if not best_contracts.empty:
                table = tabulate(best_contracts, headers="keys", tablefmt="pipe", showindex=False)
                ticker_message += f"\n**Mejores Contratos para {ticker}:**\n```\n{table}\n```\n"
            else:
                ticker_message += f"No se encontraron contratos que cumplan los criterios para {ticker}.\n"

            summary_message += ticker_message + "\n"

        except Exception as e:
            errors.append(f"{ticker}: {str(e)}")
            logger.error(f"Error procesando {ticker}: {e}")

    # Guardar todas las opciones en un archivo
    if all_options:
        df_all = pd.DataFrame(all_options)
        df_all.to_csv("todas_las_opciones.csv", index=False)
    else:
        logger.info("No se encontraron opciones que cumplan con los criterios para ningún ticker.")
        summary_message += "No se encontraron opciones que cumplan con los criterios para ningún ticker.\n"

    # Guardar los mejores contratos en un archivo
    with open("Mejores_Contratos.txt", "w") as f:
        for ticker, best_contracts in best_contracts_by_ticker.items():
            if not best_contracts.empty:
                f.write(f"Mejores Contratos para {ticker}:\n")
                table = tabulate(best_contracts, headers="keys", tablefmt="pipe", showindex=False)
                f.write(table + "\n\n")

    # Agregar errores al mensaje
    summary_message += f"Errores: {', '.join(errors) if errors else 'Ninguno'}\n"
    summary_message += "Resultados guardados.\n"

    # Guardar el resumen en un archivo
    with open("resultados.txt", "w") as f:
        f.write(summary_message)

    # Enviar notificación a Discord si hay mejores contratos o si se fuerza la notificación
    has_best_contracts = any(not best_contracts.empty for best_contracts in best_contracts_by_ticker.values())
    if DEFAULT_CONFIG["FORCE_DISCORD_NOTIFICATION"] or has_best_contracts:
        logger.debug(f"Enviando a {webhook_url} para {description}")
        send_discord_notification(summary_message, webhook_url)

if __name__ == "__main__":
    main()
