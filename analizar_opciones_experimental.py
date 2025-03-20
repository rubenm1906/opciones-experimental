import yfinance as yf
from datetime import datetime
import os
from tabulate import tabulate
import pandas as pd
import requests
import time

# === Configuración de Grupos y Tickers (Fácil de Escalar) ===
# Agrega nuevos grupos aquí siguiendo el mismo formato
GROUPS_CONFIG = {
    "magnificas": {
        "tickers": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA"],
        "description": "Las 7 magníficas (tecnología principal)",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_MAGNIFICAS", "https://discord.com/api/webhooks/1351687590536806431/nWxbEuawqZUwsk5nU39Mhoo366_beQqGUTEDpaKdJndnIXzW7r_wvPe8a8nW5PuApQmF")
    },
    "indices": {
        "tickers": ["^GSPC", "^DJI", "^IXIC"],
        "description": "Índices principales (S&P 500, Dow Jones, NASDAQ)",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_INDICES", "https://discord.com/api/webhooks/1351688679353221202/Aoyn8_T6YWl4QYruzauJGoqYKyGek6UVoomUa3APmEXt4RkhX9spXvhAgDSf1Ck00SJA")
    },
    "shortlist": {
        "tickers": os.getenv("SHORTLIST_TICKERS", "EPAM,NFE,GLNG,GLOB").split(","),
        "description": "Lista personalizada de tickers",
        "webhook": os.getenv("DISCORD_WEBHOOK_URL_SHORTLIST", "https://discord.com/api/webhooks/1351688806570655824/hOlRcUJ2UkErdZGfSLBOAq2WekOg4aEtjRZkQHLNvrYdebuytW7cyZPQkGTjVpcG46cI")
    }
    # Para agregar un nuevo grupo, simplemente añade una nueva entrada aquí, por ejemplo:
    # "nuevo_grupo": {
    #     "tickers": ["TICKER1", "TICKER2"],
    #     "description": "Descripción del nuevo grupo",
    #     "webhook": os.getenv("DISCORD_WEBHOOK_URL_NUEVO_GRUPO", "URL_POR_DEFECTO")
    # }
}
print(f"[DEBUG] Grupos configurados: {GROUPS_CONFIG}")

# Configuración por defecto para Discord (usada si no se especifica un webhook para el grupo)
DISCORD_WEBHOOK_URL_DEFAULT = "https://discord.com/api/webhooks/1350463523196768356/ePmWnO2XWnfD582oMAr2WzqSFs7ZxU1ApRYi1bz8PiSbZE5zAcR7ZoOD8SPVofxA9UUW"

# Variable para evitar ejecuciones múltiples en una sola instancia
SCRIPT_EJECUTADO = False
ENVIAR_NOTIFICACION_MANUAL = False

# Configuraciones por defecto (ajustables por grupo)
DEFAULT_CONFIG = {
    "MIN_RENTABILIDAD_ANUAL": 45.0,
    "MAX_DIAS_VENCIMIENTO": 45,
    "MIN_DIFERENCIA_PORCENTUAL": 5.0,
    "MIN_VOLUMEN": 1,
    "MIN_VOLATILIDAD_IMPLICITA": 35.0,
    "MIN_OPEN_INTEREST": 1,
    "FILTRO_TIPO_OPCION": "OTM",
    "TOP_CONTRATOS": 5,
    "ALERTA_RENTABILIDAD_ANUAL": 50.0,
    "ALERTA_VOLATILIDAD_MINIMA": 50.0,
    "MIN_BID": 0.99
}

# Clave API de Finnhub
FINNHUB_API_KEY = "cvbfudhr01qob7udcs1gcvbfudhr01qob7udcs20"

