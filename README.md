# SPACEWISE AI — Gemelo Digital y Simulación Energética de Maquinaria Industrial

Simulación horaria de 110 equipos industriales con lazo cerrado de gemelo digital:
cada máquina es un módulo independiente (`machines/<CODE>/machine.json`), se
simula su perfil de consumo en MATLAB, se persiste en SQLite, se expone en un
dashboard Flask/Chart.js y —a partir de mediciones reales o sintéticas— el
sistema estima su estado actual y **recalibra el modelo desde los datos**.

---

## 1. Visión general

```
        machines/<CODE>/machine.json          (110 módulos = 110 mini-gemelos)
                 │  autodescubrimiento por carpeta
                 ▼
   MATLAB sim_catalog ──► sim_engine / sim_machine ──► SQLite data/spacewise.db
                                  (8760 h/año, determinista con seed)
                                                   │
   Medidor real (SENTRON…)  ── POST ──►  API Flask ◄── dashboard (polling 5 s)
   Planta sintética (plant/) ─ POST ──►  /api/ingest/hourly, /api/import/real
                                                   │
                                     ┌─────────────┴─────────────┐
                                     ▼                           ▼
                          /api/machines/<c>/state      /api/machines/<c>/calibrate
                          estado actual estimado       LAZO DE VUELTA: reescribe
                          (bandas de potencia)         el machine.json (trazable)
```

Dos niveles conviven en el sistema:

- **Digital shadow** — la simulación se compara contra mediciones importadas
  (`/api/import/real` + sección *Simulado vs Real* con MAPE/bias/coverage).
- **Gemelo con lazo cerrado** — las mediciones **actualizan el modelo**
  (`/api/machines/<code>/calibrate`) y el estado instantáneo de cada máquina se
  estima en vivo desde el feed (`/api/machines/<code>/state` + panel *Gemelo*).

El canal de ingesta es el mismo para datos reales y sintéticos: no hay
supuestos de laboratorio en el backend.

Sobre estos datos corre un **Asistente IA** (Ollama): responde preguntas,
proyecta consumo/costo y evalúa escenarios "¿y si…?" en lenguaje natural. El
modelo solo razona; cada cifra proviene de herramientas de lectura que corren
Python contra la misma base de datos, así que nunca inventa números.

---

## 2. Requisitos

| Componente | Versión | Notas |
|---|---|---|
| MATLAB | R2026a o superior, con Database Toolbox | En `PATH`, o `MATLAB_BIN`/`DEFAULT_MATLAB` en `.env` |
| Python | ≥ 3.10 | El backend usa anotaciones `X \| None` |
| Dependencias Python | `pip install -r requirements.txt` | Flask, flask-cors, python-dotenv (opcional), pytest |

## 3. Instalación

```bash
git clone <repo> && cd Siemens-Spacewise
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # opcional: todo funciona con los defaults
```

---

## 4. Estructura del proyecto

