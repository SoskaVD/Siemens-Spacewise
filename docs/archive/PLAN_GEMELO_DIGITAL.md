# PLAN — Gemelo Digital Energético SPACEWISE AI

**Implementación en MATLAB + persistencia SQLite**
**Proyecto:** SPACEWISE AI — Gemelo Digital Energético con IA y Siemens SENTRON para el Centro Espacial Nacional de Chile (CEN).
**Fecha:** 2026-08-03
**Referencia:** `docs/Grupo 3 Directrices Proyecto Siemens SPACE WISE AI.pdf` (modelo matemático, §10, §15), `docs/Bases y condiciones VF 2026 RFQ.pdf`.

---

## 1. Objetivo

Construir el motor del **gemelo digital energético** en MATLAB que:

1. Simula el comportamiento energético del CEN mediante un modelo **parametrizado y editable** (clima, ocupación, 6 subsistemas, escenarios de control).
2. Modela **dispositivos eléctricos individuales** (analizadores SENTRON, HVAC, iluminación, bombas, laboratorios, TI/UPS, auxiliares) y genera sus **mediciones horarias** (tensión, corriente, potencias, energía, THD, factor de potencia, estado).
3. Ejecuta **variaciones** (escenarios E0–E5 y barridos de parámetros).
4. **Persiste todo** (dispositivos, mediciones, ambiente, escenarios, simulaciones, resultados/KPIs, alarmas) en una base de datos **SQLite** en la carpeta `bd/`.

```
Siemens-Spacewise\
├── docs\                      → documentos del proyecto (este plan incluido)
├── bd\spacewise.db            → base SQLite generada por el gemelo
└── matlab\
    ├── config\spacewise_params.m   → parámetros editables (entrada única del modelo)
    ├── src\                         → librería del gemelo (dt_*)
    ├── scripts\                     → scripts de ejecución numerados 01..04
    └── tests\                       → pruebas unitarias MATLAB Test
```

---

## 2. Flujo de ejecución

```
spacewise_params.m (P) ──► dt_engine (perfiles anuales por subsistema)
        │
        ├──► dt_measurements (desagrega a dispositivo + magnitudes eléctricas)
        │        │
        ▼        ▼
   dt_db (SQLite) ──► bd/spacewise.db
        ▲        │
   dt_scenario ──┴──► escenarios E0-E5 + barridos (cada uno = 1 simulación)
```

Los **scripts** (`matlab/scripts/`) orquestan todo:

| Script | Acción |
|---|---|
| `init_db.m` | Crea `bd/spacewise.db` y el esquema completo (idempotente). |
| `seed_devices.m` | Registra el catálogo de dispositivos y tipos. |
| `run_simulations.m` | Ejecuta el gemelo para E0–E5 + barridos y guarda mediciones, ambiente, perfiles y resultados. |
| `query_reports.m` | Consulta la BD, compara escenarios, genera gráficos y exporta CSV. |

> Nota: los nombres de script **no pueden llevar prefijo numérico** (`01_…`); `run()`/el botón Ejecutar
> fallan con «Invalid text character». Se renombraron sin prefijo.

---

## 3. Modelo matemático (base del gemelo)

El motor implementa el modelo del documento de directrices (§10 y §15). Resumen operativo:

### 3.1 Línea base anual
```
E_base = Área × EUI = 12 000 m² × 240 kWh/m²·año = 2 880 000 kWh/año
E_subsistema = E_base × frac_subsistema        (HVAC 38%, LAB 20%, IT 18%, ILUM 10%, BOMB 6%, AUX 8%)
```

### 3.2 Perfiles horarios (1 año = 8 760 h)
Para cada subsistema se construye un perfil normalizado con dependencias físicas:

| Subsistema | Perfil (factores normalizados) |
|---|---|
| HVAC | `0.35 + 0.40·ocup + 0.20·|T_ext−T_conf|/10 + 0.05·Solar` |
| LAB | `0.25 + 0.75·actividadLAB` |
| IT | `0.92 + 0.08·ocup` (carga base 24/7) |
| ILUM | `0.20 + 0.75·ocup·(1 − 0.55·Solar)` |
| BOMB | `0.30 + 0.55·ocup + 0.15·actividadLAB` |
| AUX | `0.55 + 0.25·ocup + 0.20·actividadLAB` |

Los perfiles se **reescalan** para reproducir exactamente la energía anual objetivo:
```
P_subs(t) = perfil_subs(t) × E_subs / Σ perfil_subs
```

