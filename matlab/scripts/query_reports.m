% 04_query_reports.m - Consulta la base, genera el reporte comparativo
% E0 vs E5, imprime el resumen de KPIs y exporta CSV.
% Uso: ejecutar después de 03_run_simulations.m.

projectRoot = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot, 'src'), fullfile(projectRoot, 'config'));

repoRoot = fileparts(projectRoot);
dbPath = fullfile(repoRoot, 'bd', 'spacewise.db');
outDir = fullfile(projectRoot, 'output');

P = spacewise_params();
dt_plot.fromDB(P, dbPath, outDir);
dt_plot.exportCSV(P, dbPath, outDir);