```
Siemens-Spacewise/
├── README.md                     # Este archivo
├── requirements.txt              # Dependencias Python (pip)
├── orquestador.py                # Orquestador unificado: MATLAB + Flask + navegador
├── .env.example                  # Plantilla de configuración local (copiar a .env)
│
├── machines/                     # Catálogo modular: una carpeta por máquina
│   ├── _TEMPLATE/
│   │   ├── machine.json          # Plantilla estándar de módulo (mini-gemelo)
│   │   └── _README.md            # Campos, tipos, rangos, validación y calibración
│   └── <CODE>/machine.json       # 110 módulos activos (HVAC, COMP, MOT, BOMB…)
│
├── matlab/
│   ├── config/
│   │   └── simulacion_params.m   # Constantes del motor (DB_PATH, MACHINES_DIR, seed…)
│   ├── src/
│   │   ├── sim_catalog.m         # Autodescubrimiento y validación de machines/ (contrato 26 col.)
│   │   ├── sim_engine.m          # Motor: simulación anual y continua (retoma por hora)
│   │   ├── sim_machine.m         # Perfil horario de una máquina (ciclos de trabajo)
│   │   ├── sim_db.m              # Capa SQLite (esquema, inserciones, asegurar máquinas)
│   │   ├── sim_analysis.m        # Agregación y análisis de resultados
│   │   └── sim_export.m          # Exportación CSV/Excel/resumen
│   ├── scripts/
│   │   ├── init_db.m             # Crea la BD con el esquema
│   │   ├── load_catalog.m        # Carga el catálogo desde machines/
│   │   ├── run_simulation.m      # Simulación anual completa (8760 h)
│   │   ├── run_continuous.m      # Simulación horaria continua (SIM_INTERVAL)
│   │   ├── export_results.m      # Exporta la última/indicada simulación
│   │   └── migrate_catalog.m     # Migración one-off: markdown histórico → machines/
│   └── tests/
│       ├── test_sim_catalog.m            # Contrato del catálogo (26 columnas)
│       ├── test_sim_catalog_modules.m    # Descubrimiento, validación y tolerancia a `_calibration`
│       ├── test_sim_machine.m            # Perfiles por máquina
│       ├── test_sim_engine.m             # Orquestador de simulación (requiere BD)
│       └── test_sim_db.m                 # Capa de base de datos (requiere BD)
│
├── plant/                        # Mundo físico simulado (desarrollo/demo sin hardware)
│   ├── plant_sim.py              # Planta sintética determinista (seed = máquina+hora)
│   ├── calibration.py            # Lazo de calibración: bandas de potencia → re-estimación
│   ├── feed_loop.py              # Runner que stream-ea la planta al API (como un medidor)
│   └── demo_closed_loop.py       # Demo end-to-end: ingesta → calibra → MAPE diario baja
│
├── assistant/                    # Asistente de energía con IA (Ollama)
│   ├── client.py                 # Chat con Ollama (REST local, stdlib) + bucle de herramientas
│   ├── tools.py                  # Catálogo de herramientas SOLO LECTURA (reutiliza queries.py)
│   └── forecast.py               # Matemática pura: proyección, escenarios, anomalías
│
├── web/
│   ├── backend/
│   │   ├── app.py                # Fábrica Flask: config, .env, db_path, estáticos
│   │   ├── routes.py             # Blueprint /api: catálogo, simulaciones, gemelo
│   │   ├── queries.py            # Consultas SQL parametrizadas (única capa de acceso a datos)
│   │   └── tests/
│   │       ├── test_api.py               # Endpoints de catálogo/simulación/export
│   │       ├── test_dashboard.py         # Servido del dashboard
│   │       ├── test_imports.py           # Importación CSV real + comparación (MAPE sembrado)
│   │       ├── test_ingest.py            # Ingesta continua (LIVE-STREAM, idempotencia)
│   │       ├── test_calibrate.py         # Lazo de calibración (ground-truth recovery)
│   │       ├── test_calibrate_edges.py   # Bordes: sin potencia, OFF-keys, .bak byte-exacto
│   │       ├── test_state.py             # Estado estimado por bandas + ventana
│   │       └── test_assistant_api.py     # Endpoints del asistente (validación, errores, health)
│   └── frontend/
│       ├── index.html            # Dashboard: 3 charts + Simulado vs Real + Gemelo + Asistente IA
│       ├── js/
│       │   ├── api.js            # Cliente REST del dashboard
│       │   ├── charts.js         # Renderers Chart.js (hourly, categorías, top, comparación)
│       │   └── assistant.js      # Panel del Asistente IA (chat + chips de herramientas usadas)
│       └── css/
│           └── styles.css        # Estilos del panel
│
├── tests/                        # Suite de raíz (Python puro)
│   ├── test_integration.py       # Pipeline MATLAB end-to-end (init_db→export_results)
│   ├── test_plant_sim.py         # Contratos de la planta sintética
│   ├── test_feed_loop.py         # Runner de ingesta + demo de lazo cerrado
│   └── test_assistant.py         # Asistente IA: forecast puro + herramientas + bucle de chat
│
├── data/                         # (generados en runtime, fuera de git)
│   ├── schema_simulator.sql      # Esquema canónico de la BD (sí versionado)
│   ├── spacewise.db              # BD SQLite del sistema
│   ├── export/                   # Exportaciones CSV/Excel
│   └── logs/                     # matlab.log, flask.log
│
└── docs/
    ├── README.md                 # Índice de documentación del proyecto
    ├── SIMULADOR_MAQUINARIA.md   # Arquitectura y decisiones técnicas del sistema
    └── CATALOGO_EQUIPOS.md       # Catálogo histórico de 110 equipos (referencia de datos)
```