def obtener_configuracion():
    """Obtiene la configuración dinámica basada en el grupo."""
    GROUP_TYPE = os.getenv("GROUP_TYPE", "magnificas").lower()
    print(f"[DEBUG] Grupo seleccionado: {GROUP_TYPE}")

    if GROUP_TYPE not in GROUPS_CONFIG:
        print(f"Grupo no reconocido: {GROUP_TYPE}. Usando 'magnificas' por defecto.")
        GROUP_TYPE = "magnificas"

    group_config = GROUPS_CONFIG[GROUP_TYPE]
    TICKERS = [t.strip() for t in group_config["tickers"] if t.strip()]  # Limpiar y validar tickers
    print(f"[DEBUG] Tickers para {GROUP_TYPE}: {TICKERS}")

    MIN_RENTABILIDAD_ANUAL = float(os.getenv(f"{GROUP_TYPE.upper()}_MIN_RENTABILIDAD_ANUAL", str(DEFAULT_CONFIG["MIN_RENTABILIDAD_ANUAL"])))
    MAX_DIAS_VENCIMIENTO = int(os.getenv(f"{GROUP_TYPE.upper()}_MAX_DIAS_VENCIMIENTO", str(DEFAULT_CONFIG["MAX_DIAS_VENCIMIENTO"])))
    MIN_DIFERENCIA_PORCENTUAL = float(os.getenv(f"{GROUP_TYPE.upper()}_MIN_DIFERENCIA_PORCENTUAL", str(DEFAULT_CONFIG["MIN_DIFERENCIA_PORCENTUAL"])))
    MIN_VOLUMEN = DEFAULT_CONFIG["MIN_VOLUMEN"]
    MIN_VOLATILIDAD_IMPLICITA = float(os.getenv(f"{GROUP_TYPE.upper()}_MIN_VOLATILIDAD_IMPLICITA", str(DEFAULT_CONFIG["MIN_VOLATILIDAD_IMPLICITA"])))
    MIN_OPEN_INTEREST = DEFAULT_CONFIG["MIN_OPEN_INTEREST"]
    FILTRO_TIPO_OPCION = os.getenv(f"{GROUP_TYPE.upper()}_FILTRO_TIPO_OPCION", DEFAULT_CONFIG["FILTRO_TIPO_OPCION"]).upper()
    if FILTRO_TIPO_OPCION not in ["OTM", "ITM", "TODAS"]:
        FILTRO_TIPO_OPCION = DEFAULT_CONFIG["FILTRO_TIPO_OPCION"]
    TOP_CONTRATOS = int(os.getenv(f"{GROUP_TYPE.upper()}_TOP_CONTRATOS", str(DEFAULT_CONFIG["TOP_CONTRATOS"])))
    ALERTA_RENTABILIDAD_ANUAL = DEFAULT_CONFIG["ALERTA_RENTABILIDAD_ANUAL"]
    ALERTA_VOLATILIDAD_MINIMA = DEFAULT_CONFIG["ALERTA_VOLATILIDAD_MINIMA"]
    MIN_BID = float(os.getenv(f"{GROUP_TYPE.upper()}_MIN_BID", str(DEFAULT_CONFIG["MIN_BID"])))

    return (TICKERS, MIN_RENTABILIDAD_ANUAL, MAX_DIAS_VENCIMIENTO, MIN_DIFERENCIA_PORCENTUAL,
            MIN_VOLUMEN, MIN_VOLATILIDAD_IMPLICITA, MIN_OPEN_INTEREST,
            FILTRO_TIPO_OPCION, TOP_CONTRATOS, ALERTA_RENTABILIDAD_ANUAL, ALERTA_VOLATILIDAD_MINIMA,
            MIN_BID, GROUP_TYPE, group_config["description"], group_config["webhook"])

def obtener_datos_subyacente(ticker):
    """Obtiene datos del subyacente."""
    if not ticker:
        raise ValueError("Ticker vacío.")
    stock = yf.Ticker(ticker)
    precio = stock.info.get('regularMarketPrice', None)
    minimo_52 = stock.info.get('fiftyTwoWeekLow', None)
    maximo_52 = stock.info.get('fiftyTwoWeekHigh', None)
    if precio is None or minimo_52 is None or maximo_52 is None:
        raise ValueError(f"Datos no encontrados para {ticker}")
    return stock, precio, minimo_52, maximo_52