Clima/ocupación sintéticos (editable): temperatura con componente anual + diaria + ruido, humedad, radiación solar, ocupación según día de semana y hora, actividad de laboratorio.

### 3.3 Escenario de control
```
P_ctrl_subs(t) = P_base_subs(t) × (1 − ahorro_subs)     [E4/E5]
```

### 3.4 Gestión de demanda (E5)
- Se identifica el exceso sobre `PeakLímite` en horas punta (18–22 h).
- Las cargas flexibles desplazables (fracción de LAB y AUX) se mueven a valle (1–5 h).
- Resultado: reducción de demanda máxima sin perder energía.

### 3.5 Predicción de demanda (IA de referencia)
Regresión lineal multivariable (base del sistema predictivo):
```
P̂ = β0 + β1·T_ext + β2·Hum + β3·Solar + β4·ocup + β5·actividadLAB + β6·sin(2πh/24) + β7·cos(2πh/24)
```
División 70/15/15 (entrenamiento/validación/prueba). Métricas: RMSE, MAE, R².

### 3.6 Evaluación económica
CAPEX USD 310 000, OPEX USD 12 000/año, tarifa 0,15 USD/kWh, crecimiento 2,5%/año, degradación 0,5%/año, horizonte 10 años, tasa 10%. Calcula flujo de caja, **VAN, TIR y payback**.

### 3.7 Emisiones
```
CO2_base = E_base × FE          FE = 0,40 kgCO2/kWh
CO2_evitado = (E_base − E_ctrl) × FE
```

---

## 4. Generación de datos a nivel de dispositivo (mediciones)

### 4.1 Idea clave
Cada dispositivo pertenece a un subsistema y tiene una **potencia nominal** `P_nom`. Su consumo horario es una **fracción proporcional a su potencia nominal** respecto a la capacidad instalada de su subsistema:

```
share_dev = P_nom_dev / Σ P_nom  (solo dispositivos de consumo del mismo subsistema)

P_dev(t) = P_subs(t) × share_dev × factor_estado_dev(t)
```

`factor_estado_dev(t)` modela el **estado operativo** (ON=1, STANDBY≈0,15, OFF≈0,05) según el tipo de equipo, ocupación y actividad. Luego se **renormaliza** dentro del subsistema para que:
```
Σ P_dev(t) = P_subs(t)   (conservación exacta de energía por hora)
```

**Ejemplo concreto:** si `HVAC-01` (AHU, 120 kW) es el 27,3 % de la capacidad HVAC (440 kW), y la hora t el subsistema HVAC consume 300 kW con el equipo en ON, entonces `P_HVAC-01(t) ≈ 300 × 0,273 = 81,9 kW`. Si estuviera en STANDBY, baja a ≈12,3 kW y el resto se redistribuye entre los demás equipos del subsistema.

### 4.2 Magnitudes eléctricas derivadas (para cada hora)
| Magnitud | Fórmula / regla |
|---|---|
| Tensión `V` | Nominal del dispositivo (400 V trifásico o 230 V monofásico) con fluctuación ±2 % (`voltage_v`) |
| Corriente `I` | Trifásico: `I = P×1000/(√3·V·PF)` — Monofásico: `I = P×1000/(V·PF)` |
| Factor de potencia `PF` | Nominal del dispositivo + ruido pequeño, acotado [0,70, 0,99] |
| Potencia reactiva `Q` | `Q = P·tan(acos(PF))` (kvar) |
| Energía `E` | Consumida en el intervalo: `E(t) = P(t)·Δt_h` (kWh) |
| THD | Nominal + ruido, rango típico 0,5–8 % |
| Estado | `ON` / `STANDBY` / `OFF` según tipo y ocupación |

### 4.3 Tabla ambiental (mismo eje horario)
Temperatura, humedad, radiación solar, CO₂ (≈ 420 + 500·ocupación ppm), ocupación, día de semana y hora.

### 4.4 Medidores SENTRON (tipo `meter`)
No consumen energía (`P_nom = 0`). Su medición es la **agregación** del área que monitorean:
- `MET-01` PAC4200 en Tablero General → mide **la potencia total** del CEN.
- `MET-02` PAC3200 Tablero HVAC → mide el perfil **HVAC**.
- `MET-03` PAC3200 Tablero Laboratorios → mide el perfil **LAB**.
- `MET-04` PAC2200 Tablero Iluminación → mide el perfil **ILUM**.
- `MET-05` PAC2200 Tablero Auxiliares → mide el perfil **AUX**.

