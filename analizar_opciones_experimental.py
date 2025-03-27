import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from tabulate import tabulate
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lista estática de tickers del NASDAQ-100 (como solución temporal)
NASDAQ_100_TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "PEP", "COST", "CSCO",
    "TMUS", "CMCSA", "INTC", "AMD", "QCOM", "TXN", "AMGN", "HON", "INTU", "SBUX",
    "GILD", "MDLZ", "ADBE", "NFLX", "PYPL", "ASML", "SNPS", "CDNS", "MRNA", "PANW",
    "REGN", "ADP", "VRTX", "LRCX", "CSX", "MU", "FISV", "BIIB", "KLAC", "AEP",
    "MAR", "ORLY", "KDP", "MNST", "FTNT", "ADSK", "KHC", "ODFL", "MCHP", "IDXX",
    "CTAS", "EXC", "PCAR", "WBA", "ROST", "DXCM", "ILMN", "WBD", "EA", "FAST",
    "VRSK", "CPRT", "BKR", "XEL", "ANSS", "TEAM", "DLTR", "WDAY", "PAYX", "SBAC",
    "CTSH", "VRSN", "SWKS", "MTCH", "INCY", "TTD", "ZM", "SIRI", "NTES", "EBAY",
    "LULU", "ALGN", "JD", "SGEN", "OKTA", "CDW", "ZS", "CHTR", "ULTA", "CINF",
    "NDAQ", "TTWO", "ON", "ENPH", "CEG", "FANG", "GFS", "GEHC"
]

# Configuración predeterminada para todos los grupos (valores por defecto)
BASE_CONFIG = {
    "MIN_RENTABILIDAD_ANUAL": 45.0,
    "MAX_DIAS_VENCIMIENTO": 45,
    "MIN_DIFERENCIA_PORCENTUAL": 5.0,
    "MIN_VOLATILIDAD_IMPLICITA": 35.0,
    "MIN_VOLUMEN": 1,
    "MIN_OPEN_INTEREST": 1,
    "FILTRO_TIPO_OPCION": "OTM",
    "TOP_CONTRATOS": 5,
    "FORCE_DISCORD_NOTIFICATION": False,
    "MIN_BID": 0.99,
    "ALERTA_RENTABILIDAD_ANUAL": 50.0,
    "ALERTA_VOLATILIDAD_MINIMA": 50.0,
}