def obtener_opciones_yahoo(stock):
    """Obtiene opciones PUT desde Yahoo."""
    try:
        fechas = stock.options
        opciones_put = []
        for fecha in fechas:
            opcion = stock.option_chain(fecha)
            puts = opcion.puts
            for _, put in puts.iterrows():
                opciones_put.append({
                    "strike": float(put["strike"]),
                    "lastPrice": float(put["lastPrice"]),
                    "bid": float(put.get("bid", 0) or 0),
                    "expirationDate": fecha,
                    "volume": put.get("volume", 0) or 0,
                    "impliedVolatility": (put.get("impliedVolatility", 0) or 0) * 100,
                    "openInterest": put.get("openInterest", 0) or 0,
                    "source": "Yahoo Finance"
                })
        print(f"{len(opciones_put)} opciones de Yahoo para {stock.ticker}")
        return opciones_put, "Yahoo Finance", None
    except Exception as e:
        print(f"Error en Yahoo para {stock.ticker}: {e}")
        return [], "Yahoo Finance", str(e)

def obtener_opciones_finnhub(ticker):
    """Obtiene opciones PUT desde Finnhub."""
    url = f"https://finnhub.io/api/v1/stock/option-chain?symbol={ticker}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        opciones_put = []
        for expiration in data.get("data", []):
            fecha = expiration["expirationDate"]
            for option in expiration["options"]["PUT"]:
                opciones_put.append({
                    "strike": float(option["strike"]),
                    "lastPrice": float(option.get("last", 0) or 0),
                    "bid": float(option.get("bid", 0) or 0),
                    "expirationDate": fecha,
                    "volume": option.get("volume", 0) or 0,
                    "impliedVolatility": (option.get("impliedVolatility", 0) or 0) * 100,
                    "openInterest": option.get("openInterest", 0) or 0,
                    "source": "Finnhub"
                })
        print(f"{len(opciones_put)} opciones de Finnhub para {ticker}")
        return opciones_put, "Finnhub", None
    except requests.exceptions.RequestException as e:
        print(f"Error en Finnhub para {ticker}: {e}")
        return [], "Finnhub", str(e)

def combinar_opciones(opciones_yahoo, opciones_finnhub):
    """Combina opciones de ambas fuentes."""
    opciones_dict = {}
    for opcion in opciones_yahoo + opciones_finnhub:
        key = (opcion["strike"], opcion["expirationDate"])
        if key not in opciones_dict:
            opciones_dict[key] = opcion
        else:
            existing = opciones_dict[key]
            for field in ["bid", "lastPrice", "volume", "openInterest", "impliedVolatility"]:
                if pd.isna(existing[field]) or existing[field] == 0:
                    existing[field] = opcion[field]
            existing["source"] = "Yahoo + Finnhub" if existing["source"] != opcion["source"] else existing["source"]
    return list(opciones_dict.values())

def obtener_opciones_put(ticker, stock):
    """Obtiene y combina opciones PUT."""
    opciones_yahoo, source_yahoo, error_yahoo = obtener_opciones_yahoo(stock)
    opciones_finnhub, source_finnhub, error_finnhub = obtener_opciones_finnhub(ticker)
    opciones_combinadas = combinar_opciones(opciones_yahoo, opciones_finnhub)
    print(f"Combinadas {len(opciones_combinadas)} opciones para {ticker}")
    fuentes_texto = " y ".join(filter(None, [source_yahoo if opciones_yahoo else None, source_finnhub if opciones_finnhub else None])) or "Ninguna"
    errores_texto = "; ".join(filter(None, [error_yahoo, error_finnhub])) or "Ninguno"
    return opciones_combinadas, fuentes_texto, errores_texto

