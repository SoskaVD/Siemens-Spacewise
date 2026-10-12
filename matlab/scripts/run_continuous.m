%% run_continuous.m - Ejecutar simulación continua en tiempo real
% Script para ejecutar una simulación continua que genera datos
% en intervalos de tiempo reales (1-10 segundos por hora simulada).
%
% Uso:
%   run('matlab/scripts/run_continuous.m')

% Get the root directory (2 levels up from this script) and cd to it
% so that relative paths like 'data/spacewise.db' resolve correctly.
scriptDir = fileparts(mfilename('fullpath'));
rootDir = fullfile(scriptDir, '..', '..');
cd(rootDir);
rootDir = pwd;  % Canonicalize path after cd
addpath(fullfile(rootDir, 'matlab', 'src'));
addpath(fullfile(rootDir, 'matlab', 'config'));

fprintf('=== Starting Continuous Real-Time Simulation ===\n\n');

% Parámetros de simulación
sim_code = 'SIM-CONTINUOUS-001';
sim_name = 'Continuous Real-Time Simulation';
sim_desc = 'Real-time simulation generating data every few seconds';
seed = simulacion_params.DEFAULT_SEED;

% Configuración de intervalo
interval_seconds = 2;  % Segundos entre cada actualización (configurable: 1, 2, 5, 10)
max_hours = inf;       % Infinite loop (Ctrl+C to stop)

fprintf('Configuration:\n');
fprintf('  Interval: %d seconds between updates\n', interval_seconds);
fprintf('  Mode: Continuous (press Ctrl+C to stop)\n\n');

% Verificar que existe la base de datos
if ~exist(simulacion_params.DB_PATH, 'file')
    fprintf('⚠ Database not found. Initializing...\n');
    conn = sim_db.init(simulacion_params.DB_PATH);
    sim_db.close(conn);
    fprintf('✓ Database initialized\n\n');
end

fprintf('Starting continuous simulation...\n');
fprintf('Press Ctrl+C to stop gracefully\n\n');

try
    sim_engine.runContinuous(sim_code, sim_name, sim_desc, seed, interval_seconds, max_hours);
catch ME
    if strcmp(ME.identifier, 'MATLAB:CTRL_C')
        fprintf('\n\n✓ Continuous simulation stopped by user\n');
    else
        fprintf('\n✗ Error during continuous simulation:\n');
        fprintf('  %s\n', ME.message);
        if ~isempty(ME.stack)
            fprintf('  at %s (line %d)\n', ME.stack(1).name, ME.stack(1).line);
        end
        rethrow(ME);
    end
end

fprintf('\n=== Continuous simulation finished ===\n');
