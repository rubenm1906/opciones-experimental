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
        print(f"Res
