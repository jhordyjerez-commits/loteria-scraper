"""
Scraper de resultados de loterías dominicanas — premios.do
============================================================
Busca los resultados más recientes de cada lotería y los guarda en
resultados.json con esta forma:

{
  "actualizado": "2026-08-12T20:05:00",
  "loterias": {
    "la_primera_noche": {"fecha": "2026-08-12", "numeros": [43, 86, 57]},
    "loteka":            {"fecha": "2026-08-12", "numeros": [23, 76, 44]},
    "lotedom":            {"fecha": "2026-08-12", "numeros": [71, 35, 33]},
    "la_primera_12pm":    {"fecha": "2026-08-12", "numeros": [65, 66, 42]},
    "anguila_12pm":       {"fecha": "2026-08-12", "numeros": [75, 98, 4]},
    "gana_mas":           {"fecha": "2026-08-12", "numeros": [85, 47, 97]},
    "leidsa":             {"fecha": "2026-08-12", "numeros": [43, 35, 12]}
  },
  "errores": []   <- si alguna lotería falla, aparece aquí en vez de romper todo
}

NOTA IMPORTANTE: este scraper se escribió sin poder probarlo en vivo (el entorno
donde se generó no tiene acceso a internet). La primera corrida real en GitHub
Actions es la prueba real. Si algo falla, revisa el log de la Action: cada
lotería que falle queda registrada en "errores" con el motivo, y las demás
loterías se guardan igual (un fallo no tumba todo el proceso).
"""

import json
import re
import sys
from datetime import datetime, timezone

import requests

# Cada lotería con su URL en premios.do y una llave interna para el JSON
FUENTES = {
    "la_primera_noche": "https://premios.do/resultados-la-primera-noche-hoy",
    "loteka":            "https://premios.do/resultados-loteka-hoy",
    "lotedom":            "https://premios.do/resultados-lotedom-hoy",
    "la_primera_12pm":    "https://premios.do/resultados-la-primera-hoy",
    "anguila_12pm":       "https://premios.do/resultados-anguilla-12pm-hoy",
    "gana_mas":           "https://premios.do/resultados-gana-mas-hoy",
    "leidsa":             "https://premios.do/resultados-leidsa-hoy",
}

HEADERS = {
    # Algunos sitios bloquean peticiones sin un User-Agent que parezca un navegador real
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Meses en español, para reconocer fechas tipo "12 de agosto de 2026"
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def extraer_fecha_y_numeros(texto_pagina):
    """
    Busca en el texto de la página el patrón:
        <día de la semana> <día> de <mes> de <año> ... NN · NN · NN
    y devuelve (fecha_iso, [n1, n2, n3]) del resultado MÁS RECIENTE que
    encuentre (asumiendo que la página lista del más nuevo al más viejo).

    Si no encuentra nada, devuelve (None, None).
    """
    patron_fecha = re.compile(
        r"(\d{1,2})\s+de\s+(" + "|".join(MESES.keys()) + r")\s+de\s+(\d{4})",
        re.IGNORECASE,
    )
    patron_numeros = re.compile(r"(\d{1,3})\s*[·\-\|]\s*(\d{1,3})\s*[·\-\|]\s*(\d{1,3})")

    fecha_match = patron_fecha.search(texto_pagina)
    if not fecha_match:
        return None, None

    dia, mes_txt, anio = fecha_match.groups()
    mes = MESES[mes_txt.lower()]
    fecha_iso = f"{int(anio):04d}-{mes:02d}-{int(dia):02d}"

    # Buscamos los números de lotería que aparezcan DESPUÉS de la fecha encontrada
    resto = texto_pagina[fecha_match.end():]
    numeros_match = patron_numeros.search(resto)
    if not numeros_match:
        # A veces los números aparecen ANTES de la fecha en el layout; probamos también ahí
        numeros_match = patron_numeros.search(texto_pagina[: fecha_match.start()])
        if not numeros_match:
            return fecha_iso, None

    numeros = [int(x) for x in numeros_match.groups()]
    # Normalizar "00" -> 100, como usa la app (1-100 en vez de 0-99)
    numeros = [100 if n == 0 else n for n in numeros]
    return fecha_iso, numeros


def obtener_resultado(nombre, url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    texto = resp.text
    # Quitamos etiquetas HTML de forma simple para dejar solo texto visible
    texto_limpio = re.sub(r"<[^>]+>", " ", texto)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio)

    fecha, numeros = extraer_fecha_y_numeros(texto_limpio)
    if not fecha or not numeros:
        raise ValueError(f"No se pudo extraer fecha/números para '{nombre}' desde {url}")

    return {"fecha": fecha, "numeros": numeros}


def main():
    resultado = {
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "loterias": {},
        "errores": [],
    }

    for nombre, url in FUENTES.items():
        try:
            resultado["loterias"][nombre] = obtener_resultado(nombre, url)
            print(f"OK  {nombre}: {resultado['loterias'][nombre]}")
        except Exception as exc:  # noqa: BLE001 — queremos capturar cualquier fallo y seguir
            mensaje = f"{nombre}: {exc}"
            resultado["errores"].append(mensaje)
            print(f"FALLO  {mensaje}", file=sys.stderr)

    with open("resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado resultados.json con {len(resultado['loterias'])} loterías "
          f"y {len(resultado['errores'])} errores.")

    # Si TODAS fallaron, marcamos el proceso como fallido para que GitHub Actions lo notifique
    if not resultado["loterias"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
