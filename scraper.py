"""
Scraper de resultados de lotería dominicana - loteriasdominicanas.us
========================================================================
Version 2: usa loteriasdominicanas.us en vez de rdparty.com porque esta
fuente sí trae los resultados del DIA ACTUAL en texto plano (sin
JavaScript), con fecha y etiqueta "Actualizado" cuando el sorteo ya salio.

Cómo funciona:
- Entra a la página principal de loteriasdominicanas.us
- Busca cada bloque de resultado (nombre del juego + fecha + numeros)
- Guarda todo en resultados.json, con fecha de cada sorteo

Requisitos (instalar una sola vez):
    pip install requests beautifulsoup4

Uso:
    python scraper.py
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os

URL_PRINCIPAL = "https://www.loteriasdominicanas.us/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

SALIDA_JSON = os.path.join(os.path.dirname(__file__), "resultados.json")


def extraer_resultados():
    """
    Descarga la página principal y extrae todos los bloques de resultados.
    Cada bloque tiene: nombre del sorteo, fecha, numeros ganadores, y si
    dice "Actualizado" (significa que es el resultado mas reciente de hoy).

    Devuelve un diccionario:
    {
        "Gana Mas": {"fecha": "11 Agosto 2026", "numeros": ["88","28","03"], "actualizado": True},
        "Quiniela Nacional": {"fecha": "10 Agosto 2026", "numeros": ["07","76","66"], "actualizado": False},
        ...
    }
    """
    try:
        resp = requests.get(URL_PRINCIPAL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] No se pudo descargar la pagina: {e}")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    resultados = {}

    # Cada sorteo esta dentro de un enlace <a> que apunta a su pagina
    # individual, y cerca de el estan la fecha y los numeros.
    # Buscamos todos los enlaces que parecen ser de un sorteo especifico
    # (contienen texto y estan seguidos de una lista de numeros).
    enlaces = soup.find_all("a", href=True)

    for enlace in enlaces:
        nombre = enlace.get_text(strip=True)
        href = enlace["href"]

        # Filtramos solo enlaces que parecen ser de sorteos
        # (tienen texto y no son enlaces de menu/footer)
        if not nombre or len(nombre) < 3:
            continue
        if any(skip in href.lower() for skip in
               ["contacto", "nosotros", "terminos", "javascript"]):
            continue

        # Buscamos el contenedor padre que agrupa nombre + fecha + numeros
        contenedor = enlace.find_parent()
        if not contenedor:
            continue

        texto_completo = contenedor.get_text(" ", strip=True)

        # Buscar fecha en formato "11 Agosto 2026"
        match_fecha = re.search(
            r"(\d{1,2}\s+(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|"
            r"Agosto|Septiembre|Octubre|Noviembre|Diciembre)\s+\d{4})",
            texto_completo
        )
        if not match_fecha:
            continue
        fecha = match_fecha.group(1)

        # Buscar numeros de 2 digitos despues de la fecha
        texto_despues_fecha = texto_completo[match_fecha.end():]
        numeros = re.findall(r"\b(\d{2})\b", texto_despues_fecha)
        numeros = numeros[:6]  # maximo 6 numeros (para loto 5, etc.)

        if not numeros:
            continue

        actualizado = "actualizado" in texto_completo.lower()

        # Evitar duplicados: si ya existe, solo sobreescribir si es mas
        # completo (tiene mas numeros) o si dice actualizado
        if nombre not in resultados or actualizado:
            resultados[nombre] = {
                "fecha": fecha,
                "numeros": numeros,
                "actualizado": actualizado,
            }

    return resultados


def main():
    print("=" * 60)
    print("Scraper de Loterias Dominicanas - loteriasdominicanas.us")
    print(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    resultados = extraer_resultados()

    if not resultados:
        print("\n[AVISO] No se encontraron resultados. Revisar la pagina "
              "manualmente, puede que haya cambiado su diseno.")
    else:
        print(f"\nSe encontraron {len(resultados)} sorteos:\n")
        for nombre, datos in resultados.items():
            marca = " (HOY)" if datos["actualizado"] else ""
            print(f"  {nombre}{marca}: {datos['fecha']} -> {datos['numeros']}")

    salida = {
        "ultima_actualizacion": datetime.now().isoformat(),
        "fuente": URL_PRINCIPAL,
        "loterias": resultados,
    }

    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Listo. Resultados guardados en: {SALIDA_JSON}")
    print("=" * 60)


if __name__ == "__main__":
    main()
