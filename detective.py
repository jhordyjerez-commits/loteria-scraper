"""
detective.py

Objetivo: NO intentar extraer resultados. Solo navegar a cada URL,
esperar a que cargue el JS, y volcar:
  1) El texto visible completo de la página (page.inner_text("body"))
  2) El HTML completo (page.content())

a archivos en ./debug_output/<slug>.txt y <slug>.html

Con eso vemos el formato REAL de cada lotería y construimos el
regex/selector correcto, en vez de seguir adivinando.

Uso:
    pip install playwright
    playwright install chromium
    python detective.py
"""

import os
from playwright.sync_api import sync_playwright

URLS = {
    "la_primera_noche": "https://premios.do/resultados-la-primera-noche-hoy",
    "loteka": "https://premios.do/resultados-loteka-hoy",
    "lotedom": "https://premios.do/resultados-lotedom-hoy",
    "la_primera_12pm": "https://premios.do/resultados-la-primera-hoy",
    "anguila_12pm": "https://premios.do/resultados-anguilla-12pm-hoy",
    "gana_mas": "https://premios.do/resultados-gana-mas-hoy",
    "leidsa": "https://premios.do/resultados-leidsa-hoy",
}

OUT_DIR = "debug_output"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for slug, url in URLS.items():
            print(f"--- {slug} ({url}) ---")
            try:
                # domcontentloaded en vez de networkidle: evita el timeout
                # que vimos en la_primera_noche (analytics/ads que nunca
                # dejan la red "idle").
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Espera activa a que aparezca ALGO de contenido dinámico,
                # en vez de confiar ciegamente en un tiempo fijo.
                try:
                    page.wait_for_selector("body", timeout=5000)
                except Exception:
                    pass

                # Margen extra para JS que carga resultados vía fetch/ajax
                page.wait_for_timeout(4000)

                text = page.inner_text("body")
                html = page.content()

                txt_path = os.path.join(OUT_DIR, f"{slug}.txt")
                html_path = os.path.join(OUT_DIR, f"{slug}.html")

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)

                print(f"  OK -> {txt_path} ({len(text)} chars texto)")

                # Imprime el texto directo en el log de GitHub Actions
                # para poder leerlo desde el celular sin descargar nada.
                print(f"\n===== TEXTO REAL: {slug} =====")
                print(text[:3000])  # primeros 3000 caracteres alcanzan
                print(f"===== FIN: {slug} =====\n")

            except Exception as e:
                print(f"  FALLO {slug}: {e}")

        browser.close()

    print("\nListo. Revisa la carpeta debug_output/*.txt")
    print("Copia y pégame el contenido de un par de esos .txt")
    print("(los que fallaron en el scraper) para construir el patrón exacto.")


if __name__ == "__main__":
    main()
