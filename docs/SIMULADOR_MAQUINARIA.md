# Simulador de Maquinaria Industrial — Arquitectura y decisiones técnicas

**Proyecto:** SPACEWISE AI (concurso Siemens)
**Estado:** documento técnico del sistema vigente; para uso operativo ver el [`README.md`](../README.md) de la raíz.

---

## 1. Objetivos del sistema

1. Representar y simular el comportamiento energético horario de ≥100 máquinas
   industriales individuales (perfiles de 8760 h/año, deterministas por seed).
2. Estructura modular: **una carpeta = una máquina** (`machines/<CODE>/machine.json`).
   Alta y baja de maquinaria sin tocar código.
3. Panel web con totales, por categoría y por máquina; exportación por rangos.
4. Gemelo digital funcional: importar mediciones reales, estimar el estado
   actual de cada máquina y **recalibrar el modelo desde los datos** (lazo de
   vuelta), demostrable sin hardware mediante una planta sintética.

## 2. Arquitectura por capas

```
catálogo        machines/<CODE>/machine.json          fuente de verdad por máquina
   │  sim_catalog.m (descubrimiento + validación + contrato 26 col.)
motor           sim_engine.m / sim_machine.m          perfiles horarios (anual y continuo)
persistencia    sim_db.m + data/schema_simulator.sql  SQLite (machines, simulations,
   │                                                   machine_measurements, hourly_totals,
API             web/backend (Flask)                   import_data, import_measurements)
presentación    web/frontend (Chart.js, polling 5 s)  dashboard: shadow + Gemelo
lazo gemelo     /api/ingest/hourly → /api/machines/<c>/state → …/calibrate → machine.json
planta sint.    plant/                                mundo físico simulado (demo/dev sin hardware)
```

**Regla de dependencias:** MATLAB escribe la BD; Flask solo lee la BD de
simulación y **escribe** únicamente las tablas de importación/mediciones reales
y los módulos `machine.json` (calibración). `queries.py` es la única capa de
acceso SQL del backend (consultas parametrizadas).

## 3. El módulo de máquina (mini-gemelo)

`machines/<CODE>/machine.json` contiene: identidad (`machine_code`, `name`,
`category`, fabricante/modelo), especificación eléctrica (`rated_power_kw`,
`voltage_v`, `current_a`, `power_factor`, `phases`, `thd_pct`), régimen
(`hours_per_day`, `days_per_week`, `load_factor`, `seasonal_variability`),
`work_cycles` (shares por estado operativo), arranque (`startup_time_s`,
`startup_multiplier`, `standby_pct`), y clasificación (`criticality`,
`flexibility`, `active`). La guía completa de campos y rangos está en
[`machines/_TEMPLATE/_README.md`](../machines/_TEMPLATE/_README.md).

Contratos que definen el sistema:

- **Contrato de catálogo (26 columnas).** `sim_catalog.load()` devuelve una
  tabla MATLAB de 26 columnas estables; es la interfaz consumida por
  `sim_engine`, `sim_machine` y `sim_db.ensureMachines`. Pinneado por
  `test_sim_catalog.m`.
- **Autodescubrimiento.** El loader escanea `machines/`, ignora carpetas que
  empiezan con `_`/`.`, exige campos requeridos con tipos/rangos (errores
  `SIM:ModuleInvalid` que nombran carpeta y campo), ordena por código y asigna
  `machine_id` secuencial. Claves opcionales desconocidas se toleran
  deliberadamente (permite metadatos como `_calibration` sin romper MATLAB).
- **Códigos.** `^[A-Z]{2,10}-\d{1,5}$` es el regex compartido por MATLAB,
  backend y validación de CSVs; cualquier capa que acepte un código lo valida.
- **Nombres de estado heredados.** El catálogo migrado conserva claves
  originales del parseo histórico (p. ej. `n_plena`, `n_parcial`, `Standby`).
  La calibración ajusta proporciones y **nunca renombra estados**: el contrato
  round-trip está testeado.

## 4. Motor de simulación

- **Anual (`run_simulation.m`):** genera 8760 h por máquina (parfor), inserta
  `machine_measurements` + `hourly_totals` y marca resultados. Grilla horaria
  desde `2026-01-01 00:00`.
- **Continuo (`run_continuous.m`):** `sim_engine.runContinuous` emite una hora
  simulada cada `SIM_INTERVAL` segundos reales y **retoma desde la última hora
  guardada** si se reinicia (el orquestador reinicia MATLAB hasta 3 veces).
  No acumula el año en memoria: es el modo que corre en producción/demo.
