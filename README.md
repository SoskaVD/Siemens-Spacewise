# Simulador de Maquinaria Industrial - Siemens Spacewise

Sistema de simulación energética de maquinaria industrial con 110 equipos, generación de perfiles horarios (8760h), persistencia SQLite, backend Flask y panel web con visualización Chart.js.

## Gemelo digital: simulación + comparación contra mediciones reales

El sistema funciona como *digital shadow* de la maquinaria: cada máquina tiene un módulo propio (mini-gemelo), se simula su perfil horario y se compara contra mediciones reales importadas por CSV, con error porcentual (MAPE) visible en el dashboard.

### Estructura modular de máquinas (`machines/`)

Una carpeta por máquina. **Añadir una carpeta = añadir una máquina; eliminarla = eliminarla.** El catálogo de MATLAB se autodescubre escaneando `machines/` (se ignoran las carpetas que empiezan con `_`).

```
machines/
├── _TEMPLATE/            # Plantilla estándar (no se carga como máquina)
│   ├── machine.json      # Copiar y completar
│   └── _README.md        # Campos, tipos, rangos y validación
├── HVAC-001/
│   └── machine.json      # Especificación + ciclos de trabajo (work_cycles)
└── ...                   # 110 módulos migrados desde docs/CATALOGO_EQUIPOS.md
```

Para dar de alta maquinaria nueva:

```bash
cp -r machines/_TEMPLATE machines/NUEVA-001
# editar machines/NUEVA-001/machine.json (código: ^[A-Z]{2,10}-\d{1,5}$)
matlab -batch "cd('matlab/tests'); runtests('test_sim_catalog_modules')"
python orquestador.py            # la máquina aparece sola en dashboard y export
```

`docs/CATALOGO_EQUIPOS.md` quedó solo como referencia histórica de datos; la fuente en tiempo de ejecución son las carpetas `machines/`. La migración desde el markdown puede re-ejecutarse con `matlab/scripts/migrate_catalog.m`.

## Características

- **Motor de simulación MATLAB**: Genera perfiles de consumo horario para las máquinas definidas en `machines/`
- **Catálogo modular**: 110 equipos con especificaciones eléctricas y perfiles de consumo, un módulo `machine.json` por máquina con autodescubrimiento por carpeta
- **Persistencia SQLite**: Almacena máquinas, simulaciones, mediciones horarias, resultados e importaciones de datos reales
- **Backend Flask API**: Endpoints REST para consultar datos y exportar resultados
- **Panel web**: Visualización interactiva con Chart.js (gráficos horarios, por categoría, top consumidores)
- **Exportación**: CSV y JSON con filtros por fecha
- **Importación de datos reales**: CSV de mediciones (`POST /api/import/real`) cargable desde el dashboard
- **Comparación gemelo vs real**: Superposición horario simulado/real con MAPE y sesgo en el dashboard
- **Ingesta continua (feed)**: `POST /api/ingest/hourly` alimenta un import vivo `LIVE-STREAM` con idempotencia por (máquina, hora)
- **Estado estimado del gemelo**: `GET /api/machines/<code>/state` clasifica las últimas horas medidas en bandas (RUNNING/PARTIAL/STANDBY/OFF) y lo muestra en el dashboard
- **Calibración con lazo de vuelta**: `POST /api/machines/<code>/calibrate` reescribe el `machine.json` (shares, load_factor, standby_pct, horario) desde mediciones reales, con backup `.bak` y traza `_calibration`
- **Planta sintética reproducible**: `plant/` genera mediciones con ground-truth desviada del catálogo, para cerrar y demostrar el lazo sin hardware

## Gemelo digital de lazo cerrado (shadow → twin)

El sistema recorre los dos niveles de la escalera de gemelo digital: la **sombra** (comparar lo que el modelo dice contra lo que el medidor mide) y el **gemelo** (que la medición actualice el modelo — lazo bidireccional):

```
planta física          ingesta            estimación        calibración (lazo A)
(SENTRON real   ──►  /api/ingest/hourly ──► /state en el ──► /calibrate reescribe
 o planta            (LIVE-STREAM)          dashboard         machines/<CODE>/machine.json
 sintética)                                                        │
                                            re-simulación ◄───────┘ (MATLAB lee los
                                            → MAPE menor            módulos calibrados)
```

