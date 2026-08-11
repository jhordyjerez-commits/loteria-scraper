# Instrucciones - Scraper de Lotería Dominicana

## 1. Probarlo en tu computadora primero

1. Instala Python si no lo tienes (python.org)
2. Abre una terminal en esta carpeta y corre:
   ```
   pip install requests beautifulsoup4
   python scraper.py
   ```
3. Debe crear un archivo `resultados.json` con los números de cada lotería.
4. Revisa que los datos se vean bien antes de automatizarlo.

## 2. Dejarlo corriendo solo (gratis, con GitHub)

### Paso 1: Crear cuenta y repositorio
- Ve a github.com y crea una cuenta (si no tienes)
- Crea un repositorio nuevo, ej: `loteria-dominicana-scraper`
- Puede ser público o privado (privado es gratis también)

### Paso 2: Subir estos archivos
Sube toda esta carpeta al repositorio, incluyendo:
- `scraper.py`
- `.github/workflows/actualizar_resultados.yml` (¡ojo, la carpeta `.github` es invisible a veces, asegúrate de subirla!)

Puedes hacerlo arrastrando los archivos directo en la web de GitHub (botón "Add file" > "Upload files"), no necesitas usar comandos.

### Paso 3: Activar permisos de escritura
- En tu repositorio, ve a Settings > Actions > General
- Baja hasta "Workflow permissions"
- Selecciona "Read and write permissions"
- Guarda

### Paso 4: Listo
- El scraper correrá solo todos los días a las 10:00 PM (hora RD)
- Puedes forzar que corra ya mismo: ve a la pestaña "Actions" en tu repo,
  selecciona el workflow, y dale "Run workflow"
- Cada vez que corra, actualizará `resultados.json` con los números más recientes

## 3. Conectarlo a tu app Grisel Numerología

Una vez que tengas esto corriendo, el siguiente paso es que tu app HTML
lea `resultados.json` automáticamente en vez de que tú metas los números
a mano. Para eso necesito ver el archivo de tu app — súbelo en el chat
y te armo esa conexión.

## 4. Nota sobre Anguila

Anguila no está incluida en este script porque su fuente confiable usa
JavaScript pesado (no se puede leer con este método simple). Es un paso
aparte que podemos resolver después si la necesitas con urgencia.

## 5. Mantenimiento

Si en algún momento el scraper deja de traer resultados (columna "AVISO"
o "ERROR" en la consola), lo más probable es que rdparty.com cambió el
diseño de su página. Tráeme el error y ajustamos el script.