- **Determinismo:** seed por simulación (`simulacion_params.DEFAULT_SEED`);
  el perfil de cada máquina es reproducible dado (catálogo, seed).

## 5. Modelo de datos (resumen)

| Tabla | Rol |
|---|---|
| `machines` | Espejo del catálogo (inserta MATLAB vía `ensureMachines`) |
| `simulations` | Corridas con estado `RUNNING`/`COMPLETED`, contadores, semilla |
| `machine_measurements` | Perfil horario simulado por máquina (kW por hora) |
| `hourly_totals` | Totales horarios por simulación |
| `import_data` | Encabezados de importaciones batch y del feed vivo `LIVE-STREAM` |
| `import_measurements` | Mediciones reales/ingresadas: `(import_id, machine_code, ts, kW, …)` |

Decisiones: las mediciones reales usan las tablas de importación **preexistentes**
del esquema (sin esquema nuevo); `import_measurements` no tiene constraint
`(machine_code, ts)`, por lo que la idempotencia de la ingesta continua se
resuelve en la capa de aplicación (dentro de una transacción `BEGIN IMMEDIATE`).

## 6. Gemelo digital: lazo cerrado

Escalera conceptual (Grieves): *digital model* (sin enlace) → *digital shadow*
(enlace físico→virtual) → *digital twin* (enlace de vuelta: los datos corrigen
el modelo). El sistema implementa ambos tramos:

**Shadow (comparación).** `POST /api/import/real` (CSV validado fila a fila,
atómico) y `GET /api/simulations/<id>/compare` alinean simulación y mediciones
por igualdad exacta de `ts` (la grilla horaria arranca en 2026-01-01). Métricas:
`mape_pct` (excluye horas reales en 0 — guard de división), `mean_bias_pct`,
`hours_compared` y `coverage_pct`; solapamiento vacío produce métricas `null`,
nunca error.

**Ingesta continua (Camino B).** `POST /api/ingest/hourly` escribe de a lotes
horarios contra el import vivo único `LIVE-STREAM`; reenviar una hora la
actualiza (upsert por `(machine_code, ts)`), la validación es la misma que la
del CSV y todo el lote es atómico. Es exactamente el canal que usaría un
recolector real (SENTRON/Modbus gateway/MQTT bridge): cambiar de planta
sintética a hardware no toca backend ni dashboard.

**Estado estimado.** `GET /api/machines/<code>/state` clasifica las últimas N
horas medidas (default 48, cap 168) en **bandas de potencia** y reporta la
banda de la hora más reciente con confianza; sin datos degrada a `UNKNOWN`
para no romper el dashboard.

**Calibración (Camino A).** `POST /api/machines/<code>/calibrate` (mínimo 24 h,
default `LIVE-STREAM`) re-estima `work_cycles` (shares), `load_factor`,
`standby_pct`, `hours_per_day` y `days_per_week` a partir de las bandas —
derivadas del propio prior del módulo (OFF ≈ 0; STANDBY ≈ `rated·standby_pct/100`;
RUNNING ≈ `rated·load_factor`; PARTIAL ≈ 0.65× RUNNING) — y reescribe
`machine.json`:

- los nombres de estado se conservan siempre;
- `machine.json.bak` guarda los bytes originales la primera vez (nunca se pisa);
- el bloque opcional `_calibration` deja `before/after` + `calibrated_from
  {import_id, start_ts, end_ts, hours_analyzed, calibrated_at}`;
- escrituras todo-o-nada: un módulo ilegible se rechaza **antes** de tocar
  nada; sin suficientes mediciones → 400 tipado (`InsufficientMeasurementsError`).

Tras calibrar, **re-simular** para que `compare` mida el modelo corregido.

**Métricas honestas.** Para comparar perfiles estadísticos contra mediciones,
la métrica de demostración es **MAPE de energía diaria**: el MAPE horario está
dominado por las horas standby (potencias pequeñas donde el error relativo
explota) y penaliza como "error de modelo" los simples desfasajes de timing.
El compare horario por hora sigue disponible para inspección visual.

## 7. Planta sintética (`plant/`)

Sin acceso a maquinaria ni datos reales (restricción del proyecto), el mundo
físico también se simula, con ground-truth conocida:

- `plant_sim.py`: serie horaria determinista por `(machine_code, hora)` —
  shares con drift sembrado, horario desplazado respecto al prior, degradación
  de potencia 1.05–1.25×, ruido gaussiano σ=2% con clamp ≥0, cortes
  (outages) contiguos y arranques. Salida compatible byte a byte con el
  contrato de importación.
- `feed_loop.py`: productor que stream-ea la planta al API (rol de medidor).
- `calibration.py`: lógica del lazo (bandas y re-estimación; sin dependencias
  de Flask/BD, testeable en aislado).
- `demo_closed_loop.py`: lazo completo end-to-end sobre BD/catálogo en copia
  temporal: ingesta → calibración → **MAPE diario antes/después** (demo real:
  203→57 %, 184→36 %, 269→75 %). Cero mutación del repositorio.

## 8. Orquestador y configuración

`orquestador.py` centraliza el ciclo de vida: prepara la BD, lanza Flask y la
simulación continua con vigilancia/reinicio, espera el healthcheck y abre el
dashboard; `--mode once` corre el pipeline anual completo y termina.
Configuración por capas con precedencia **CLI > `.env` > default**:
`MODE`, `SIM_INTERVAL`, `HOST`, `PORT`, `DATABASE_PATH`, `SECRET_KEY`,
`CORS_ORIGINS`, `FLASK_DEBUG`, `MATLAB_BIN`/`DEFAULT_MATLAB`, `ONCE_TIMEOUT`
(ver `.env.example`). `.env` queda fuera de git (por integrante).

## 9. Estrategia de pruebas

| Suite | Alcance | Runner |
|---|---|---|
| `matlab/tests/test_sim_catalog.m` + `test_sim_catalog_modules.m` | Contrato de 26 columnas, descubrimiento, validación, tolerancia a `_calibration` | `matlab -batch "runtests(...)"` |
| `matlab/tests/test_sim_machine.m` | Perfiles por máquina | idem |
| `matlab/tests/test_sim_engine.m`, `test_sim_db.m` | Motor y BD (dependen de simulación completa) | idem — ver nota ambiental |
| `web/backend/tests/test_api.py`, `test_dashboard.py` | Endpoints existentes y servido del panel | `.venv/bin/python -m pytest` |
| `web/backend/tests/test_imports.py` | Import CSV + compare (MAPE con valores sembrados exactos) | idem |
| `web/backend/tests/test_ingest.py` | Ingesta continua, idempotencia, atomicidad | idem |
| `web/backend/tests/test_calibrate.py`, `test_calibrate_edges.py` | Lazo A: recuperación contra ground-truth, bak byte-exacto, OFF-keys, guards | idem |
| `web/backend/tests/test_state.py` | Bandas, ventana, `UNKNOWN`, LIVE-STREAM default | idem |
| `tests/test_plant_sim.py`, `tests/test_feed_loop.py` | Contratos de planta sintética + runner/demo | idem |
| `tests/test_integration.py` | Pipeline MATLAB end-to-end | idem (ver nota) |

**Nota ambiental:** las corridas que materializan el año completo en memoria
(~963k mediciones por corrida 110×8760) reciben SIGKILL en máquinas de ~16 GB;
`TestIntegration` 03–05 y las suites MATLAB de BD se consideran **baseline
ambiental, no gate de regresión**. El modo continuo y todas las suites
unitarias/integración Python corren en esas máquinas (estado actual: 138
passed, 5 deselected).

## 10. Decisiones de diseño registradas

1. **Catálogo por módulo de carpeta** en lugar de un markdown parseado en
   runtime: el parseo histórico vive en `migrate_catalog.m` como herramienta
   one-off; la fuente de ejecución son las carpetas.
2. **Preservar el contrato 26-columnas** durante la migración (incluidos los
   nombres de estado mangled heredados) para no romper consumidores.
3. **Reutilizar `import_data`/`import_measurements`** para mediciones reales en
   vez de crear tablas nuevas.
4. **Idempotencia de ingesta en la capa de aplicación** (sin UNIQUE en la tabla
   heredada; no se altera el esquema en runtime).
5. **Calibración con backup primera-vez + traza en el propio archivo**: la
   historia del modelo viaja con el módulo, auditable sin BD.
6. **Planta sintética con el mismo contrato API que un medidor real**: el lazo
   se desarrolla, prueba y demuestra sin hardware, y se enchufa a lo real sin
   cambios de código.
7. **MAPE de energía diaria como métrica de demo del lazo** (la horaria
   confunde timing con forma y la dominan las horas standby).