- Cada `machines/<CODE>/machine.json` es un **mini-gemelo**: identidad propia + estado estimado + memoria de calibración (`_calibration` con `before/after` y `calibrated_from: import_id`) + salvaguarda de los valores originales (`machine.json.bak`, escrito solo la primera vez).
- Los nombres de estado del `work_cycles` **nunca se renombran**: la calibración ajusta proporciones, preservando el contrato con MATLAB (incluidos los heredados como `n_plena`).

### Demo sin hardware (planta sintética)

`plant/` es el mundo físico simulado: mediciones horarias deterministas (seed = máquina+hora) deliberadamente desviadas del catálogo — turnos corridos, degradación de potencia 1.05–1.25×, ruido, cortes. Sirve para desarrollar y demostrar el lazo sin acceso a maquinaria, y es **exactamente el mismo canal de API que usará un medidor real**:

```bash
# 1. Demo de lazo cerrado completo (autocontenido, no toca el worktree):
.venv/bin/python plant/demo_closed_loop.py --hours 336
#   → por máquina: MAPE de energía diaria ANTES → DESPUÉS (ej. 203% → 57%)

# 2. O en vivo: servidor + stream + panel Gemelo
python orquestador.py                        # o el backend Flask solo
.venv/bin/python plant/feed_loop.py --hours 168 --interval 0.1 --machines HVAC-001
#   → el dashboard muestra estado actual y el botón "Calibrar con datos reales"
```

### Cambiar de planta sintética a datos reales

No hay que tocar el backend ni el dashboard:

- **Un medidor/colector (SENTRON, Modbus gateway…)**: que haga `POST /api/ingest/hourly` con `{"records":[{machine_code, ts, active_power_kw}]}` por hora (mismo contrato que `feed_loop.py`).
- **Un export histórico**: CSV con `machine_code,ts,active_power_kw` vía `POST /api/import/real` o el panel, y calibrar con `?import_id=<id>`.
- Tras calibrar, **re-simular** (`python orquestador.py` o `run_simulation`) para que la comparación `GET /api/simulations/<id>/compare` refleje el modelo corregido.

## Requisitos

### MATLAB
- MATLAB R2026a o superior
- Database Toolbox (para SQLite)
- Agregar `matlab/bin` al PATH o definir `MATLAB_BIN`
  (o copiar `.env.example` a `.env` y fijar `DEFAULT_MATLAB`; el `.env` no se sube al repositorio)

### Python
- Python 3.10+
- Dependencias en `requirements.txt` (Flask incluido):
  ```bash
  pip install -r requirements.txt
  ```

## Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone <repo-url>
   cd Siemens-Spacewise
   ```

2. **Instalar dependencias Python**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verificar MATLAB**:
   ```bash
   matlab -batch "disp('MATLAB OK')"
   ```

## Uso

### 1. Lanzar todo con el orquestador (recomendado)

```bash
python orquestador.py
```

Es el modo `full` (por defecto). En un solo comando:
1. Crea `data/spacewise.db` con el esquema si todavía no existe.
2. Inicia la simulación continua de MATLAB (una hora simulada cada 2 s; se
   reinicia sola si falla y retoma desde la última hora guardada).
3. Inicia el servidor Flask, que sirve la API y el dashboard.
4. Espera a que el servidor responda y abre `http://127.0.0.1:5000`.

`Ctrl+C` detiene todos los procesos. Los registros quedan en `data/logs/`
(`matlab.log` y `flask.log`).

Opciones:
```bash
python orquestador.py --interval 5     # segundos reales por hora simulada
python orquestador.py --no-browser     # no abrir el navegador
python orquestador.py --mode continuous  # lo mismo, sin abrir el navegador
python orquestador.py --mode once      # pipeline de un año completo y termina
```

El modo `once` ejecuta en orden:
- `init_db.m`: Crea la base de datos SQLite con el esquema
- `load_catalog.m`: Carga el catálogo de 110 máquinas
- `run_simulation.m`: Ejecuta simulación de 8760 horas
- `export_results.m`: Exporta resultados a CSV

### 2. Dashboard

Con el orquestador activo, abrir `http://127.0.0.1:5000`. Muestra la
simulación en ejecución y se actualiza solo cada 5 segundos. El puerto se
cambia con la variable de entorno `PORT`.

### 3. Solo el servidor web (sin simulación)

```bash
python web/backend/app.py
```