# Configuración de grupos (cada grupo puede tener su propia configuración)
GROUPS_CONFIG = {
    "7magnificas": {
        "tickers": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA"],
        "description": "Magnificas",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_7MAGNIFICAS", "URL_POR_DEFECTO"),
        "config": {
            "MIN_RENTABILIDAD_ANUAL": float(os.getenv("MIN_RENTABILIDAD_ANUAL", BASE_CONFIG["MIN_RENTABILIDAD_ANUAL"])),
            "MAX_DIAS_VENCIMIENTO": int(os.getenv("MAX_DIAS_VENCIMIENTO", BASE_CONFIG["MAX_DIAS_VENCIMIENTO"])),
            "MIN_DIFERENCIA_PORCENTUAL": float(os.getenv("MIN_DIFERENCIA_PORCENTUAL", BASE_CONFIG["MIN_DIFERENCIA_PORCENTUAL"])),
            "MIN_VOLATILIDAD_IMPLICITA": float(os.getenv("MIN_VOLATILIDAD_IMPLICITA", BASE_CONFIG["MIN_VOLATILIDAD_IMPLICITA"])),
            "MIN_VOLUMEN": int(os.getenv("MIN_VOLUMEN", BASE_CONFIG["MIN_VOLUMEN"])),
            "MIN_OPEN_INTEREST": int(os.getenv("MIN_OPEN_INTEREST", BASE_CONFIG["MIN_OPEN_INTEREST"])),
            "FILTRO_TIPO_OPCION": os.getenv("FILTRO_TIPO_OPCION", BASE_CONFIG["FILTRO_TIPO_OPCION"]),
            "TOP_CONTRATOS": int(os.getenv("TOP_CONTRATOS", BASE_CONFIG["TOP_CONTRATOS"])),
            "FORCE_DISCORD_NOTIFICATION": os.getenv("FORCE_DISCORD_NOTIFICATION", str(BASE_CONFIG["FORCE_DISCORD_NOTIFICATION"])).lower() == "true",
            "MIN_BID": float(os.getenv("MIN_BID", BASE_CONFIG["MIN_BID"])),
            "ALERTA_RENTABILIDAD_ANUAL": float(os.getenv("ALERTA_RENTABILIDAD_ANUAL", BASE_CONFIG["ALERTA_RENTABILIDAD_ANUAL"])),
            "ALERTA_VOLATILIDAD_MINIMA": float(os.getenv("ALERTA_VOLATILIDAD_MINIMA", BASE_CONFIG["ALERTA_VOLATILIDAD_MINIMA"])),
        }
    },
    "indices": {
        "tickers": ["SPY", "QQQ", "IWM", "DIA"],
        "description": "Índices",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_INDICES", "URL_POR_DEFECTO"),
        "config": {
            "MIN_RENTABILIDAD_ANUAL": float(os.getenv("MIN_RENTABILIDAD_ANUAL", BASE_CONFIG["MIN_RENTABILIDAD_ANUAL"])),
            "MAX_DIAS_VENCIMIENTO": int(os.getenv("MAX_DIAS_VENCIMIENTO", BASE_CONFIG["MAX_DIAS_VENCIMIENTO"])),
            "MIN_DIFERENCIA_PORCENTUAL": float(os.getenv("MIN_DIFERENCIA_PORCENTUAL", BASE_CONFIG["MIN_DIFERENCIA_PORCENTUAL"])),
            "MIN_VOLATILIDAD_IMPLICITA": float(os.getenv("MIN_VOLATILIDAD_IMPLICITA", BASE_CONFIG["MIN_VOLATILIDAD_IMPLICITA"])),
            "MIN_VOLUMEN": int(os.getenv("MIN_VOLUMEN", BASE_CONFIG["MIN_VOLUMEN"])),
            "MIN_OPEN_INTEREST": int(os.getenv("MIN_OPEN_INTEREST", BASE_CONFIG["MIN_OPEN_INTEREST"])),
            "FILTRO_TIPO_OPCION": os.getenv("FILTRO_TIPO_OPCION", BASE_CONFIG["FILTRO_TIPO_OPCION"]),
            "TOP_CONTRATOS": int(os.getenv("TOP_CONTRATOS", BASE_CONFIG["TOP_CONTRATOS"])),
            "FORCE_DISCORD_NOTIFICATION": os.getenv("FORCE_DISCORD_NOTIFICATION", str(BASE_CONFIG["FORCE_DISCORD_NOTIFICATION"])).lower() == "true",
            "MIN_BID": float(os.getenv("MIN_BID", BASE_CONFIG["MIN_BID"])),
            "ALERTA_RENTABILIDAD_ANUAL": float(os.getenv("ALERTA_RENTABILIDAD_ANUAL", BASE_CONFIG["ALERTA_RENTABILIDAD_ANUAL"])),
            "ALERTA_VOLATILIDAD_MINIMA": float(os.getenv("ALERTA_VOLATILIDAD_MINIMA", BASE_CONFIG["ALERTA_VOLATILIDAD_MINIMA"])),
        }
    },
    "shortlist": {
        "tickers": ["EPAM", "NFE", "GLNG", "GLOB", "ASTS"],
        "description": "Shortlist",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_SHORTLIST", "URL_POR_DEFECTO"),
        "config": {
            "MIN_RENTABILIDAD_ANUAL": float(os.getenv("MIN_RENTABILIDAD_ANUAL", BASE_CONFIG["MIN_RENTABILIDAD_ANUAL"])),
            "MAX_DIAS_VENCIMIENTO": int(os.getenv("MAX_DIAS_VENCIMIENTO", BASE_CONFIG["MAX_DIAS_VENCIMIENTO"])),
            "MIN_DIFERENCIA_PORCENTUAL": float(os.getenv("MIN_DIFERENCIA_PORCENTUAL", BASE_CONFIG["MIN_DIFERENCIA_PORCENTUAL"])),
            "MIN_VOLATILIDAD_IMPLICITA": float(os.getenv("MIN_VOLATILIDAD_IMPLICITA", BASE_CONFIG["MIN_VOLATILIDAD_IMPLICITA"])),
            "MIN_VOLUMEN": int(os.getenv("MIN_VOLUMEN", BASE_CONFIG["MIN_VOLUMEN"])),
            "MIN_OPEN_INTEREST": int(os.getenv("MIN_OPEN_INTEREST", BASE_CONFIG["MIN_OPEN_INTEREST"])),
            "FILTRO_TIPO_OPCION": os.getenv("FILTRO_TIPO_OPCION", BASE_CONFIG["FILTRO_TIPO_OPCION"]),
            "TOP_CONTRATOS": int(os.getenv("TOP_CONTRATOS", BASE_CONFIG["TOP_CONTRATOS"])),
            "FORCE_DISCORD_NOTIFICATION": os.getenv("FORCE_DISCORD_NOTIFICATION", str(BASE_CONFIG["FORCE_DISCORD_NOTIFICATION"])).lower() == "true",
            "MIN_BID": float(os.getenv("MIN_BID", BASE_CONFIG["MIN_BID"])),
            "ALERTA_RENTABILIDAD_ANUAL": float(os.getenv("ALERTA_RENTABILIDAD_ANUAL", BASE_CONFIG["ALERTA_RENTABILIDAD_ANUAL"])),
            "ALERTA_VOLATILIDAD_MINIMA": float(os.getenv("ALERTA_VOLATILIDAD_MINIMA", BASE_CONFIG["ALERTA_VOLATILIDAD_MINIMA"])),
        }
    },
    "european_companies": {
        "tickers": ["ASML", "SAP", "UL", "TTE"],
        "description": "Empresas Europeas",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_EUROPEAN", "URL_POR_DEFECTO"),
        "config": {
            "MIN_RENTABILIDAD_ANUAL": 30.0,
            "MAX_DIAS_VENCIMIENTO": 45,
            "MIN_DIFERENCIA_PORCENTUAL": 3.0,
            "MIN_VOLATILIDAD_IMPLICITA": 25.0,
            "MIN_VOLUMEN": 1,
            "MIN_OPEN_INTEREST": 1,
            "FILTRO_TIPO_OPCION": "OTM",
            "TOP_CONTRATOS": 5,
            "FORCE_DISCORD_NOTIFICATION": False,
            "MIN_BID": 0.99,
            "ALERTA_RENTABILIDAD_ANUAL": 35.0,
            "ALERTA_VOLATILIDAD_MINIMA": 30.0
        }
    },
    "nasdaq_top_volatility": {
        "dynamic_source": {"index": "nasdaq100"},
        "dynamic_criteria": {
            "top": 15,
            "metric": "implied_volatility",
            "prefer_iv_over_hist_vol": True,
            "min_iv": 35.0,
            "min_volume": 1000000,
            "hist_vol_period": 30  # Volvemos a 30, pero ahora el script manejará dinámicamente los datos disponibles
        },
        "description": "NASDAQ-100 Top 15 Volatilidad Implícita",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_NASDAQ_TOP_VOLATILITY", "URL_POR_DEFECTO"),
        "config": {
            "MIN_RENTABILIDAD_ANUAL": 45.0,
            "MAX_DIAS_VENCIMIENTO": 45,
            "MIN_DIFERENCIA_PORCENTUAL": 5.0,
            "MIN_VOLATILIDAD_IMPLICITA": 35.0,
            "MIN_VOLUMEN": 1,
            "MIN_OPEN_INTEREST": 1,
            "FILTRO_TIPO_OPCION": "OTM",
            "TOP_CONTRATOS": 5,
            "FORCE_DISCORD_NOTIFICATION": False,
            "MIN_BID": 0.99,
            "ALERTA_RENTABILIDAD_ANUAL": 55.0,
            "ALERTA_VOLATILIDAD_MINIMA": 40.0
        }
    }
}

