"""
Scraper de resultados de loterías dominicanas — premios.do  (v2, corregido)
=============================================================================
CAMBIO IMPORTANTE respecto a la v1: la primera versión buscaba cualquier
patrón "número · número · número" cerca de una fecha, y eso hacía que
agarrara por error el texto de premios que aparece en TODAS las páginas
("Primer premio: RD$60... Segundo premio: RD$8... Tercer premio: RD$4...").
Por eso todas las loterías salían con números parecidos/repetidos.

La corrección: los números reales del sorteo aparecen siempre pegados a
la HORA exacta del sorteo, con este formato específico:

    12:00PM · 13 · 52 · 72

Ese patrón (hora + tres números separados por "·") es mucho más específico
y no se confunde con el texto de premios. Además, se descarta cualquier
coincidencia que tenga la palabra "RD$" a menos de 60 caracteres de
distancia, como filtro extra de seguridad.

Formato de salida (resultados.json):
{
  "actualizado": "2026-08-12T20:05:00+00:00",
  "loterias": {
    "la_primera_noche": {"fecha": "2026-08-12", "numeros": [43, 86, 57]},
    ...
  },
  "errores": []
}

NOTA: este scraper se escribió sin poder probarlo en vivo contra internet
real (el entorno donde se generó no tiene acceso a la red). Está basado en
fragmentos reales de esas páginas que sí pude ver mediante búsqueda. Si al
correrlo en GitHub Actions algo sigue fallando o saliendo raro, pégame el
resultados.json o el log de error y lo ajusto de nuevo.
"""

import json
import re
import sys
from datetime import datetime, timezone

import requests

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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Patrón específico: hora (12:00PM, 7:00 PM, etc.) seguida de 3 números separados por "·"
PATRON_RESULTADO = re.compile(
    r"(\d{1,2}:\d{2}\s*[APap][Mm])\s*[·•]\s*(\d{1,3})\s*[·•]\s*(\d{1,3})\s*[·•]\s*(\d{1,3})"
)

PATRON_FECHA = re.compile(
    r"(\d{1,2})\s+de\s+(" + "|".join(MESES.keys()) + r")\s+de\s+(\d{4})",
    re.IGNORECASE,
)


def limpiar_html(html):
    texto = re.sub(r"<[^>]+>", " ", html)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def extraer_resultado(texto):
    """
    Recorre TODAS las coincidencias del patrón hora+números, descarta las
    que tengan 'RD$' cerca (texto de premios), y se queda con la primera
    coincidencia válida (la más reciente, porque la página lista de más
    nuevo a más viejo). Busca también la fecha más cercana ANTES de esa
    coincidencia.
    """
    for match in PATRON_RESULTADO.finditer(texto):
        inicio, fin = match.span()
        contexto = texto[max(0, inicio - 60): fin + 10]
        if "RD$" in contexto or "RD $" in contexto:
            continue  # es texto de premios, no un resultado real; seguimos buscando

        numeros = [int(match.group(i)) for i in (2, 3, 4)]
        numeros = [100 if n == 0 else n for n in numeros]

        # Buscar la fecha más cercana que aparezca ANTES de este resultado
        texto_antes = texto[:inicio]
        fecha_match = None
        for fm in PATRON_FECHA.finditer(texto_antes):
            fecha_match = fm  # nos quedamos con la última (la más cercana al resultado)
        if fecha_match:
            dia, mes_txt, anio = fecha_match.groups()
            mes = MESES[mes_txt.lower()]
            fecha_iso = f"{int(anio):04d}-{mes:02d}-{int(dia):02d}"
        else:
            fecha_iso = None

        return fecha_iso, numeros

    return None, None


def obtener_resultado(nombre, url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    texto = limpiar_html(resp.text)

    fecha, numeros = extraer_resultado(texto)
    if not numeros:
        raise ValueError(
            f"No se encontró un patrón válido de 'hora · num · num · num' "
            f"(sin 'RD$' cerca) para '{nombre}' en {url}"
        )
    if not fecha:
        fecha = "desconocida"

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
        except Exception as exc:  # noqa: BLE001
            mensaje = f"{nombre}: {exc}"
            resultado["errores"].append(mensaje)
            print(f"FALLO  {mensaje}", file=sys.stderr)

    with open("resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado resultados.json con {len(resultado['loterias'])} loterías "
          f"y {len(resultado['errores'])} errores.")

    if not resultado["loterias"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