Sirve el dashboard en `http://127.0.0.1:5000` con los datos que ya existan en
`data/spacewise.db`. No hace falta abrir `web/frontend/index.html` a mano: el
servidor lo entrega en `/`.

## Estructura del proyecto

```
Siemens-Spacewise/
├── machines/
│   ├── _TEMPLATE/                  # Plantilla estándar de módulo de máquina
│   │   ├── machine.json
│   │   └── _README.md
│   └── <CODE>/machine.json         # 110 módulos (uno por máquina = mini-gemelo)
├── plant/                          # Mundo físico simulado (sin hardware)
│   ├── plant_sim.py                # Planta sintética determinista con ground-truth
│   ├── calibration.py              # Lazo A: bandas de potencia → re-estimación
│   ├── feed_loop.py                # Lazo B: stream de horas al API
│   └── demo_closed_loop.py         # Demo: ingesta → calibra → MAPE diario baja
├── docs/
│   ├── CATALOGO_EQUIPOS.md         # Catálogo original (referencia; fuente de la migración)
│   └── SIMULADOR_MAQUINARIA.md     # Especificaciones técnicas
├── matlab/
│   ├── config/
│   │   └── simulacion_params.m     # Parámetros de simulación (incl. MACHINES_DIR)
│   ├── src/
│   │   ├── sim_catalog.m           # Autodescubrimiento de modules machines/
│   │   ├── sim_engine.m            # Motor de simulación
│   │   ├── sim_machine.m           # Perfil individual de máquina
│   │   ├── sim_db.m                # Capa SQLite
│   │   ├── sim_analysis.m          # Análisis y agregación
│   │   └── sim_export.m            # Exportación CSV/Excel
│   ├── scripts/
│   │   ├── init_db.m               # Inicializar base de datos
│   │   ├── load_catalog.m          # Cargar catálogo desde machines/
│   │   ├── migrate_catalog.m       # Migración markdown → machines/ (one-off)
│   │   ├── run_simulation.m        # Ejecutar simulación
│   │   └── export_results.m        # Exportar resultados
│   └── tests/
│       ├── test_sim_catalog.m      # Tests del catálogo
│       ├── test_sim_catalog_modules.m  # Tests de módulos y validación
│       ├── test_sim_machine.m      # Tests de perfiles
│       ├── test_sim_engine.m       # Tests del motor
│       └── test_sim_db.m           # Tests de base de datos
├── web/
│   ├── backend/
│   │   ├── app.py                  # Aplicación Flask
│   │   ├── routes.py               # Endpoints API (imports, compare)
│   │   ├── queries.py              # Consultas SQL parametrizadas
│   │   └── tests/
│   │       ├── test_api.py         # Tests de la API
│   │       ├── test_dashboard.py   # Tests del dashboard
│   │       └── test_imports.py     # Tests de importación y comparación real
│   └── frontend/
│       ├── index.html              # Panel principal + sección "Simulado vs Real"
│       ├── js/
│       │   ├── api.js              # Cliente API
│       │   └── charts.js           # Visualizaciones Chart.js (4º chart comparativo)
│       └── css/
│           └── styles.css          # Estilos
├── data/
│   ├── spacewise.db                # Base de datos SQLite
│   └── export/                     # Resultados exportados
├── tests/
│   └── test_integration.py         # Tests de integración
├── orquestador.py                  # Orquestador del pipeline MATLAB
└── requirements.txt                # Dependencias Python
```

## API Endpoints

### Máquinas
- `GET /api/machines` - Lista todas las máquinas
- `GET /api/machines/<code>` - Detalle de una máquina

### Simulaciones
- `GET /api/simulations` - Lista simulaciones
- `GET /api/simulations/<id>/summary` - Resumen de simulación
- `GET /api/simulations/<id>/hourly` - Totales horarios
- `GET /api/simulations/<id>/machines/<code>` - Mediciones de máquina
- `GET /api/simulations/<id>/compare?machine=<code>&import_id=<n>` - Comparación simulado vs real (series alineadas + MAPE)
- `GET /api/simulations/<id>/export?format=csv&start=...&end=...` - Exportar datos

### Datos reales (importaciones)
- `POST /api/import/real` - Cargar CSV de mediciones reales (`machine_code,ts,active_power_kw[,energy_kwh,current_a,power_factor,voltage_v]`; multipart o text/csv; escritura atómica)
- `GET /api/imports` - Lista importaciones
- `GET /api/imports/<id>` - Detalle con conteos por máquina
- `DELETE /api/imports/<id>` - Eliminar importación y sus mediciones

