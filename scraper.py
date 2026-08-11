"""
Scraper de resultados de lotería dominicana - rdparty.com
============================================================
Lee automáticamente los resultados más recientes de varias loterías
dominicanas y los guarda en un archivo JSON (resultados.json).

Cómo funciona:
- Cada lotería tiene su propia página en rdparty.com
- El script entra a cada página, busca la tabla de "Últimos resultados"
  y extrae fecha + números ganadores
- Todo se guarda en resultados.json, organizado por lotería

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

# ---------------------------------------------------------------------
# CONFIGURACIÓN: mapea el nombre de tu lotería -> URL de rdparty.com
# Agrega o quita líneas aquí según lo que necesites.
# ---------------------------------------------------------------------
LOTERIAS = {
    "Quiniela Real":        "https://rdparty.com/quiniela-real/",
    "Quiniela Leidsa":      "https://rdparty.com/quiniela-leidsa/",
    "Loto Pool Leidsa":     "https://rdparty.com/loto-pool-leidsa/",
    "Pega 3 Mas":           "https://rdparty.com/pega-3-mas/",
    "Super Kino TV":        "https://rdparty.com/super-kino-tv/",
    "Loto Leidsa":          "https://rdparty.com/loto-leidsa/",
    "Super Pale":           "https://rdparty.com/super-pale/",
    "Gana Mas":             "https://rdparty.com/gana-mas/",
    "Quiniela Nacional":    "https://rdparty.com/quiniela-loteria-nacional/",
    "Juega Mas Pega Mas":   "https://rdparty.com/juega-mas-pega-mas/",
    "Quiniela Loteka":      "https://rdparty.com/quiniela-loteka/",
    "Mega Chances":         "https://rdparty.com/mega-chances/",
    "MegaLotto":            "https://rdparty.com/megalotto/",
    "La Primera":           "https://rdparty.com/resultados-la-primera/",
    "La Suerte":            "https://rdparty.com/resultados-la-suerte/",
    "LoteDom":              "https://rdparty.com/resultados-lotedom/",
}

HEADERS = {
    # Simula un navegador normal para evitar bloqueos básicos
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

SALIDA_JSON = os.path.join(os.path.dirname(__file__), "resultados.json")


def extraer_resultados(nombre, url):
    """
    Descarga la página de una lotería y extrae la tabla
    'Últimos resultados de X'. Devuelve una lista de dicts:
    [{"fecha": "19 de julio 2026", "numeros": ["35", "48", "12"]}, ...]
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] No se pudo descargar {nombre}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    resultados = []

    # Buscamos la primera tabla de la página (ahí suele estar el historial)
    tabla = soup.find("table")
    if not tabla:
        print(f"  [AVISO] No se encontró tabla de resultados para {nombre}")
        return []

    filas = tabla.find_all("tr")
    for fila in filas:
        celdas = [c.get_text(strip=True) for c in fila.find_all(["td", "th"])]
        if len(celdas) < 2:
            continue
        fecha, numeros_texto = celdas[0], celdas[1]

        # Saltar la fila de encabezado ("Fecha", "Números ganadores")
        if fecha.lower() in ("fecha", "") or not re.search(r"\d", fecha):
            continue

        # Los números vienen separados por comas, ej: "35, 48, 12"
        numeros = [n.strip() for n in numeros_texto.split(",") if n.strip()]
        if numeros:
            resultados.append({"fecha": fecha, "numeros": numeros})

    return resultados


def main():
    print("=" * 60)
    print("Scraper de Loterías Dominicanas - rdparty.com")
    print(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    data_final = {}

    for nombre, url in LOTERIAS.items():
        print(f"\n-> Consultando {nombre}...")
        resultados = extraer_resultados(nombre, url)
        if resultados:
            print(f"   OK: {len(resultados)} sorteos encontrados. "
                  f"Último: {resultados[0]['fecha']} -> {resultados[0]['numeros']}")
        else:
            print(f"   Sin resultados (revisar manualmente esta lotería)")
        data_final[nombre] = resultados

    # Guardamos todo en JSON con fecha de última actualización
    salida = {
        "ultima_actualizacion": datetime.now().isoformat(),
        "loterias": data_final,
    }

    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Listo. Resultados guardados en: {SALIDA_JSON}")
    print("=" * 60)


if __name__ == "__main__":
    main()
