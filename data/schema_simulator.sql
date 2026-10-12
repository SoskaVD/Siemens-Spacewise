-- Esquema SQLite para Simulador de Maquinaria Industrial
-- Basado en dt_db.m (gemelo anterior) pero adaptado para 110 máquinas individuales
-- Fecha: Octubre 2026

-- ============================================================================
-- TABLA: machines
-- Catálogo de máquinas industriales (110 equipos desde CATALOGO_EQUIPOS.md)
-- ============================================================================
CREATE TABLE IF NOT EXISTS machines (
    machine_id INTEGER PRIMARY KEY,
    machine_code TEXT UNIQUE NOT NULL,          -- ej: HVAC-001, COMP-015, MOT-042
    name TEXT NOT NULL,                          -- ej: Chiller Centrífugo de Alta Eficiencia
    category TEXT NOT NULL,                      -- ej: HVAC, Compresores, Motores, Bombas, etc.
    manufacturer TEXT,                           -- ej: Trane, Carrier, Daikin
    model TEXT,                                  -- ej: CenTraVac CVHE, AquaForce 30KAV
    
    -- Especificaciones eléctricas
    rated_power_kw REAL NOT NULL,                -- Potencia nominal (kW)
    voltage_v REAL NOT NULL,                     -- Voltaje (V)
    current_a REAL NOT NULL,                     -- Corriente nominal (A)
    power_factor REAL NOT NULL,                  -- Factor de potencia nominal (0-1)
    phases INTEGER NOT NULL,                     -- Fases (1 o 3)
    thd_pct REAL NOT NULL,                       -- THD esperado (%)
    
    -- Perfil de consumo
    hours_per_day REAL NOT NULL,                 -- Horas de operación por día (0-24)
    days_per_week REAL NOT NULL,                 -- Días de operación por semana (0-7)
    load_factor REAL NOT NULL,                   -- Factor de carga promedio (0-1)
    seasonal_variability TEXT,                   -- ej: Alta, Moderada, Baja
    work_cycles_json TEXT,                       -- JSON con ciclos de trabajo y fracciones
    
    -- Comportamiento dinámico
    startup_time_s REAL,                         -- Tiempo de arranque (segundos)
    startup_multiplier REAL DEFAULT 1.0,         -- Consumo durante arranque (múltiplo de nominal)
    standby_pct REAL DEFAULT 0.0,                -- Consumo en standby (% de nominal)
    flexibility INTEGER DEFAULT 0,               -- 0=no, 1=sí (puede shiftar carga)
    
    -- Contexto operativo
    application TEXT,                            -- Aplicación típica
    criticality TEXT NOT NULL,                   -- CRITICA, ESENCIAL, FLEXIBLE, NO_CRITICA
    dependencies TEXT,                           -- Dependencias de otros equipos
    environmental_notes TEXT,                    -- Condiciones ambientales que afectan consumo
    
    -- Metadata
    active INTEGER DEFAULT 1,                    -- 1=activo, 0=inactivo
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT                           -- Campos adicionales futuros
);

CREATE INDEX IF NOT EXISTS idx_machines_code ON machines(machine_code);
CREATE INDEX IF NOT EXISTS idx_machines_category ON machines(category);
CREATE INDEX IF NOT EXISTS idx_machines_criticality ON machines(criticality);

-- ============================================================================
-- TABLA: simulations
-- Registro de ejecuciones de simulación
-- ============================================================================
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id INTEGER PRIMARY KEY,
    simulation_code TEXT UNIQUE NOT NULL,        -- ej: SIM-2026-001, SIM-BASELINE
    name TEXT NOT NULL,                          -- Nombre descriptivo
    description TEXT,                            -- Descripción de la simulación
    engine_version TEXT,                         -- Versión del motor (ej: 1.0.0)
    start_time TEXT,                             -- Timestamp de inicio
    end_time TEXT,                               -- Timestamp de fin
    status TEXT NOT NULL,                        -- PENDING, RUNNING, COMPLETED, FAILED
    total_machines INTEGER DEFAULT 0,            -- Número de máquinas simuladas
    total_hours INTEGER DEFAULT 8760,            -- Horas simuladas (default 1 año)
    random_seed INTEGER,                         -- Seed para reproducibilidad
    params_json TEXT,                            -- Parámetros adicionales (JSON)
    log TEXT,                                    -- Log de ejecución
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_simulations_status ON simulations(status);
CREATE INDEX IF NOT EXISTS idx_simulations_created ON simulations(created_at);

