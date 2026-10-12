%% init_db.m - Inicializar base de datos del simulador
% Script para crear la base de datos SQLite con el esquema del simulador
% de maquinaria industrial.
%
% Uso:
%   run('matlab/scripts/init_db.m')

% Get the root directory (2 levels up from this script) and cd to it
% so that relative paths like 'data/spacewise.db' resolve correctly.
scriptDir = fileparts(mfilename('fullpath'));
rootDir = fullfile(scriptDir, '..', '..');
cd(rootDir);
addpath(fullfile(rootDir, 'matlab', 'src'));
addpath(fullfile(rootDir, 'matlab', 'config'));

fprintf('=== Inicializando base de datos del simulador ===\n\n');

% Ruta de la base de datos
db_path = simulacion_params.DB_PATH;
fprintf('Ruta de la base de datos: %s\n', db_path);

% Verificar si ya existe
if exist(db_path, 'file')
    fprintf('⚠ La base de datos ya existe. Recreando...\n');
    delete(db_path);
end

% Inicializar base de datos
fprintf('\nCreando base de datos...\n');
try
    conn = sim_db.init(db_path);
    sim_db.close(conn);
    fprintf('✓ Base de datos creada exitosamente en: %s\n', db_path);
catch ME
    fprintf('✗ Error al crear la base de datos: %s\n', ME.message);
    rethrow(ME);
end

fprintf('\n=== Inicialización completada ===\n');