---

## 5. Alta y baja de maquinaria (módulos)

**Añadir una carpeta = añadir una máquina. Eliminarla = eliminarla.** No hay
listas centrales que editar: `sim_catalog.m` escanea `machines/`, ignora las
carpetas que empiezan con `_`, valida cada `machine.json` (campos requeridos,
tipos, rangos; errores `SIM:ModuleInvalid` que nombran la carpeta) y arma la
tabla de contrato con la que hablan motor, dashboard y exportadores.

```bash
cp -r machines/_TEMPLATE machines/NUEVA-001
# editar machines/NUEVA-001/machine.json  (código: ^[A-Z]{2,10}-\d{1,5}$)
python orquestador.py --mode once         # la máquina aparece sola en todo el sistema
```

Calibración: un módulo calibrado conserva sus **nombres de estado** (nunca se
renombran), guarda los bytes originales en `machine.json.bak` (solo la primera
vez) y deja trazabilidad en el bloque opcional `_calibration` (el catálogo
MATLAB lo tolera por diseño). Ver `machines/_TEMPLATE/_README.md`.

---

## 6. Configuración

Toda la configuración local vive en `.env` (copiar de `.env.example`, que está
versionado). Todo es opcional; los valores por defecto funcionan tal cual.
**Precedencia: línea de comando > `.env` > default del código.**

| Variable | Default | Qué controla |
|---|---|---|
| `MATLAB_BIN` / `DEFAULT_MATLAB` | (buscar en PATH) | Ruta del ejecutable de MATLAB |
| `HOST` | `127.0.0.1` | Interfaz donde escucha Flask y a donde espera el orquestador |
| `PORT` | `5000` | Puerto del servidor web |
| `FLASK_DEBUG` | `0` | Debug de Flask (1 solo en desarrollo) |
| `SECRET_KEY` | `dev-secret-change-me` | Clave de sesión Flask — **cambiar fuera de localhost** |
| `CORS_ORIGINS` | (vacío → default seguro local) | Orígenes permitidos, separados por coma |
| `DATABASE_PATH` | `../data/spacewise.db` (relativo a `web/backend/`) | BD que lee la API |
| `MODE` | `full` | Modo por defecto del orquestador: `once` / `continuous` / `full` |
| `SIM_INTERVAL` | `2` | Segundos reales entre hora simulada (modo continuo; se propaga a MATLAB) |
| `ONCE_TIMEOUT` | `3600` | Timeout del pipeline `once`, en segundos |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Servidor Ollama que usa el Asistente IA |
| `OLLAMA_MODEL` | `gemma4:cloud` | Modelo del asistente (único gratis de Ollama Cloud; cambiar si agregas créditos) |
| `OLLAMA_TIMEOUT` | `120` | Segundos de espera por respuesta del modelo |
| `PRECIO_KWH` | `0.0` | Precio por kWh para estimar costos (0 = solo energía) |
| `CURRENCY` | `USD` | Etiqueta de moneda que reporta el asistente |

Los parámetros del motor de simulación (seed default, rutas internas,
constantes físicas) viven en `matlab/config/simulacion_params.m`.

---

## 7. Ejecución

### 7.1 Todo con el orquestador (recomendado)

