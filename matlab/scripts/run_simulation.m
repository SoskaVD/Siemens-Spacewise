%% run_simulation.m - Ejecutar simulación completa
% Script para ejecutar una simulación completa del sistema de maquinaria
% industrial. Genera perfiles horarios para 110 máquinas durante 8760 horas.
%
% Uso:
%   run('matlab/scripts/run_simulation.m')

% Get the root directory (2 levels up from this script) and cd to it
% so that relative paths like 'data/spacewise.db' resolve correctly.
scriptDir = fileparts(mfilename('fullpath'));
rootDir = fullfile(scriptDir, '..', '..');
cd(rootDir);
addpath(fullfile(rootDir, 'matlab', 'src'));
addpath(fullfile(rootDir, 'matlab', 'config'));

fprintf('=== Simulador de Maquinaria Industrial ===\n');
fprintf('Motor versión: %s\n', simulacion_params.ENGINE_VERSION);
fprintf('Horas por año: %d\n', simulacion_params.HOURS_PER_YEAR);
fprintf('Seed por defecto: %d\n\n', simulacion_params.DEFAULT_SEED);

% Parámetros de simulación
sim_code = 'SIM-BASELINE-001';
sim_name = 'Baseline Simulation - All Machines';
sim_desc = 'Full year simulation of 110 industrial machines with default parameters';
seed = simulacion_params.DEFAULT_SEED;

% Verificar que existe la base de datos
if ~exist(simulacion_params.DB_PATH, 'file')
    fprintf('⚠ Base de datos no encontrada. Inicializando...\n');
    conn = sim_db.init(simulacion_params.DB_PATH);
    sim_db.close(conn);
    fprintf('✓ Base de datos inicializada\n\n');
end

% Ejecutar simulación
fprintf('Ejecutando simulación...\n');
fprintf('  Código: %s\n', sim_code);
fprintf('  Nombre: %s\n', sim_name);
fprintf('  Descripción: %s\n', sim_desc);
fprintf('  Seed: %d\n\n', seed);

try
    [sim_id, summary] = sim_engine.run(sim_code, sim_name, sim_desc, seed);
    
    fprintf('\n=== Resumen de la simulación ===\n');
    fprintf('Simulation ID: %d\n', summary.simulation_id);
    fprintf('Status: %s\n', summary.status);
    fprintf('Total machines: %d\n', summary.total_machines);
    fprintf('Total hours: %d\n', summary.total_hours);
    fprintf('Total energy: %.2f kWh\n', summary.total_energy_kwh);
    fprintf('Average power: %.2f kW\n', summary.avg_power_kw);
    fprintf('Peak power: %.2f kW\n', summary.peak_power_kw);
    fprintf('Peak timestamp: %s\n', summary.peak_ts);
    fprintf('Elapsed time: %.2f seconds\n', summary.elapsed_seconds);
    
    fprintf('\n✓ Simulación completada exitosamente\n');
    
catch ME
    fprintf('\n✗ Error durante la simulación:\n');
    fprintf('  %s\n', ME.message);
    if ~isempty(ME.stack)
        fprintf('  en %s (línea %d)\n', ME.stack(1).name, ME.stack(1).line);
    end
    rethrow(ME);
end

fprintf('\n=== Simulación finalizada ===\n');
