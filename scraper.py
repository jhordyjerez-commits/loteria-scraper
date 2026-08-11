"""
Scraper de resultados de loterías dominicanas — premios.do  (v3, con Playwright)
=================================================================================
POR QUÉ CAMBIÓ: las versiones anteriores usaban `requests`, que solo descarga
el HTML que manda el servidor SIN ejecutar JavaScript. Las páginas de
premios.do cargan los números ganadores con JavaScript después de la carga
inicial, así que `requests` nunca llegaba a verlos (por eso todo fallaba con
"no se encontró un patrón válido").

La solución: usar Playwright, que abre un navegador real (Chromium) sin
interfaz gráfica, espera a que la página termine de cargar su JavaScript,
y AHÍ SÍ lee el texto ya completo.

Formato de salida (resultados.json) — igual que antes:
{
  "actualizado": "2026-08-12T20:05:00+00:00",
  "loterias": {
    "la_primera_noche": {"fecha": "2026-08-12", "numeros": [43, 86, 57]},
    ...
  },
  "errores": []
}

IMPORTANTE: este cambio requiere instalar el navegador de Playwright en el
GitHub Action (ver instrucciones que te doy aparte para el archivo .yml).
Sin ese paso, este script fallará con un error de "navegador no encontrado".
"""

import json
import re
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

FUENTES = {
    "la_primera_noche": "https://premios.do/resultados-la-primera-noche-hoy",
    "loteka":            "https://premios.do/resultados-loteka-hoy",
    "lotedom":            "https://premios.do/resultados-lotedom-hoy",
    "la_primera_12pm":    "https://premios.do/resultados-la-primera-hoy",
    "anguila_12pm":       "https://premios.do/resultados-anguilla-12pm-hoy",
    "gana_mas":           "https://premios.do/resultados-gana-mas-hoy",
    "leidsa":             "https://premios.do/resultados-leidsa-hoy",
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Hora (12:00PM, 7:00 PM, etc.) seguida de 3 números separados por "·"
PATRON_RESULTADO = re.compile(
    r"(\d{1,2}:\d{2}\s*[APap][Mm])\s*[·•]\s*(\d{1,3})\s*[·•]\s*(\d{1,3})\s*[·•]\s*(\d{1,3})"
)
PATRON_FECHA = re.compile(
    r"(\d{1,2})\s+de\s+(" + "|".join(MESES.keys()) + r")\s+de\s+(\d{4})",
    re.IGNORECASE,
)


def extraer_resultado(texto):
    for match in PATRON_RESULTADO.finditer(texto):
        numeros = [int(match.group(i)) for i in (2, 3, 4)]
        if any(n > 99 for n in numeros):
            continue
        numeros = [100 if n == 0 else n for n in numeros]

        texto_antes = texto[:match.start()]
        fecha_match = None
        for fm in PATRON_FECHA.finditer(texto_antes):
            fecha_match = fm
        if fecha_match:
            dia, mes_txt, anio = fecha_match.groups()
            fecha_iso = f"{int(anio):04d}-{MESES[mes_txt.lower()]:02d}-{int(dia):02d}"
        else:
            fecha_iso = None

        return fecha_iso, numeros

    return None, None


def obtener_resultado(page, nombre, url):
    page.goto(url, wait_until="networkidle", timeout=30000)
    # Esperamos un poco extra por si el JS tarda en pintar los números
    page.wait_for_timeout(2000)
    texto = page.inner_text("body")

    fecha, numeros = extraer_resultado(texto)
    if not numeros:
        raise ValueError(
            f"No se encontró un patrón válido de 'hora · num · num · num' "
            f"para '{nombre}' en {url} (aunque ya se esperó a que cargara el JS)"
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

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for nombre, url in FUENTES.items():
            try:
                resultado["loterias"][nombre] = obtener_resultado(page, nombre, url)
                print(f"OK  {nombre}: {resultado['loterias'][nombre]}")
            except Exception as exc:  # noqa: BLE001
                mensaje = f"{nombre}: {exc}"
                resultado["errores"].append(mensaje)
                print(f"FALLO  {mensaje}", file=sys.stderr)

        browser.close()

    with open("resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado resultados.json con {len(resultado['loterias'])} loterías "
          f"y {len(resultado['errores'])} errores.")

    if not resultado["loterias"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
