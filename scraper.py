"""
Scraper de resultados de loterías dominicanas — premios.do  (v4, patrón corregido)
====================================================================================
QUÉ CAMBIÓ EN ESTA VERSIÓN: el script "detective" mostró que el formato real
de la página NO es "hora · num · num · num" en una sola línea. El formato
real es línea por línea, así:

    Loteka
     Martes 11 de agosto, 2026  7:50PM
    79
    18
    84

Es decir: nombre de la lotería, luego una línea con "DD de mes de AAAA  H:MMPM",
y después cada número ganador en su PROPIA línea, sin ningún símbolo "·" ni
separador. Por eso el patrón anterior nunca encontraba nada.

También se cambió `wait_until="networkidle"` por `"domcontentloaded"` en
la_primera_noche (y en todas), porque esa página nunca queda "en reposo" de
red (scripts de analytics/ads siguen corriendo) y eso causaba el timeout de
30 segundos.

Formato de salida (resultados.json) — igual que antes:
{
  "actualizado": "2026-08-12T20:05:00+00:00",
  "loterias": {
    "la_primera_noche": {"fecha": "2026-08-12", "numeros": [43, 86, 57]},
    ...
  },
  "errores": []
}
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

# Línea con "DD de mes de AAAA   H:MMPM" (la hora puede o no tener espacio
# antes de AM/PM, ej. "7:00PM" o "7:00 PM")
PATRON_FECHA_HORA = re.compile(
    r"(\d{1,2})\s+de\s+(" + "|".join(MESES.keys()) + r")"
    r"(?:\s+de\s+|\s*,\s*)(\d{4})"  # acepta "de 2026" O ", 2026"
    r"\s+\d{1,2}:\d{2}\s*[APap][Mm]",
    re.IGNORECASE,
)

# Una línea que es SOLO un número (el resultado ganador), 1 a 3 dígitos
PATRON_NUMERO_LINEA = re.compile(r"^\d{1,3}$")


def extraer_resultado(texto):
    """
    Busca la primera línea con fecha+hora (la más reciente aparece primero
    en la página) y toma los 3 números que vienen en las líneas siguientes.
    """
    lineas = texto.split("\n")

    for i, linea in enumerate(lineas):
        m = PATRON_FECHA_HORA.search(linea)
        if not m:
            continue

        numeros = []
        j = i + 1
        while j < len(lineas) and len(numeros) < 3:
            candidata = lineas[j].strip()
            if candidata == "":
                j += 1
                continue
            if PATRON_NUMERO_LINEA.match(candidata):
                n = int(candidata)
                if n > 99:
                    # No es un número de resultado válido; dejamos de buscar
                    # en este bloque de fecha.
                    break
                numeros.append(100 if n == 0 else n)
                j += 1
            else:
                # Apareció texto que no es número antes de completar los 3;
                # este bloque de fecha no tiene el formato esperado.
                break

        if len(numeros) == 3:
            dia, mes_txt, anio = m.group(1), m.group(2), m.group(3)
            fecha_iso = f"{int(anio):04d}-{MESES[mes_txt.lower()]:02d}-{int(dia):02d}"
            return fecha_iso, numeros

    return None, None


def obtener_resultado(page, nombre, url):
    # domcontentloaded en vez de networkidle: evita el timeout que ocurría
    # en la_primera_noche por scripts que nunca dejan la red "en reposo".
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    # Esperamos un poco extra por si el JS tarda en pintar los números
    page.wait_for_timeout(4000)
    texto = page.inner_text("body")

    fecha, numeros = extraer_resultado(texto)
    if not numeros:
        raise ValueError(
            f"No se encontró un patrón válido de 'fecha/hora + 3 números en "
            f"líneas separadas' para '{nombre}' en {url} (aunque ya se "
            f"esperó a que cargara el JS)"
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