---

## 5. Catálogo de dispositivos (siembra inicial)

`subsystem`: subsistema al que pertenece. `criticidad`: CRITICA / ESENCIAL / FLEXIBLE / NO_CRITICA (jerarquía de control del documento).

| Código | Nombre | Tipo | Subsistema | Criticidad | Modelo | P_nom (kW) | Fases | PF | V (V) |
|---|---|---|---|---|---|---|---|---|---|
| MET-01 | Analizador Tablero General BT | meter | GENERAL | CRITICA | SENTRON PAC4200 | 0 | 3 | 0,95 | 400 |
| MET-02 | Analizador Tablero HVAC | meter | HVAC | CRITICA | SENTRON PAC3200 | 0 | 3 | 0,92 | 400 |
| MET-03 | Analizador Tablero Laboratorios | meter | LAB | CRITICA | SENTRON PAC3200 | 0 | 3 | 0,88 | 400 |
| MET-04 | Analizador Tablero Iluminación | meter | ILUM | ESENCIAL | SENTRON PAC2200 | 0 | 1 | 0,95 | 230 |
| MET-05 | Analizador Tablero Auxiliares | meter | AUX | ESENCIAL | SENTRON PAC2200 | 0 | 3 | 0,90 | 400 |
| HVAC-01 | AHU Principal Zona Este | hvac | HVAC | ESENCIAL | AHU + SINAMICS G120 | 120 | 3 | 0,90 | 400 |
| HVAC-02 | AHU Secundaria Zona Oeste | hvac | HVAC | FLEXIBLE | AHU | 80 | 3 | 0,90 | 400 |
| HVAC-03 | Climatización Precisión Sala Limpia | hvac | HVAC | CRITICA | Sala limpia | 150 | 3 | 0,92 | 400 |
| HVAC-04 | Fan-coil Oficinas Sur | hvac | HVAC | FLEXIBLE | FCU | 45 | 3 | 0,88 | 400 |
| HVAC-05 | Fan-coil Oficinas Norte | hvac | HVAC | FLEXIBLE | FCU | 45 | 3 | 0,88 | 400 |
| LIGHT-01 | Circuito Iluminación Interior LED | lighting | ILUM | FLEXIBLE | LED | 30 | 1 | 0,98 | 230 |
| LIGHT-02 | Circuito Iluminación Exterior | lighting | ILUM | NO_CRITICA | LED | 20 | 1 | 0,98 | 230 |
| LAB-01 | Laboratorio Electrónico 1 | lab | LAB | ESENCIAL | Bancos de carga | 60 | 3 | 0,85 | 400 |
| LAB-02 | Laboratorio Electrónico 2 | lab | LAB | ESENCIAL | Bancos de carga | 60 | 3 | 0,85 | 400 |
| LAB-03 | Banco de Pruebas Satelital | lab | LAB | CRITICA | Integración satelital | 90 | 3 | 0,85 | 400 |
| IT-01 | UPS Centro de Datos | it | IT | CRITICA | UPS | 100 | 3 | 0,95 | 400 |
| IT-02 | Servidores y Comunicaciones | it | IT | CRITICA | Racks | 70 | 3 | 0,95 | 400 |
| PUMP-01 | Bomba Primaria | pump | BOMB | ESENCIAL | SINAMICS G120 | 25 | 3 | 0,86 | 400 |
| PUMP-02 | Bomba Secundaria | pump | BOMB | ESENCIAL | SINAMICS G120 | 25 | 3 | 0,86 | 400 |
| FAN-01 | Ventilación Auxiliar | fan | BOMB | FLEXIBLE | SINAMICS G120 | 15 | 3 | 0,85 | 400 |
| AUX-01 | Ascensor y equipos auxiliares | aux | AUX | ESENCIAL | Elevador | 15 | 3 | 0,85 | 400 |
| AUX-02 | Cargas exteriores y seguridad | aux | AUX | NO_CRITICA | CCTV/alumbrado | 20 | 1 | 0,90 | 230 |

**Capacidad instalada por subsistema (solo consumo):** HVAC = 440 kW · LAB = 210 kW · IT = 170 kW · ILUM = 50 kW · BOMB = 65 kW · AUX = 35 kW.

