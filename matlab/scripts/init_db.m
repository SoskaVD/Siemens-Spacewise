%% init_db.m - Inicializar base de datos del simulador
% Script para crear la base de datos SQLite con el esquema del simulador
% de maquinaria industrial.
%
% Uso:
%   run('matlab/scripts/init_db.m')

% Agregar rutas necesarias
addpath('matlab/src');
addpath('matlab/config');

fprintf('=== Inicializando base de datos del simulador ===\n\n');

% Ruta de la base de datos
db_path = simulacion_params.DB_PATH;
fprintf('Ruta de la base de datos: %s\n', db_path);

% Verificar si ya existe
if exist(db_path, 'file')
    fprintf('⚠ La base de datos ya existe.\n');
    fprintf('¿Desea eliminarla y crear una nueva? (s/n): ');
    respuesta = input('', 's');
    if ~strcmpi(respuesta, 's')
        fprintf('Operación cancelada.\n');
        return;
    end
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