def calculate_volatility_metrics(ticker, max_days=45, hist_vol_period=30):
    """
    Calcula la volatilidad implícita promedio (IV) y la volatilidad histórica (Hist Vol) de un ticker.
    Retorna un diccionario con IV, Hist Vol y el volumen del subyacente.
    """
    try:
        stock = yf.Ticker(ticker)
        # Obtener el precio actual y el volumen del subyacente
        current_price = stock.info.get('regularMarketPrice', stock.info.get('previousClose', 0))
        volume = stock.info.get('averageVolume', 0)
        if current_price <= 0:
            logger.info(f"{ticker}: Precio actual no válido: ${current_price}")
            print(f"{ticker}: Precio actual no válido: ${current_price}")
            return None

        logger.info(f"{ticker}: Precio actual: ${current_price:.2f}, Volumen promedio: {volume}")
        print(f"{ticker}: Precio actual: ${current_price:.2f}, Volumen promedio: {volume}")

        # Calcular volatilidad implícita promedio (IV) usando opciones ATM
        expirations = stock.options
        if not expirations:
            logger.info(f"{ticker}: No hay fechas de vencimiento disponibles para opciones")
            print(f"{ticker}: No hay fechas de vencimiento disponibles para opciones")
            return None

        iv_values = []
        for expiration in expirations:
            expiration_date = datetime.strptime(expiration, '%Y-%m-%d')
            days_to_expiration = (expiration_date - datetime.now()).days
            if days_to_expiration <= 0 or days_to_expiration > max_days:
                logger.debug(f"{ticker}: Expiración {expiration} descartada: {days_to_expiration} días")
                continue

            opt = stock.option_chain(expiration)
            # Considerar puts y calls para obtener una mejor estimación
            for chain in [opt.puts, opt.calls]:
                if chain.empty:
                    logger.debug(f"{ticker}: Cadena de opciones vacía para {expiration}")
                    continue
                # Encontrar la opción ATM (strike más cercano al precio actual)
                chain['strike_diff'] = abs(chain['strike'] - current_price)
                atm_option = chain.loc[chain['strike_diff'].idxmin()]
                iv = atm_option.get('impliedVolatility', 0) * 100
                if iv > 0:
                    iv_values.append(iv)
                else:
                    logger.debug(f"{ticker}: Volatilidad implícita no válida para {expiration}: {iv}%")

        if not iv_values:
            logger.info(f"{ticker}: No se encontraron opciones válidas para calcular IV")
            print(f"{ticker}: No se encontraron opciones válidas para calcular IV")
            return None
        implied_volatility = np.mean(iv_values)
        logger.info(f"{ticker}: Volatilidad implícita promedio: {implied_volatility:.2f}%")
        print(f"{ticker}: Volatilidad implícita promedio: {implied_volatility:.2f}%")

        # Calcular volatilidad histórica (Hist Vol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=hist_vol_period + 1)
        hist_data = stock.history(start=start_date, end=end_date)
        num_days = len(hist_data)
        min_days_required = 10  # Requerimos al menos 10 días para un cálculo significativo

        if num_days < min_days_required:
            logger.info(f"{ticker}: No hay suficientes datos históricos para calcular Hist Vol (se encontraron {num_days} días, se requieren al menos {min_days_required})")
            print(f"{ticker}: No hay suficientes datos históricos para calcular Hist Vol (se encontraron {num_days} días, se requieren al menos {min_days_required})")
            return None

        # Si hay menos días de los solicitados, usar los días disponibles
        if num_days < hist_vol_period:
            logger.info(f"{ticker}: Datos históricos insuficientes para {hist_vol_period} días, usando {num_days} días disponibles")
            print(f"{ticker}: Datos históricos insuficientes para {hist_vol_period} días, usando {num_days} días disponibles")

        # Calcular retornos diarios logarítmicos
        hist_data['returns'] = np.log(hist_data['Close'] / hist_data['Close'].shift(1))
        hist_vol = hist_data['returns'].std() * np.sqrt(252) * 100  # Anualizar
        logger.info(f"{ticker}: Volatilidad histórica: {hist_vol:.2f}%")
        print(f"{ticker}: Volatilidad histórica: {hist_vol:.2f}%")

        return {
            "ticker": ticker,
            "implied_volatility": implied_volatility,
            "historical_volatility": hist_vol,
            "volume": volume
        }
    except Exception as e:
        logger.info(f"Error calculando métricas de volatilidad para {ticker}: {e}")
        print(f"Error calculando métricas de volatilidad para {ticker}: {e}")
        return None