**Reglas de estado por tipo (ejemplo del funcionamiento):**
- `it`: siempre `ON` (operación 24/7).
- `hvac`: `ON` si hay ocupación o en horas punta; `STANDBY` en la noche/fines de semana (carga 24/7 parcial).
- `lab`: `ON` en horas de actividad de laboratorio; `STANDBY` fuera de campaña.
- `lighting`: `ON` con ocupación (día) o en la noche para exterior; dimming en `STANDBY`.
- `pump`/`fan`/`aux`: `ON` con ocupación o actividad; `STANDBY` en vacíos.

---

## 6. Escenarios y variaciones

### 6.1 Escenarios de la Fase 6 del documento
| Escenario | Lógica | Efecto esperado |
|---|---|---|
| **E0** | Operación actual (base, sin control) | 0 % ahorro |
| **E1** | Solo medición (se registra, sin control) | 0 % ahorro (mismo que E0, distintos propósitos) |
| **E2** | Control horario (horarios fijos de operación) | Ahorro intermedio |
| **E3** | Sensores y regulación por ocupación | Ahorro intermedio |
| **E4** | IA predictiva (ahorros técnicos uniformes por subsistema) | Ahorro ≈ 21 % |
| **E5** | Gemelo digital + control integral (E4 + gestión de peak + predicción) | Ahorro ≈ 21 % y reducción de demanda ≥ 10 % |

Cada escenario se guarda en `scenarios` (con su `params_json` completo) y produce una simulación en `simulations` con sus resultados en `simulation_results`.

### 6.2 Barridos de parámetros (sensibilidad)
Variaciones automáticas sobre el escenario E5 cambiando un parámetro a la vez:

| Código | Parámetro | Valor |
|---|---|---|
| S01 | EUI (índice energético) | 200 kWh/m²·año |
| S02 | EUI (índice energético) | 280 kWh/m²·año |
| S03 | Ahorro técnico HVAC | 30 % |
| S04 | Tarifa eléctrica | 0,12 USD/kWh |
| S05 | Tarifa eléctrica | 0,18 USD/kWh |

Permiten construir curvas de sensibilidad de VAN/TIR/payback/ahorro (ver `query_reports.m`).

---

## 7. Esquema de la base SQLite (`bd/spacewise.db`)

| Tabla | Contenido |
|---|---|
| `device_types` | Catálogo de tipos: meter, hvac, lighting, pump, fan, lab, it, aux |
| `devices` | Dispositivos con código, tipo, subsistema, criticidad, modelo, P_nom, PF, tensión, fases, ubicación, metadata JSON |
| `scenarios` | Escenario/variación: código (E0…E5, S01…), nombre, descripción, `params_json` |
| `simulations` | Corrida: escenario FK, versión del motor, inicio/fin, estado, log |
| `environment` | Serie horaria ambiental por simulación: T, humedad, CO₂, ocupación, solar, hora, día |
| `measurements` | Mediciones horarias por dispositivo y simulación: V, I, P, Q, PF, energía, THD, estado |
| `subsystem_profiles` | Perfil horario anual por subsistema: P_base, P_ctrl (salida del gemelo) |
| `simulation_results` | KPIs por subsistema y TOTAL: energía base/ctrl, ahorro, peak, CO₂, RMSE/MAE/R², payback, VAN, TIR |
| `events` | Alarmas/anomalías: sobrecarga, calidad eléctrica, desviación > 15 % |

Índices sobre `simulation_id`, `device_id` y `ts` para consultas eficientes.

---

## 8. Pasos para completar el plan (checklist)

- [x] **P0.** Documento de plan (este archivo).
- [x] **P1.** Estructura de carpetas (`bd/`, `matlab/config`, `matlab/src`, `matlab/scripts`, `matlab/tests`).
- [x] **P2.** `config/spacewise_params.m` — parámetros editables (única fuente de entrada).
- [x] **P3.** `src/dt_db.m` — capa SQLite: abrir/crear BD, crear esquema, insertar en bloque (`sqlwrite`), consultas, cerrar.
- [x] **P4.** `src/dt_device.m` — catálogo de dispositivos (tabla de la §5) y tipos.
- [x] **P5.** `src/dt_engine.m` — motor del gemelo (perfiles anuales, clima, ocupación, control, peak, predicción, economía). Validar `E_base ≈ 2 880 000 kWh`.
- [x] **P6.** `src/dt_analysis.m` — KPIs y métricas (RMSE, MAE, R², VAN, TIR, payback, CO₂).
- [x] **P7.** `src/dt_measurements.m` — desagregación a dispositivo y magnitudes eléctricas + tabla ambiental + eventos.
- [x] **P8.** `src/dt_scenario.m` — definición de escenarios E0–E5 y barridos S01–S05.
- [x] **P9.** `src/dt_plot.m` — gráficos (semana base vs control, barras por subsistema, predicción, flujo de caja) y export CSV.
- [x] **P10.** Scripts `init_db.m`, `seed_devices.m`, `run_simulations.m`, `query_reports.m` (sin prefijo numérico).
- [x] **P11.** Tests MATLAB (`tests/`): `test_dt_engine` (6), `test_dt_db` (4), `test_dt_measurements` (3) — 13/13 PASS con `runtests`.
- [x] **P12.** Ejecutar la simulación, poblar `bd/spacewise.db` y verificar resultados (tablas pobladas, KPIs coherentes, gráficos/CSV generados).

