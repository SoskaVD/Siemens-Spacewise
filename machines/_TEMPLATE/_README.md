# Plantilla de módulo de máquina (`_TEMPLATE`)

Cada carpeta dentro de `machines/` es un "mini-gemelo": una máquina del
catálogo. El cargador (`sim_catalog.load()`) descubre automáticamente las
carpetas de módulo al escanear `machines/`:

- **Añadir máquina** → crear `machines/<CODE>/machine.json` (copia esta
  plantilla y ajusta los valores).
- **Quitar máquina** → eliminar su carpeta `machines/<CODE>/`.
- Las carpetas cuyo nombre empieza con `_` o `.` se ignoran (por eso esta
  plantilla vive en `_TEMPLATE/` y no se carga como máquina).

## Convenciones

- `<CODE>` debe coincidir con el contrato del backend: `^[A-Z]{2,10}-\d{1,5}$`
  (p. ej. `HVAC-001`, `BOMB-012`, `TI-005`).
- `machine_id` **no** se guarda en el JSON: `sim_catalog.load()` lo asigna
  secuencialmente (1..N) ordenando las máquinas por `machine_code` ascendente.
- `active` es opcional; si se omite, el cargador lo toma como `1`.
- `work_cycles` es un objeto JSON de fracciones de estado (no un string).
  El cargador lo re-serializa a la columna string `work_cycles_json` del
  contrato de 26 columnas.
- Los errores de validación se reportan como `SIM:ModuleInvalid` nombrando la
  carpeta y el archivo ofensivos; un directorio `machines/` inexistente o sin
  módulos produce `SIM:CatalogNotFound`.

## Campos de `machine.json`

Todos los campos son obligatorios salvo `active`. JSON no admite comentarios;
esta tabla es la documentación de cada campo.

| Campo | Tipo | Rango / dominio | Descripción |
|-------|------|-----------------|-------------|
| `machine_code` | string | `^[A-Z]{2,10}-\d{1,5}$`, único en `machines/` | Código identificador (columna `machine_code`) |
| `name` | string (no vacío) | — | Nombre comercial del equipo |
| `category` | string | `HVAC`, `Compresores`, `Motores`, `Bombas`, `Iluminacion`, `Laboratorios`, `Manufactura`, `TI`, `Auxiliares` | Categoría energética (columna `category`) |
| `manufacturer` | string (puede ser `""`) | — | Fabricante |
| `model` | string (puede ser `""`) | — | Modelo |
| `rated_power_kw` | number | > 0 | Potencia nominal en kW |
| `voltage_v` | number | > 0 | Tensión de alimentación en V |
| `current_a` | number | ≥ 0 | Corriente nominal en A |
| `power_factor` | number | (0, 1] | Factor de potencia nominal |
| `phases` | integer | 1, 2 o 3 | Número de fases |
| `thd_pct` | number | ≥ 0 | Distorsión armónica total esperada (%) |
| `hours_per_day` | number | [0, 24] | Horas de operación por día |
| `days_per_week` | number | [0, 7] | Días de operación por semana |
| `load_factor` | number | [0, 1] | Factor de carga promedio |
| `seasonal_variability` | string | `Alta`, `Moderada` o `Baja` | Variabilidad estacional del consumo |
| `work_cycles` | objeto JSON | valores en [0, 1], suma ≈ 1 | Fracción de tiempo por estado operativo (p. ej. `{"RUNNING":0.6,"STANDBY":0.4}`) |
| `startup_time_s` | number | ≥ 0 | Duración del arranque en segundos |
| `startup_multiplier` | number | ≥ 1 | Pico de arranque como múltiplo de la potencia nominal |
| `standby_pct` | number | [0, 100] | Consumo en standby (% de la nominal) |
| `flexibility` | integer | 0 o 1 | 1 = consumo desplazable en el tiempo |
| `application` | string (puede ser `""`) | — | Aplicación típica |
| `criticality` | string | `CRITICA`, `ESENCIAL`, `FLEXIBLE`, `NO_CRITICA` | Nivel de criticidad operativa |
| `dependencies` | string (puede ser `""`) | — | Dependencias de otros equipos |
| `environmental_notes` | string (puede ser `""`) | — | Condiciones ambientales relevantes |
| `active` | integer (opcional) | 0 o 1 | 0 excluye la máquina de nuevas simulaciones; defecto: 1 |

## Cómo crear una máquina nueva

1. `cp -r machines/_TEMPLATE machines/MICODIGO` (ajusta el nombre de carpeta).
2. Edita `machines/MICODIGO/machine.json` con los datos reales del equipo.
3. Verifica: `matlab -batch "addpath('matlab/src'); addpath('matlab/config'); disp(height(sim_catalog.load()))"`
   — el conteo debe subir en uno y no debe haber errores `SIM:ModuleInvalid`.

## Migración desde el catálogo markdown histórico

`docs/CATALOGO_EQUIPOS.md` ya **no** se parsea en tiempo de carga. Los 110
módulos actuales se generaron una única vez con:

```
matlab -batch "run('matlab/scripts/migrate_catalog.m')"
```

El markdown queda solo como referencia histórica de los datos.