def generate_dynamic_tickers(dynamic_source, dynamic_criteria):
    """
    Genera una lista de tickers dinámicamente basada en los criterios especificados.
    """
    try:
        # Obtener la lista de tickers según la fuente
        index = dynamic_source.get("index")
        if index == "nasdaq100":
            tickers = NASDAQ_100_TICKERS  # Usar la lista estática
        else:
            logger.error(f"Fuente dinámica no soportada: {index}")
            print(f"Fuente dinámica no soportada: {index}")
            return []

        logger.info(f"Total de tickers iniciales para {index}: {len(tickers)}")
        print(f"Total de tickers iniciales para {index}: {len(tickers)}")

        # Obtener criterios de filtrado
        top_n = dynamic_criteria.get("top", 15)
        metric = dynamic_criteria.get("metric", "implied_volatility")
        prefer_iv_over_hist_vol = dynamic_criteria.get("prefer_iv_over_hist_vol", True)
        min_iv = dynamic_criteria.get("min_iv", 35.0)
        min_volume = dynamic_criteria.get("min_volume", 1000000)
        hist_vol_period = dynamic_criteria.get("hist_vol_period", 30)

        # Calcular métricas de volatilidad para cada ticker
        volatility_data = []
        discarded_by_iv = 0
        discarded_by_volume = 0
        discarded_by_data = 0

        for ticker in tickers:
            metrics = calculate_volatility_metrics(ticker, max_days=45, hist_vol_period=hist_vol_period)
            if metrics is None:
                discarded_by_data += 1
                continue

            # Aplicar filtros iniciales
            if metrics["implied_volatility"] < min_iv:
                logger.info(f"{ticker}: Descartado por volatilidad implícita baja: {metrics['implied_volatility']:.2f}% < {min_iv}%")
                print(f"{ticker}: Descartado por volatilidad implícita baja: {metrics['implied_volatility']:.2f}% < {min_iv}%")
                discarded_by_iv += 1
                continue
            if metrics["volume"] < min_volume:
                logger.info(f"{ticker}: Descartado por volumen bajo: {metrics['volume']} < {min_volume}")
                print(f"{ticker}: Descartado por volumen bajo: {metrics['volume']} < {min_volume}")
                discarded_by_volume += 1
                continue
            volatility_data.append(metrics)

        # Resumen de descartes
        logger.info(f"Resumen de filtrado: {discarded_by_data} tickers descartados por falta de datos, {discarded_by_iv} por IV baja, {discarded_by_volume} por volumen bajo")
        print(f"Resumen de filtrado: {discarded_by_data} tickers descartados por falta de datos, {discarded_by_iv} por IV baja, {discarded_by_volume} por volumen bajo")

        if not volatility_data:
            logger.warning("No se encontraron tickers que cumplan con los criterios de filtrado")
            print("No se encontraron tickers que cumplan con los criterios de filtrado")
            return []

        # Convertir a DataFrame para facilitar el ordenamiento
        df = pd.DataFrame(volatility_data)
        df['iv_hist_diff'] = df['implied_volatility'] - df['historical_volatility']
        df['iv_hist_diff_abs'] = df['iv_hist_diff'].abs()

        # Seleccionar tickers
        selected_tickers = []
        # Primero, tickers con IV > Hist Vol, ordenados por IV (descendente)
        if prefer_iv_over_hist_vol:
            iv_greater = df[df['iv_hist_diff'] > 0].sort_values(by="implied_volatility", ascending=False)
            selected_tickers.extend(iv_greater['ticker'].head(top_n).tolist())
            logger.info(f"Tickers con IV > Hist Vol: {len(iv_greater)}")
            print(f"Tickers con IV > Hist Vol: {len(iv_greater)}")

        # Si no se alcanzan los top_n tickers, seleccionar los restantes por diferencia absoluta (menor es mejor)
        if len(selected_tickers) < top_n:
            remaining_slots = top_n - len(selected_tickers)
            remaining = df[~df['ticker'].isin(selected_tickers)].sort_values(by="iv_hist_diff_abs", ascending=True)
            selected_tickers.extend(remaining['ticker'].head(remaining_slots).tolist())
            logger.info(f"Tickers adicionales seleccionados por diferencia absoluta: {len(remaining)}")
            print(f"Tickers adicionales seleccionados por diferencia absoluta: {len(remaining)}")

        logger.info(f"Tickers seleccionados para el grupo dinámico: {selected_tickers}")
        print(f"Tickers seleccionados para el grupo dinámico: {selected_tickers}")
        return selected_tickers
    except Exception as e:
        logger.error(f"Error generando tickers dinámicos: {e}")
        print(f"Error generando tickers dinámicos: {e}")
        return []