```bash
python orquestador.py                    # full: BD + simulación continua + API + navegador
python orquestador.py --mode continuous  # igual, sin abrir navegador
python orquestador.py --mode once        # pipeline anual completo (init_db → export) y termina
python orquestador.py --mode once --timeout 7200
```

En modos continuos: si MATLAB cae, el orquestador lo reinicia (hasta 3 veces)
**retomando desde la última hora guardada**; el dashboard sigue sirviendo datos
aun si la simulación terminara. Registros en `data/logs/`. Ctrl+C detiene todo.

### 7.2 Solo el servidor web

```bash
python web/backend/app.py     # dashboard en http://127.0.0.1:5000 con los datos existentes
```

### 7.3 Feed de mediciones (lazo continuo)

Cualquier productor —un recolector SENTRON real o la planta sintética— usa el
mismo canal:

```bash
# Medidor real (histórico o integrador): CSV con header machine_code,ts,active_power_kw
curl -F "file=@mediciones.csv" "http://127.0.0.1:5000/api/import/real?name=Octubre"

# Stream horario (el collector hace POST por hora; feed_loop simula ese rol):
.venv/bin/python plant/feed_loop.py --hours 168 --interval 0.1 --machines HVAC-001
```

### 7.4 Cerrar el lazo (calibrar)

Desde el panel **Gemelo** del dashboard (botón *Calibrar con datos reales*) o:

```bash
curl -X POST "http://127.0.0.1:5000/api/machines/HVAC-001/calibrate"
python orquestador.py --mode once   # re-simula leyendo ya los módulos calibrados
```

### 7.5 Demo de lazo cerrado sin MATLAB ni hardware

```bash
.venv/bin/python plant/demo_closed_loop.py --hours 336
# Lazo completo sobre BD y catálogo en copia temporal (no toca el repositorio):
#   AUX-001: MAPE energía diaria 203.59% -> 56.62%  [MEJORÓ]
```

---

## 8. API (todos los endpoints)

Base: `http://<HOST>:<PORT>/api`. Todas las respuestas son JSON; los errores
devuelven `{"error": "..."}` con código de estado acorde, sin stack traces.

### Catálogo de máquinas

| Endpoint | Descripción |
|---|---|
| `GET /machines` | Lista las máquinas de la última simulación completa (26 columnas del contrato). |
| `GET /machines/<code>` | Una máquina por código. `404` si el código no existe o tiene formato inválido (`400`). |

### Simulación y resultados

| Endpoint | Descripción |
|---|---|
| `GET /simulations` | Lista simulaciones con estado (`RUNNING`/`COMPLETED`), contadores y fechas. |
| `GET /simulations/<id>/summary` | Resumen KPI: energía total, media, pico, horas procesadas. Si la simulación sigue en curso, se computa on-the-fly desde `hourly_totals`. |
| `GET /simulations/<id>/hourly` | Serie horaria completa (totales) de la simulación. |
| `GET /simulations/<id>/machines/<code>` | Perfil horario de una máquina dentro de una simulación. |
| `GET /simulations/<id>/export?format=csv\|json&start=&end=` | Descarga los datos de la simulación con filtro opcional de rango `[YYYY-MM-DD]`. |

### Datos reales (importación batch)

| Endpoint | Descripción |
|---|---|
| `POST /import/real` | Importa un **CSV** de mediciones (`machine_code,ts,active_power_kw[,energy_kwh,current_a,power_factor,voltage_v]`; multipart o `text/csv`). Validación fila a fila **antes** de escribir: si una fila es inválida, no se escribe nada (`400` con hasta 20 errores y `error_count`). Éxito: `201 {import_id, rows}`. |
| `GET /imports` | Lista importaciones, más nueva primero. |
| `GET /imports/<id>` | Detalle con conteos por máquina y rango temporal. |
| `DELETE /imports/<id>` | Elimina la importación y sus mediciones (cascade explícito en una transacción). |
| `GET /simulations/<id>/compare?machine=<CODE>&import_id=<n>` | Compara perfil simulado vs mediciones reales: series alineadas por `ts` exacto + `mape_pct` (excluye horas reales en 0), `mean_bias_pct`, `hours_compared`, `coverage_pct`. Sin `import_id` usa la última importación. Sin solapamiento: métricas `null`, nunca error. |