-- ============================================================================
-- TABLA: machine_measurements
-- Perfiles horarios de consumo por máquina (8760 horas por máquina)
-- Esta es la tabla más grande: 110 máquinas × 8760 horas = ~963,600 filas
-- ============================================================================
CREATE TABLE IF NOT EXISTS machine_measurements (
    measurement_id INTEGER PRIMARY KEY,
    simulation_id INTEGER NOT NULL REFERENCES simulations(simulation_id),
    machine_id INTEGER NOT NULL REFERENCES machines(machine_id),
    ts TEXT NOT NULL,                            -- Timestamp (YYYY-MM-DD HH:MM:SS)
    hour_index INTEGER NOT NULL,                 -- Índice 0-8759
    
    -- Mediciones eléctricas
    active_power_kw REAL NOT NULL,               -- Potencia activa (kW)
    energy_kwh REAL NOT NULL,                    -- Energía consumida en esa hora (kWh)
    load_factor REAL NOT NULL,                   -- Factor de carga en esa hora (0-1)
    power_factor REAL,                           -- PF en esa hora (si varía)
    current_a REAL,                              -- Corriente en esa hora (A)
    
    -- Estado operativo
    operation_state TEXT,                        -- RUNNING, PARTIAL, STANDBY, STARTUP, OFF
    cycle_phase TEXT,                            -- ej: FULL_LOAD, PARTIAL_LOAD, STANDBY
    
    -- Calidad de energía (opcional)
    thd_pct REAL,                                -- THD en esa hora (%)
    voltage_v REAL,                              -- Voltaje en esa hora (V)
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Índices críticos para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_meas_sim ON machine_measurements(simulation_id);
CREATE INDEX IF NOT EXISTS idx_meas_machine ON machine_measurements(machine_id);
CREATE INDEX IF NOT EXISTS idx_meas_sim_machine ON machine_measurements(simulation_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_meas_ts ON machine_measurements(ts);
CREATE INDEX IF NOT EXISTS idx_meas_sim_ts ON machine_measurements(simulation_id, ts);

-- ============================================================================
-- TABLA: hourly_totals
-- Totales horarios agregados (suma de todas las máquinas por hora)
-- 8760 filas por simulación
-- ============================================================================
CREATE TABLE IF NOT EXISTS hourly_totals (
    total_id INTEGER PRIMARY KEY,
    simulation_id INTEGER NOT NULL REFERENCES simulations(simulation_id),
    ts TEXT NOT NULL,                            -- Timestamp
    hour_index INTEGER NOT NULL,                 -- Índice 0-8759
    
    -- Totales de potencia
    total_power_kw REAL NOT NULL,                -- Suma de potencia activa (kW)
    total_energy_kwh REAL NOT NULL,              -- Suma de energía (kWh)
    
    -- Desglose por categoría
    hvac_power_kw REAL DEFAULT 0,
    compressors_power_kw REAL DEFAULT 0,
    motors_power_kw REAL DEFAULT 0,
    pumps_power_kw REAL DEFAULT 0,
    lighting_power_kw REAL DEFAULT 0,
    lab_power_kw REAL DEFAULT 0,
    manufacturing_power_kw REAL DEFAULT 0,
    it_power_kw REAL DEFAULT 0,
    auxiliary_power_kw REAL DEFAULT 0,
    
    -- Estadísticas
    machine_count INTEGER,                       -- Número de máquinas activas en esa hora
    avg_load_factor REAL,                        -- Factor de carga promedio
    peak_power_kw REAL,                          -- Máquina con mayor consumo en esa hora
    peak_machine_id INTEGER REFERENCES machines(machine_id),
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_totals_sim ON hourly_totals(simulation_id);
CREATE INDEX IF NOT EXISTS idx_totals_ts ON hourly_totals(ts);

-- ============================================================================
-- TABLA: simulation_results
-- KPIs y resúmenes por simulación (1 fila por simulación)
-- ============================================================================
CREATE TABLE IF NOT EXISTS simulation_results (
    result_id INTEGER PRIMARY KEY,
    simulation_id INTEGER NOT NULL REFERENCES simulations(simulation_id),
    
    -- Totales anuales
    total_energy_kwh REAL NOT NULL,              -- Energía total consumida (kWh)
    total_cost_usd REAL,                         -- Costo total (USD, si se define tarifa)
    avg_power_kw REAL NOT NULL,                  -- Potencia promedio (kW)
    peak_power_kw REAL NOT NULL,                 -- Potencia pico (kW)
    peak_ts TEXT,                                -- Timestamp del pico
    
    -- Desglose por categoría
    energy_by_category_json TEXT,                -- JSON con energía por categoría
    top_machines_json TEXT,                      -- JSON con top 10 máquinas por consumo
    
    -- Análisis temporal
    monthly_energy_json TEXT,                    -- JSON con energía por mes
    weekly_pattern_json TEXT,                    -- JSON con patrón semanal promedio
    daily_pattern_json TEXT,                     -- JSON con patrón diario promedio
    
    -- Análisis por criticidad
    energy_by_criticality_json TEXT,             -- JSON con energía por nivel de criticidad
    
    -- Estadísticas de calidad
    avg_power_factor REAL,                       -- Factor de potencia promedio
    avg_thd_pct REAL,                            -- THD promedio
    flexibility_potential_kwh REAL,              -- Energía que podría shiftarse (máquinas flexibles)
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_results_sim ON simulation_results(simulation_id);

-- ============================================================================
-- TABLA: machine_results
-- KPIs por máquina individual (1 fila por máquina por simulación)
-- ============================================================================
CREATE TABLE IF NOT EXISTS machine_results (
    machine_result_id INTEGER PRIMARY KEY,
    simulation_id INTEGER NOT NULL REFERENCES simulations(simulation_id),
    machine_id INTEGER NOT NULL REFERENCES machines(machine_id),
    
    -- Totales anuales por máquina
    total_energy_kwh REAL NOT NULL,              -- Energía total consumida (kWh)
    total_cost_usd REAL,                         -- Costo total (USD)
    avg_power_kw REAL NOT NULL,                  -- Potencia promedio (kW)
    peak_power_kw REAL NOT NULL,                 -- Potencia pico (kW)
    peak_ts TEXT,                                -- Timestamp del pico
    
    -- Estadísticas operativas
    operating_hours REAL,                        -- Horas totales de operación
    avg_load_factor REAL,                        -- Factor de carga promedio
    capacity_factor REAL,                        -- Factor de capacidad (energía real / máxima posible)
    
    -- Desglose temporal
    monthly_energy_json TEXT,                    -- JSON con energía por mes
    hourly_pattern_json TEXT,                    -- JSON con patrón horario promedio
    
    -- Contribución al total
    energy_share_pct REAL,                       -- % del consumo total de la simulación
    rank_by_energy INTEGER,                      -- Ranking por consumo (1 = mayor consumidor)
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mach_results_sim ON machine_results(simulation_id);
CREATE INDEX IF NOT EXISTS idx_mach_results_machine ON machine_results(machine_id);

-- ============================================================================
-- TABLA: import_data
-- Datos reales importados para comparación con simulación
-- ============================================================================
CREATE TABLE IF NOT EXISTS import_data (
    import_id INTEGER PRIMARY KEY,
    import_code TEXT UNIQUE NOT NULL,            -- ej: IMPORT-2026-Q1
    name TEXT NOT NULL,                          -- Nombre descriptivo
    source_file TEXT,                            -- Archivo origen (CSV/Excel)
    import_date TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    start_date TEXT,                             -- Rango temporal de los datos
    end_date TEXT,
    total_records INTEGER,                       -- Número de registros importados
    metadata_json TEXT                           -- Metadata adicional
);

CREATE INDEX IF NOT EXISTS idx_import_code ON import_data(import_code);

-- ============================================================================
-- TABLA: import_measurements
-- Mediciones reales importadas (para comparación con simulación)
-- ============================================================================
CREATE TABLE IF NOT EXISTS import_measurements (
    import_meas_id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES import_data(import_id),
    machine_code TEXT,                           -- Código de máquina (puede ser NULL si es total)
    ts TEXT NOT NULL,                            -- Timestamp
    active_power_kw REAL,                        -- Potencia activa medida (kW)
    energy_kwh REAL,                             -- Energía medida (kWh)
    current_a REAL,                              -- Corriente medida (A)
    power_factor REAL,                           -- Factor de potencia medido
    voltage_v REAL,                              -- Voltaje medido (V)
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_import_meas_import ON import_measurements(import_id);
CREATE INDEX IF NOT EXISTS idx_import_meas_ts ON import_measurements(ts);