def get_option_data_yahoo(ticker, group_config):
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
            if days_to_expiration <= 0 or days_to_expiration > group_config["MAX_DIAS_VENCIMIENTO"]:
                logger.debug(f"Expiración {expiration} descartada: {days_to_expiration} días")
                continue

            opt = stock.option_chain(expiration)
            chain = opt.puts
            for _, row in chain.iterrows():
                strike = row['strike']
                bid = row.get('bid', 0)
                if bid < group_config["MIN_BID"]:
                    logger.debug(f"Opción descartada: bid ${bid:.2f} < {group_config['MIN_BID']}")
                    continue

                implied_volatility = row.get('impliedVolatility', 0) * 100
                if implied_volatility < group_config["MIN_VOLATILIDAD_IMPLICITA"]:
                    logger.debug(f"Opción descartada: volatilidad implícita {implied_volatility:.2f}% < {group_config['MIN_VOLATILIDAD_IMPLICITA']}%")
                    continue

                last_price = row.get('lastPrice', 0)
                if last_price <= 0:
                    logger.debug(f"Opción descartada: último precio ${last_price:.2f} <= 0")
                    continue

                volume = row.get('volume', 0) or 0
                if volume < group_config["MIN_VOLUMEN"]:
                    logger.debug(f"Opción descartada: volumen {volume} < {group_config['MIN_VOLUMEN']}")
                    continue

                open_interest = row.get('openInterest', 0) or 0
                if open_interest < group_config["MIN_OPEN_INTEREST"]:
                    logger.debug(f"Opción descartada: interés abierto {open_interest} < {group_config['MIN_OPEN_INTEREST']}")
                    continue

                if group_config["FILTRO_TIPO_OPCION"] == "OTM":
                    if strike >= current_price:
                        logger.debug(f"Opción descartada: put OTM, strike ${strike:.2f} >= precio actual ${current_price:.2f}")
                        continue
                elif group_config["FILTRO_TIPO_OPCION"] == "ITM":
                    if strike < current_price:
                        logger.debug(f"Opción descartada: put ITM, strike ${strike:.2f} < precio actual ${current_price:.2f}")
                        continue

                break_even = strike - last_price
                percent_diff = ((current_price - break_even) / current_price) * 100
                if percent_diff < group_config["MIN_DIFERENCIA_PORCENTUAL"]:
                    logger.debug(f"Opción descartada: diferencia porcentual {percent_diff:.2f}% < {group_config['MIN_DIFERENCIA_PORCENTUAL']}%")
                    continue

                rentabilidad_diaria = (last_price * 100) / current_price
                rentabilidad_anual = rentabilidad_diaria * (365 / days_to_expiration)
                if rentabilidad_anual < group_config["MIN_RENTABILIDAD_ANUAL"]:
                    logger.debug(f"Opción descartada: rentabilidad anualizada {rentabilidad_anual:.2f}% < {group_config['MIN_RENTABILIDAD_ANUAL']}%")
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