### Gemelo (lazo cerrado)

| Endpoint | Descripción |
|---|---|
| `POST /ingest/hourly` | **Ingesta continua**: `{"records":[{machine_code, ts, active_power_kw, …}]}`. Escribe en un único import vivo `LIVE-STREAM`; idempotencia por `(machine_code, ts)` (re-enviar una hora la actualiza, no la duplica); validación todo-o-nada como el CSV. Respuesta: `200 {import_id, inserted, updated, total}`. |
| `GET /machines/<code>/state?window=48&import_id=<n>` | **Estado actual estimado**: clasifica las últimas N horas medidas (cap 168) en bandas de potencia derivadas del modelo del módulo (OFF/STANDBY/PARTIAL/RUNNING) y responde la banda de la hora más reciente, `power_kw`, `last_ts`, `confidence` y el nombre de estado real del módulo. Sin datos: `state: "UNKNOWN"` (el dashboard degrada sin errores). |
| `POST /machines/<code>/calibrate?import_id=<n>` | **Lazo de calibración**: reescribe `machines/<CODE>/machine.json` a partir de las mediciones — shares de `work_cycles` (los nombres nunca se renombran), `load_factor`, `standby_pct`, `hours_per_day`, `days_per_week`. Protecciones: `machine.json.bak` con los bytes originales (solo la primera calibración), traza `_calibration` con `before/after` y `calibrated_from {import_id, start_ts, end_ts, hours_analyzed}`, mínimo 24 horas de datos, rechazo de módulo roto **antes** de escribir. Sin `import_id` calibra contra `LIVE-STREAM`. Respuesta: `200 {machine_code, import_id, hours_analyzed, before, after}`; `400` sin datos suficientes, `404` sin módulo, `500` con módulo inválido (archivo intacto). Tras calibrar, re-simular para ver el modelo corregido en `compare`. |

### Asistente IA (Ollama)

| Endpoint | Descripción |
|---|---|
| `POST /assistant/chat` | Pregunta en lenguaje natural. Body `{"message": "...", "history": [{role, content}, …]}`. El modelo responde **solo con cifras obtenidas de herramientas de lectura** (nunca inventadas) y devuelve `{reply, tool_calls, model, rounds}`, donde `tool_calls` lista exactamente qué herramientas se ejecutaron. Si Ollama no está disponible: `503 {available:false}`; error del modelo: `502`. |
| `GET /assistant/health` | Indica si el backend de Ollama responde (`{available, model, ollama_version}`), sin invocar al modelo (no gasta cuota). |

Herramientas que el asistente puede usar (todas de **solo lectura**; calibración
e ingesta quedan fuera de su alcance a propósito): `listar_simulaciones`,
`resumen_energetico`, `top_consumidores`, `detalle_maquina`,
`comparar_real_vs_simulado`, `proyectar_consumo`, `simular_escenario`,
`detectar_anomalias`, `estado_actual_maquina`.

### Salud

| Endpoint | Descripción |
|---|---|
| `GET /health` / `GET /api/health` | Estado del servidor (lo usa el orquestador para esperar el arranque). |

---

## 9. Dashboard

`http://127.0.0.1:5000` — se refresca solo cada 5 s y contiene:

1. **Consumo horario** (totales de la simulación en curso o última completa).
2. **Por categoría** (agregado HVAC, Bombas, Compresores, …).
3. **Top consumidores**.
4. **Simulado vs Real**: selector de importación, gráfico superpuesto y badges
   de MAPE/bias/coverage/horas comparadas.
5. **Gemelo (lazo cerrado)**: selector de máquina, badge de estado actual en
   vivo (banda + potencia + confianza) y botón *Calibrar con datos reales* con
   resumen antes → después.
