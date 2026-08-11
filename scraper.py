"""
Scraper de resultados de lotería dominicana - loteriasdominicanas.us
========================================================================
Version 2: usa loteriasdominicanas.us porque trae resultados del DIA
ACTUAL en texto plano (sin JavaScript).
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
    try:
        resp = requests.get(URL_PRINCIPAL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] No se pudo descargar la pagina: {e}")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    resultados = {}

    enlaces = soup.find_all("a", href=True)

    for enlace in enlaces:
        nombre = enlace.get_text(strip=True)
        href = enlace["href"]

        if not nombre or len(nombre) < 3:
            continue
        if any(skip in href.lower() for skip in
               ["contacto", "nosotros", "terminos", "javascript"]):
            continue

        contenedor = enlace.find_parent()
        if not contenedor:
            continue

        texto_completo = contenedor.get_text(" ", strip=True)

        match_fecha = re.search(
            r"(\d{1,2}\s+(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|"
            r"Agosto|Septiembre|Octubre|Noviembre|Diciembre)\s+\d{4})",
            texto_completo
        )
        if not match_fecha:
            continue
        fecha = match_fecha.group(1)

        texto_despues_fecha = texto_completo[match_fecha.end():]
        numeros = re.findall(r"\b(\d{2})\b", texto_despues_fecha)
        numeros = numeros[:6]

        if not numeros:
            continue

        actualizado = "actualizado" in texto_completo.lower()

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
        print("\n[AVISO] No se encontraron resultados.")
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