def get_option_data_finnhub(ticker, group_config):
    return []

def combine_options_data(yahoo_data, finnhub_data):
    combined = yahoo_data + finnhub_data
    return combined

def analyze_ticker(ticker, group_config):
    logger.info(f"Analizando {ticker}...")
    print(f"\n{'='*50}\nAnalizando ticker: {ticker}\n{'='*50}\n")
    yahoo_data = get_option_data_yahoo(ticker, group_config)
    finnhub_data = get_option_data_finnhub(ticker, group_config)
    logger.info(f"{len(yahoo_data)} opciones de Yahoo para {ticker}")
    logger.info(f"{len(finnhub_data)} opciones de Finnhub para {ticker}")
    logger.info(f"Combinadas {len(yahoo_data + finnhub_data)} opciones para {ticker}")
    print(f"{len(yahoo_data)} opciones de Yahoo para {ticker}")
    print(f"{len(finnhub_data)} opciones de Finnhub para {ticker}")
    print(f"Combinadas {len(yahoo_data + finnhub_data)} opciones para {ticker}")
    return combine_options_data(yahoo_data, finnhub_data)

def send_discord_notification(tickers_identificados, webhook_url, group_config, group_description):
    if not webhook_url or webhook_url == "URL_POR_DEFECTO":
        logger.error(f"Error: Webhook inválido: {webhook_url}")
        print(f"Error: Webhook inválido: {webhook_url}")
        return
    try:
        ticker_list = ", ".join(tickers_identificados) if tickers_identificados else "Ninguno"
        # Encabezado con las reglas de alerta
        header = (
            f"**Análisis de Opciones - {group_description}**\n"
            f"Reglas de Alerta:\n"
            f"- Rentabilidad Anual Mínima: {group_config['ALERTA_RENTABILIDAD_ANUAL']}%\n"
            f"- Volatilidad Implícita Mínima: {group_config['ALERTA_VOLATILIDAD_MINIMA']}%\n"
            f"{'-'*50}\n"
        )
        message = (
            f"{header}"
            f"Se encontraron contratos que cumplen los filtros de alerta para los siguientes tickers: {ticker_list}"
        )
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
    # Determinar si el grupo es dinámico o estático
    if "dynamic_source" in group_config:
        tickers = generate_dynamic_tickers(group_config["dynamic_source"], group_config["dynamic_criteria"])
    else:
        tickers = group_config["tickers"]

    if not tickers:
        logger.error(f"No se encontraron tickers para el grupo {group_type}")
        print(f"No se encontraron tickers para el grupo {group_type}")
        return

    description = group_config["description"]
    webhook_url = group_config["webhook"]
    config = group_config["config"]
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
            options = analyze_ticker(ticker, config)
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
            filtered_contracts = df_ticker.head(config["TOP_CONTRATOS"])
            filtered_contracts_by_ticker[ticker] = filtered_contracts

            # Filtrar por reglas de alerta (solo para notificación a Discord)
            best_contracts = df_ticker[
                (df_ticker["rentabilidad_anual"] >= config["ALERTA_RENTABILIDAD_ANUAL"]) &
                (df_ticker["implied_volatility"] >= config["ALERTA_VOLATILIDAD_MINIMA"])
            ].head(config["TOP_CONTRATOS"])
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
            ticker_message += f"{len(get_option_data_yahoo(ticker, config))} opciones de Yahoo para {ticker}\n"
            ticker_message += f"{len(get_option_data_finnhub(ticker, config))} opciones de Finnhub para {ticker}\n"
            ticker_message += f"Combinadas {len(options)} opciones para {ticker}\n"
            ticker_message += f"Fuentes: Yahoo Finance\n"
            ticker_message += f"Errores: Ninguno\n"

            print(f"Precio del subyacente ({ticker}): ${current_price:.2f}")
            print(f"Mínimo de las últimas 52 semanas: ${min_52_week:.2f}")
            print(f"Máximo de las últimas 52 semanas: ${max_52_week:.2f}")
            print(f"{len(get_option_data_yahoo(ticker, config))} opciones de Yahoo para {ticker}")
            print(f"{len(get_option_data_finnhub(ticker, config))} opciones de Finnhub para {ticker}")
            print(f"Combinadas {len(options)} opciones para {ticker}")
            print(f"Fuentes: Yahoo Finance")
            print(f"Errores: Ninguno")

            if not filtered_contracts.empty:
                tipo_opcion_texto = "Out of the Money" if config["FILTRO_TIPO_OPCION"] == "OTM" else "In the Money"
                ticker_message += f"\nOpciones PUT {tipo_opcion_texto} con rentabilidad anual > {config['MIN_RENTABILIDAD_ANUAL']}% y diferencia % > {config['MIN_DIFERENCIA_PORCENTUAL']}% (máximo {config['MAX_DIAS_VENCIMIENTO']} días, volumen > {config['MIN_VOLUMEN']}, volatilidad >= {config['MIN_VOLATILIDAD_IMPLICITA']}%, interés abierto > {config['MIN_OPEN_INTEREST']}, bid >= ${config['MIN_BID']}):\n"
                print(f"\nOpciones PUT {tipo_opcion_texto} con rentabilidad anual > {config['MIN_RENTABILIDAD_ANUAL']}% y diferencia % > {config['MIN_DIFERENCIA_PORCENTUAL']}% (máximo {config['MAX_DIAS_VENCIMIENTO']} días, volumen > {config['MIN_VOLUMEN']}, volatilidad >= {config['MIN_VOLATILIDAD_IMPLICITA']}%, interés abierto > {config['MIN_OPEN_INTEREST']}, bid >= ${config['MIN_BID']}):")

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
    if config["FORCE_DISCORD_NOTIFICATION"] or tickers_identificados:
        logger.debug(f"Enviando a {webhook_url} para {description}")
        print(f"Enviando notificación a Discord para {description}")
        send_discord_notification(tickers_identificados, webhook_url, config, description)

if __name__ == "__main__":
    main()