6. **Asistente IA**: chat en lenguaje natural para consultas, costos,
   proyecciones y escenarios "¿y si…?". Cada respuesta muestra chips con las
   herramientas que usó, y un indicador avisa si la IA no está disponible.

### Asistente IA — requisitos y funcionamiento

- **Requisito único**: [Ollama](https://ollama.com) instalado y con sesión
  iniciada una vez (`ollama signin`). El modelo por defecto `gemma4:cloud` corre
  en la nube de Ollama (plan gratuito) y soporta llamadas a herramientas. **No
  hay dependencias de pip nuevas**: el cliente habla con Ollama por su API REST
  local (`localhost:11434`) usando solo la librería estándar.
- **La IA no inventa números**: todas las cifras (consumo, costo, MAPE, estado,
  proyección, ahorro) las calcula código Python en herramientas de **solo
  lectura**; el modelo solo decide qué herramienta llamar e interpreta el
  resultado en español. Las operaciones que modifican el sistema (calibración,
  ingesta) **no** se exponen al modelo.
- **Costo**: para que el asistente reporte dinero y no solo kWh, define
  `PRECIO_KWH` en el `.env` (p. ej. `PRECIO_KWH=0.15`).
- Para cambiar de modelo (p. ej. tras agregar créditos a Ollama), solo edita
  `OLLAMA_MODEL` en el `.env`.

## 10. Testing

```bash
# Python (única fuente de verdad rápida; usa el .venv del repo)
.venv/bin/python -m pytest web/backend/tests tests -q -k "not TestIntegration"
#   → 172 passed, 9 deselected (backend: api, dashboard, imports, ingest,
#      calibrate, edges, state, assistant-api; raíz: planta sintética, feed loop,
#      demo de lazo y asistente IA)

# Tests MATLAB (suites puras de catálogo/perfiles: 44 verdes)
cd matlab/tests
matlab -batch "runtests('test_sim_catalog_modules')"   # módulos + validación + tolerancia a _calibration
matlab -batch "runtests"                               # suite completa (incl. suites de BD)

# Pipeline completo end-to-end (MATLAB + Flask)
python orquestador.py --mode once
```

**Fallos ambientales conocidos** (no son regresiones del código):
`run_simulation.m`/`test_integration.py` materializan ~963k mediciones en
memoria y pueden recibir SIGKILL en máquinas de ~16 GB; las suites `test_sim_db.m`
y los tests que consumen una simulación completa dependen de ese estado. El
modo `continuous` —el que usa el orquestador— no acumula el año en memoria y
funciona en esas máquinas.

## 11. Seguridad

- **SQL parametrizado** en todas las consultas (`?` placeholders; sin string interpolation).
- **Validación estricta de inputs**: códigos `^[A-Z]{2,10}-\d{1,5}$`, timestamps `YYYY-MM-DD HH:MM:SS` (strptime), números finitos; escrituras **atómicas** (todo-o-nada).
- **Escrituras auditables**: la calibración preserva backups `.bak` byte-exactos y trazabilidad `_calibration` dentro del módulo.
- **CORS** con orígenes explícitos (default seguro de desarrollo); **sin stack traces** en las respuestas de error.
- **Secretos fuera del repo**: `.env` está gitignoreado; `SECRET_KEY` debe cambiarse para despliegues reales.

## 12. Documentación

| Documento | Contenido |
|---|---|
| `docs/README.md` | Índice de documentación del proyecto |
| `docs/SIMULADOR_MAQUINARIA.md` | Arquitectura técnica: capas, contrato del catálogo, motor, lazo del gemelo, métricas |
| `docs/CATALOGO_EQUIPOS.md` | Catálogo histórico de los 110 equipos (referencia de datos y entrada de `migrate_catalog.m`) |
| `machines/_TEMPLATE/_README.md` | Guía de campos de un módulo, validación y reglas de calibración |
| `.env.example` | Todas las variables de configuración con sus defaults |

## Licencia

Proyecto interno Siemens Spacewise.
