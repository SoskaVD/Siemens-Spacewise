%% load_catalog.m - Cargar catálogo de máquinas
% Script para cargar el catálogo de máquinas industriales desde
% docs/CATALOGO_EQUIPOS.md y mostrar información básica.
%
% Uso:
%   run('matlab/scripts/load_catalog.m')

% Get the root directory (2 levels up from this script) and cd to it
% so that relative paths like 'data/spacewise.db' resolve correctly.
scriptDir = fileparts(mfilename('fullpath'));
rootDir = fullfile(scriptDir, '..', '..');
cd(rootDir);
addpath(fullfile(rootDir, 'matlab', 'src'));
addpath(fullfile(rootDir, 'matlab', 'config'));

fprintf('=== Cargando catálogo de máquinas ===\n\n');

% Cargar catálogo
fprintf('Leyendo catálogo desde: %s\n', simulacion_params.CATALOG_PATH);
try
    machines = sim_catalog.load();
    fprintf('✓ Catálogo cargado exitosamente\n');
catch ME
    fprintf('✗ Error al cargar el catálogo: %s\n', ME.message);
    rethrow(ME);
end

% Mostrar estadísticas básicas
fprintf('\n--- Estadísticas del catálogo ---\n');
fprintf('Total de máquinas: %d\n', height(machines));
fprintf('\nMáquinas por categoría:\n');

categories = unique(machines.category);
for i = 1:numel(categories)
    cat = categories{i};
    count = sum(strcmp(machines.category, cat));
    fprintf('  %-20s: %3d máquinas\n', cat, count);
end

% Mostrar máquinas con mayor potencia
fprintf('\n--- Top 10 máquinas por potencia nominal ---\n');
[~, idx] = sort(machines.rated_power_kw, 'descend');
top10 = idx(1:min(10, height(machines)));

fprintf('%-4s %-12s %-40s %8s kW\n', 'ID', 'Code', 'Name', 'Power');
fprintf('%s\n', repmat('-', 1, 70));
for i = 1:numel(top10)
    row = top10(i);
    fprintf('%-4d %-12s %-40s %8.1f kW\n', ...
        machines.machine_id(row), ...
        machines.machine_code{row}, ...
        machines.name{row}, ...
        machines.rated_power_kw(row));
end

% Mostrar distribución de criticidad
fprintf('\n--- Distribución por criticidad ---\n');
criticalities = unique(machines.criticality);
for i = 1:numel(criticalities)
    crit = criticalities{i};
    count = sum(strcmp(machines.criticality, crit));
    fprintf('  %-15s: %3d máquinas\n', crit, count);
end

fprintf('\n=== Carga completada ===\n');