---

## 9. Cómo añadir más dispositivos, mediciones u opciones

### 9.1 Añadir un dispositivo nuevo
Agregar una fila al catálogo en `src/dt_device.m` (función `deviceCatalog`) o insertarla directamente con `dt_db.insertDevices`. Campos requeridos: `device_code`, `name`, `type_code`, `subsystem`, `criticality`, `rated_power_kw`, `phases`, `voltage_v`. El resto es opcional.

Ejemplo:
```matlab
dev = struct('device_code','HVAC-06','name','Chiller Torre Enfriamiento', ...
            'type_code','hvac','subsystem','HVAC','criticality','FLEXIBLE', ...
            'rated_power_kw',70,'phases',3,'voltage_v',400,'model','Chiller','pf_nominal',0.92);
```

El reparto automático por potencia nominal (`share = P_nom/ΣP_nom_subsistema`) redistribuye el consumo del subsistema, por lo que **no hay que tocar el motor**.

### 9.2 Añadir un nuevo tipo de dispositivo
Registrarlo en `device_types` y, si corresponde, definir su regla de estado en `dt_measurements.m` (función `deviceState`).

### 9.3 Añadir un escenario o variación
En `src/dt_scenario.m`, agregar una entrada al array de escenarios con: `scenario_code`, `name`, `description`, y un `override` de parámetros (struct con los campos de `P` que cambian). Ejemplo: variar solo el ahorro de iluminación:
```matlab
sc = struct('scenario_code','S06','name','Ahorro iluminación 50%', ...
            'description','Sensibilidad: ahorro ILUM 0.50', ...
            'override',struct('ahorroILUM',0.50));
```

### 9.4 Añadir un parámetro editable
Agregar el campo a `config/spacewise_params.m`. Si el motor debe usarlo, referéncielo en `dt_engine.m` (o `dt_measurements.m`) y en `dt_analysis.m`. El `params_json` lo guarda automáticamente en `scenarios`.

### 9.5 Cambiar la resolución o el horizonte temporal
En `spacewise_params.m`: `dt_h` (hora por intervalo, 1 h por defecto), `dias_simulacion` (365 por defecto) y `measurement_days` (ventana de mediciones por dispositivo, 365 por defecto). Con `measurement_days = 28` se replica la campaña de medición de 4 semanas del documento (Fase 2).

---

## 10. KPIs verificables

| KPI | Fórmula | Meta |
|---|---|---|
| Ahorro total | `(E_base − E_ctrl)/E_base` | 20–30 % (E4/E5) |
| Reducción de peak | `(P_peak_base − P_peak_ctrl)/P_peak_base` | ≥ 10 % (E5) |
| Error de predicción | `RMSE/Peak` | ≤ 10 % |
| Línea base | `E_base = Área·EUI` | 2 880 MWh/año |
| CO₂ evitado | `(E_base − E_ctrl)·FE` | ≥ 200 t/año |
| Payback | `CAPEX / flujo neto` | ≤ 5 años |
| VAN/TIR | flujo descontado | VAN > 0, TIR > 10 % |

---

## 11. Entorno y limitaciones

- MATLAB R2026a + **Database Toolbox** (función `sqlite`, JDBC). La conexión requiere JVM.
- Rendimiento medido: inserción de 52 560 filas ≈ 0,4 s (`sqlwrite`), por lo que el volumen anual completo es viable.
- Los datos son **simulados** (gemelo). Reemplazarlos por mediciones reales de SENTRON powermanager es transparente: solo cambia el origen de `P_subs(t)`.
- El modelo usa `randn`/`rand` con semilla fija (reproducibilidad).
