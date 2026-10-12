%% export_results.m - Exportar resultados de simulación
% Script para exportar los resultados de una simulación a diferentes formatos:
% CSV, Excel y reporte de texto.
%
% Uso:
%   run('matlab/scripts/export_results.m')

% Get the root directory (2 levels up from this script) and cd to it
% so that relative paths like 'data/spacewise.db' resolve correctly.
scriptDir = fileparts(mfilename('fullpath'));
rootDir = fullfile(scriptDir, '..', '..');
cd(rootDir);
rootDir = pwd;  % Canonicalize path after cd
addpath(fullfile(rootDir, 'matlab', 'src'));
addpath(fullfile(rootDir, 'matlab', 'config'));

fprintf('=== Exportación de resultados ===\n\n');

% Parámetros
sim_id = 1;  % ID de la simulación a exportar
output_dir = 'data/export';

% Crear directorio de salida si no existe
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
    fprintf('Directorio de salida creado: %s\n', output_dir);
end

% Abrir conexión a la base de datos
fprintf('Conectando a base de datos: %s\n', simulacion_params.DB_PATH);
conn = sim_db.open(simulacion_params.DB_PATH);

try
    % Verificar que existe la simulación
    sql = sprintf('SELECT simulation_code, name, status FROM simulations WHERE simulation_id = %d', sim_id);
    sim_info = conn.fetch(sql);
    
    if isempty(sim_info)
        error('SIM:NotFound', 'Simulación %d no encontrada', sim_id);
    end
    
    fprintf('\nSimulación: %s\n', sim_info.simulation_code{1});
    fprintf('Nombre: %s\n', sim_info.name{1});
    fprintf('Estado: %s\n\n', sim_info.status{1});
    
    % Exportar a CSV
    fprintf('[1/3] Exportando a CSV...\n');
    csv_path = fullfile(output_dir, sprintf('simulation_%d_measurements.csv', sim_id));
    sim_export.exportToCSV(sim_id, conn, csv_path);
    
    % Exportar a Excel
    fprintf('[2/3] Exportando a Excel...\n');
    xlsx_path = fullfile(output_dir, sprintf('simulation_%d_results.xlsx', sim_id));
    sim_export.exportToExcel(sim_id, conn, xlsx_path);
    
    % Exportar resumen de texto
    fprintf('[3/3] Exportando resumen de texto...\n');
    txt_path = fullfile(output_dir, sprintf('simulation_%d_summary.txt', sim_id));
    sim_export.exportSummary(sim_id, conn, txt_path);
    
    fprintf('\n✓ Exportación completada\n');
    fprintf('\nArchivos generados:\n');
    fprintf('  CSV:  %s\n', csv_path);
    fprintf('  Excel: %s\n', xlsx_path);
    fprintf('  Texto: %s\n', txt_path);
    
catch ME
    fprintf('\n✗ Error durante la exportación:\n');
    fprintf('  %s\n', ME.message);
    if ~isempty(ME.stack)
        fprintf('  en %s (línea %d)\n', ME.stack(1).name, ME.stack(1).line);
    end
    rethrow(ME);
    
finally
    % Cerrar conexión
    sim_db.close(conn);
end

fprintf('\n=== Exportación finalizada ===\n');