### Gemelo (lazo cerrado)
- `POST /api/ingest/hourly` - Ingesta incremental al import vivo `LIVE-STREAM`; idempotencia por (machine_code, ts); validación todo-o-nada igual que el CSV
- `GET /api/machines/<code>/state?window=48` - Estado actual estimado por bandas de potencia sobre las últimas N horas del feed (default `LIVE-STREAM`); sin datos responde `UNKNOWN` (nunca rompe el dashboard)
- `POST /api/machines/<code>/calibrate?import_id=N` - Lazo de calibración: reescribe `machines/<CODE>/machine.json` (shares, `load_factor`, `standby_pct`, `hours_per_day`, `days_per_week`) desde las mediciones; preserva nombres de estado, crea `machine.json.bak` una sola vez y agrega la traza `_calibration`; requiere ≥24 horas

### Salud
- `GET /api/health` (alias `/health`) - Estado del servidor

### 4. Cargar mediciones reales y comparar

Desde el dashboard (sección **Simulado vs Real**) o por API:

```bash
curl -F "file=@mediciones.csv" \
  "http://127.0.0.1:5000/api/import/real?name=Campana+Octubre"

curl "http://127.0.0.1:5000/api/simulations/1/compare?machine=HVAC-001"
```

El CSV debe usar `machine_code` existentes en `machines/` y marcas `YYYY-MM-DD HH:MM:SS` (la grilla horaria de la simulación comienza en 2026-01-01 00:00). La importación es atómica: si una fila es inválida, no se escribe nada. El dashboard muestra el chart superpuesto y el error medio (MAPE) junto con las horas comparadas.

## Testing

### Tests MATLAB
```bash
cd matlab/tests
matlab -batch "runtests('test_sim_catalog_modules')"   # catálogo modular (rápido)
matlab -batch "runtests"                               # suite completa (incl. tests de BD)
```

### Tests Python Backend
```bash
cd web/backend
pytest tests/ -v
```

### Tests de Integración
```bash
python -m pytest tests/test_integration.py -v
```

### Fallos ambientales conocidos (preexistentes en main)
- `run_simulation.m` (pipeline `--mode once`) falla también en la base: la sesión MATLAB con parfor que materializa los ~963k perfiles horarios completos recibe SIGKILL por memoria en máquinas de ~16 GB. El modo `continuous` (el que usan el orquestador y el demo) no acumula el año en memoria y funciona.
- `test_sim_db.m` ya fallaba en la base (errores previos dependientes de estado de la BD); no es gate de regresión del cambio actual.

## Seguridad

- **SQL parametrizado**: Todas las consultas usan placeholders (`?`)
- **Validación de inputs**: Machine codes, IDs y fechas validados con regex; los CSV importados se validan fila a fila antes de escribir (importación atómica)
- **CORS**: Configurado con orígenes explícitos
- **Sin stack traces**: Errores genéricos en producción
- **Variables de entorno**: Configuración sensible en `.env`

## Documentación adicional

- `machines/_TEMPLATE/_README.md` - Guía de la plantilla para añadir nueva maquinaria
- `docs/CATALOGO_EQUIPOS.md` - Catálogo original de 110 equipos (referencia de datos)
- `docs/SIMULADOR_MAQUINARIA.md` - Documento de planificación original del simulador
- `docs/archive/` - Documentación del proyecto anterior (gemelo digital del edificio)

## Estado del proyecto

✅ Motor de simulación MATLAB completo  
✅ Catálogo modular `machines/` con autodescubrimiento por carpeta y plantilla `_TEMPLATE`  
✅ Persistencia SQLite funcional  
✅ Backend Flask API  
✅ Panel web con visualizaciones  
✅ Exportación CSV/JSON  
✅ Importación de mediciones reales (CSV) con carga atómica y validación fila a fila  
✅ Comparación gemelo vs real en el dashboard (series superpuestas + MAPE y horas comparadas)  
✅ Tests Python backend: 65 pasando (API, dashboard, importaciones, comparación)  
✅ Limpieza: pipeline CEN legado (`dt_*`) eliminado; recuperable desde el historial de git  

## Licencia

Proyecto interno Siemens Spacewise.

## Contacto

Para consultas sobre el simulador, contactar al equipo de desarrollo.
