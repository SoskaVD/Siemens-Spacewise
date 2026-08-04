% 01_init_db.m - Inicializa la base SQLite bd/spacewise.db con el esquema completo.
% Uso: abrir desde matlab/scripts y ejecutar, o run('matlab/scripts/01_init_db.m').

projectRoot = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot, 'src'), fullfile(projectRoot, 'config'));

repoRoot = fileparts(projectRoot);
dbPath = fullfile(repoRoot, 'bd', 'spacewise.db');

if ~exist(fullfile(repoRoot, 'bd'), 'dir')
    mkdir(fullfile(repoRoot, 'bd'));
end

conn = dt_db.init(dbPath);
dt_db.close(conn);

fprintf('Base inicializada: %s\n', dbPath);
fprintf('Esquema creado: device_types, devices, scenarios, simulations,\n');
fprintf('  environment, measurements, subsystem_profiles, simulation_results, events\n');