def calcular_rentabilidad(precio_put, precio_subyacente, dias_vencimiento):
    """Calcula rentabilidad."""
    rent_diaria = (precio_put * 100) / precio_subyacente
    rent_anual = rent_diaria * (365 / dias_vencimiento)
    return rent_diaria, rent_anual

def calcular_break_even(strike, precio_put):
    """Calcula break-even."""
    return strike - precio_put

def calcular_diferencia_porcentual(precio_subyacente, break_even):
    """Calcula diferencia porcentual."""
    return ((precio_subyacente - break_even) / precio_subyacente) * 100

def enviar_notificacion_discord(tipo_opcion_texto, top_contratos, tickers_identificados, alerta_rentabilidad_anual, alerta_volatilidad_minima, group_type, webhook_url):
    """Envía notificación a Discord con formato mejorado."""
    print(f"[DEBUG] Enviando a {webhook_url} para {group_type}")
    if not webhook_url or not webhook_url.startswith(('http://', 'https://')):
        print(f"Error: Webhook inválido para {group_type}: {webhook_url}")
        return

    ticker_list = ", ".join(tickers_identificados) if tickers_identificados else "Ninguno"
    mensaje = (
        f"**[{group_type.upper()}] Nuevas Oportunidades de Opciones**\n"
        f"**Tipo de Opción:** {tipo_opcion_texto}\n"
        f"**Top Contratos por Ticker:** {top_contratos}\n"
        f"**Tickers Identificados:** {ticker_list}\n"
        f"**Criterios de Alerta:** Rentabilidad Anual ≥ {alerta_rentabilidad_anual}%, Volatilidad Implícita ≥ {alerta_volatilidad_minima}%\n"
        f"**Archivo Adjunto:** Mejores_Contratos.txt (ver detalles abajo)"
    )

    try:
        file_size = os.path.getsize("Mejores_Contratos.txt")
        if file_size > 8 * 1024 * 1024:
            mensaje += f"\n⚠️ **Archivo demasiado grande** ({file_size / (1024 * 1024):.2f} MB). Revisa los artifacts en GitHub Actions."
            payload = {"content": mensaje}
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            print(f"Notificación de error enviada a {webhook_url}")
            return
    except FileNotFoundError:
        mensaje += "\n⚠️ **Archivo no encontrado:** Mejores_Contratos.txt. Revisa los logs para más detalles."
        payload = {"content": mensaje}
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"Notificación de error enviada a {webhook_url}")
        return

    try:
        with open("Mejores_Contratos.txt", "rb") as f:
            files = {"file": ("Mejores_Contratos.txt", f, "text/plain")}
            payload = {"content": mensaje}
            response = requests.post(webhook_url, data=payload, files=files)
            response.raise_for_status()
            print(f"Notificación enviada a {webhook_url}")
    except requests.exceptions.RequestException as e:
        print(f"Error enviando a {webhook_url}: {e}")

def analizar_opciones():
    global SCRIPT_EJECUTADO

    print(f"[DEBUG] Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    if SCRIPT_EJECUTADO:
        print("Ejecución previa detectada. Saliendo.")
        return
    SCRIPT_EJECUTADO = True

    try:
        (TICKERS, MIN_RENTABILIDAD_ANUAL, MAX_DIAS_VENCIMIENTO, MIN_DIFERENCIA_PORCENTUAL,
         MIN_VOLUMEN, MIN_VOLATILIDAD_IMPLICITA, MIN_OPEN_INTEREST,
         FILTRO_TIPO_OPCION, TOP_CONTRATOS, ALERTA_RENTABILIDAD_ANUAL, ALERTA_VOLATILIDAD_MINIMA,
         MIN_BID, GROUP_TYPE, group_description, webhook_url) = obtener_configuracion()
    except Exception as e:
        print(f"Error en configuración: {e}")
        with open("resultados.txt", "w") as f:
            f.write(f"Error: {e}\n")
        return

    es_manual = os.getenv("GITHUB_EVENT_NAME", "schedule") == "workflow_dispatch"
    force_discord = os.getenv("FORCE_DISCORD_NOTIFICATION", "false").lower() == "true"
    print(f"Manual: {es_manual}, Forzar Discord: {force_discord}")

    resumen = (
        f"Resumen - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n"
        f"Grupo: {GROUP_TYPE} ({group_description})\n"
        f"Tickers: {', '.join(TICKERS)}\n"
        f"Filtro: {FILTRO_TIPO_OPCION}\n"
        f"Rent. Mín.: {MIN_RENTABILIDAD_ANUAL}%\n"
        f"Días Máx.: {MAX_DIAS_VENCIMIENTO}\n"
        f"Dif. Mín.: {MIN_DIFERENCIA_PORCENTUAL}%\n"
        f"Vol. Mín.: {MIN_VOLUMEN}\n"
        f"Vol. Impl. Mín.: {MIN_VOLATILIDAD_IMPLICITA}%\n"
        f"Interés Mín.: {MIN_OPEN_INTEREST}\n"
        f"Bid Mín.: ${MIN_BID}\n{'='*50}\n"
    )

    resultado = resumen
    todas_opciones = []
    todas_df = []

    try:
        print(f"[DEBUG] Analizando {len(TICKERS)} tickers")
        for ticker in TICKERS:
            resultado += f"\n{'='*50}\n{ticker} ({GROUP_TYPE})\n{'='*50}\n"
            print(f"\n{'='*50}\n{ticker} ({GROUP_TYPE})\n{'='*50}\n")

            try:
                stock, precio, min_52, max_52 = obtener_datos_subyacente(ticker)
                resultado += f"Precio: ${precio:.2f}\nMin 52s: ${min_52:.2f}\nMax 52s: ${max_52:.2f}\n"
                print(f"Precio: ${precio:.2f}\nMin 52s: ${min_52:.2f}\nMax 52s: ${max_52:.2f}")

                opciones, fuentes, errores = obtener_opciones_put(ticker, stock)
                resultado += f"Fuentes: {fuentes}\nErrores: {errores}\n"
                print(f"Fuentes: {fuentes}\nErrores: {errores}")

                opciones_filtradas = []
                for contrato in opciones:
                    strike = float(contrato["strike"])
                    precio_put = float(contrato["lastPrice"])
                    vencimiento = contrato["expirationDate"]
                    dias = (datetime.strptime(vencimiento, "%Y-%m-%d") - datetime.now()).days
                    volumen = contrato["volume"]
                    vol_impl = contrato["impliedVolatility"]
                    open_int = contrato["openInterest"]
                    bid = contrato["bid"]

                    if FILTRO_TIPO_OPCION == "OTM" and strike >= precio:
                        continue
                    elif FILTRO_TIPO_OPCION == "ITM" and strike < precio:
                        continue

                    if dias <= 0 or dias > MAX_DIAS_VENCIMIENTO:
                        continue
                    if volumen < MIN_VOLUMEN:
                        continue
                    if vol_impl < MIN_VOLATILIDAD_IMPLICITA:
                        continue
                    if open_int < MIN_OPEN_INTEREST:
                        continue
                    if bid < MIN_BID:
                        continue

                    rent_diaria, rent_anual = calcular_rentabilidad(precio_put, precio, dias)
                    break_even = calcular_break_even(strike, precio_put)
                    dif_porcentual = calcular_diferencia_porcentual(precio, break_even)

                    if rent_anual >= MIN_RENTABILIDAD_ANUAL and dif_porcentual >= MIN_DIFERENCIA_PORCENTUAL:
                        opcion = {
                            "ticker": ticker, "strike": strike, "lastPrice": precio_put, "bid": bid,
                            "vencimiento": vencimiento, "dias_vencimiento": dias, "rentabilidad_diaria": rent_diaria,
                            "rentabilidad_anual": rent_anual, "break_even": break_even,
                            "diferencia_porcentual": dif_porcentual, "volatilidad_implícita": vol_impl,
                            "volumen": volumen, "open_interest": open_int, "source": contrato["source"]
                        }
                        opciones_filtradas.append(opcion)
                        todas_opciones.append(opcion)

                if opciones_filtradas:
                    tipo_opcion = "Out of the Money" if FILTRO_TIPO_OPCION == "OTM" else "In the Money" if FILTRO_TIPO_OPCION == "ITM" else "Todas"
                    resultado += f"\nOpciones {tipo_opcion} (Rent. > {MIN_RENTABILIDAD_ANUAL}%, Dif. > {MIN_DIFERENCIA_PORCENTUAL}%):\n"
                    tabla = tabulate([[f"${o['strike']:.2f}", f"${o['lastPrice']:.2f}", f"${o['bid']:.2f}",
                                     o['vencimiento'], o['dias_vencimiento'], f"{o['rentabilidad_diaria']:.2f}%",
                                     f"{o['rentabilidad_anual']:.2f}%", f"${o['break_even']:.2f}",
                                     f"{o['diferencia_porcentual']:.2f}%", f"{o['volatilidad_implícita']:.2f}%",
                                     o['volumen'], o['open_interest'], o['source']] for o in opciones_filtradas],
                                    headers=["Strike", "Last", "Bid", "Venc.", "Días", "Rent. Diaria",
                                             "Rent. Anual", "Break-even", "Dif. %", "Vol. Impl.",
                                             "Volumen", "Interés", "Fuente"], tablefmt="grid")
                    resultado += f"\n{tabla}\n"
                    for opcion in opciones_filtradas:
                        if opcion['rentabilidad_anual'] >= ALERTA_RENTABILIDAD_ANUAL and opcion['volatilidad_implícita'] >= ALERTA_VOLATILIDAD_MINIMA:
                            resultado += f"¡Oportunidad! {ticker}: Rent. {opcion['rentabilidad_anual']:.2f}%, Vol. {opcion['volatilidad_implícita']:.2f}%\n"
                else:
                    resultado += "\nSin resultados.\n"

            except Exception as e:
                resultado += f"Error en {ticker}: {e}\n"
                print(f"Error en {ticker}: {e}")
                continue

        with open("resultados.txt", "w") as f:
            f.write(resultado)
        print("Resultados guardados.")

        headers = ["Ticker", "Strike", "Last", "Bid", "Venc.", "Días", "Rent. Diaria",
                   "Rent. Anual", "Break-even", "Dif. %", "Vol. Impl.", "Volumen",
                   "Interés", "Fuente"]
        if todas_opciones:
            df_todas = pd.DataFrame([[o["ticker"]] + [f"${o[k]:.2f}" if k in ["strike", "lastPrice", "bid", "break_even"] else f"{o[k]:.2f}%" if k in ["rentabilidad_diaria", "rentabilidad_anual", "diferencia_porcentual", "volatilidad_implícita"] else o[k]
                                                    for k in ["strike", "lastPrice", "bid", "vencimiento", "dias_vencimiento",
                                                              "rentabilidad_diaria", "rentabilidad_anual", "break_even",
                                                              "diferencia_porcentual", "volatilidad_implícita", "volumen",
                                                              "open_interest", "source"]]
                                    for o in todas_opciones], columns=headers)
            df_todas.to_csv("todas_las_opciones.csv", index=False)
        else:
            pd.DataFrame(columns=headers).to_csv("todas_las_opciones.csv", index=False)

        mejores_contratos = []
        for ticker in set(o["ticker"] for o in todas_opciones):
            opciones_ticker = [o for o in todas_opciones if o["ticker"] == ticker]
            if opciones_ticker:
                mejores = sorted(opciones_ticker, key=lambda x: (-x["rentabilidad_anual"], x["dias_vencimiento"], -x["diferencia_porcentual"]))[:TOP_CONTRATOS]
                mejores_contratos.extend(mejores)

        if mejores_contratos:
            tickers_identificados = sorted(set(o["ticker"] for o in mejores_contratos))
            contenido = f"Mejores Contratos ({GROUP_TYPE}):\n{'='*50}\n"
            contratos_por_ticker = {}
            for opcion in mejores_contratos:
                ticker = opcion['ticker']
                if ticker not in contratos_por_ticker:
                    contratos_por_ticker[ticker] = []
                contratos_por_ticker[ticker].append(opcion)

            for ticker in sorted(tickers_identificados):
                contratos = contratos_por_ticker[ticker]
                contenido += f"\nTicker: {ticker}\n{'-'*30}\n"
                for i, opcion in enumerate(contratos, 1):
                    contenido += f"Contrato {i}:\n"
                    contenido += f"  Ticker: {opcion['ticker']}\n"
                    contenido += f"  Strike: ${opcion['strike']:.2f}\n"
                    contenido += f"  Last Closed: ${opcion['lastPrice']:.2f}\n"
                    contenido += f"  Bid: ${opcion['bid']:.2f}\n"
                    contenido += f"  Vencimiento: {opcion['vencimiento']}\n"
                    contenido += f"  Días Venc.: {opcion['dias_vencimiento']}\n"
                    contenido += f"  Rent. Diaria: {opcion['rentabilidad_diaria']:.2f}%\n"
                    contenido += f"  Rent. Anual: {opcion['rentabilidad_anual']:.2f}%\n"
                    contenido += f"  Break-even: ${opcion['break_even']:.2f}\n"
                    contenido += f"  Dif. % (Suby.-Break.): {opcion['diferencia_porcentual']:.2f}%\n"
                    contenido += f"  Volatilidad Implícita: {opcion['volatilidad_implícita']:.2f}%\n"
                    contenido += f"  Volumen: {opcion['volumen']}\n"
                    contenido += f"  Interés Abierto: {opcion['open_interest']}\n"
                    contenido += f"  Fuente: {opcion['source']}\n"
                    contenido += "\n"

            with open("Mejores_Contratos.txt", "w") as f:
                f.write(contenido)
            df_mejores = pd.DataFrame([[o["ticker"]] + [f"${o[k]:.2f}" if k in ["strike", "lastPrice", "bid", "break_even"] else f"{o[k]:.2f}%" if k in ["rentabilidad_diaria", "rentabilidad_anual", "diferencia_porcentual", "volatilidad_implícita"] else o[k]
                                                       for k in ["strike", "lastPrice", "bid", "vencimiento", "dias_vencimiento",
                                                                 "rentabilidad_diaria", "rentabilidad_anual", "break_even",
                                                                 "diferencia_porcentual", "volatilidad_implícita", "volumen",
                                                                 "open_interest", "source"]] for o in mejores_contratos],
                                     columns=headers)
            df_mejores.to_csv("mejores_contratos.csv", index=False)
            if not es_manual or force_discord or ENVIAR_NOTIFICACION_MANUAL:
                tipo_opcion = "Out of the Money" if FILTRO_TIPO_OPCION == "OTM" else "In the Money" if FILTRO_TIPO_OPCION == "ITM" else "Todas"
                enviar_notificacion_discord(tipo_opcion, TOP_CONTRATOS, tickers_identificados,
                                          ALERTA_RENTABILIDAD_ANUAL, ALERTA_VOLATILIDAD_MINIMA, GROUP_TYPE, webhook_url)
        else:
            pd.DataFrame(columns=headers).to_csv("mejores_contratos.csv", index=False)

    except Exception as e:
        print(f"Error general: {e}")
        resultado += f"Error: {e}\n"
        with open("resultados.txt", "w") as f:
            f.write(resultado)
        pd.DataFrame(columns=headers).to_csv("todas_las_opciones.csv", index=False)
        pd.DataFrame(columns=headers).to_csv("mejores_contratos.csv", index=False)

if __name__ == "__main__":
    analizar_opciones()
