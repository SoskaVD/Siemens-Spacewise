% 03_run_simulations.m - Ejecuta el gemelo para todos los escenarios y
% variaciones (E0-E5 + S01-S05) y guarda mediciones, ambiente, perfiles,
% resultados y eventos en bd/spacewise.db.
% Uso: ejecutar después de 01_init_db.m y 02_seed_devices.m.

projectRoot = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot, 'src'), fullfile(projectRoot, 'config'));

repoRoot = fileparts(projectRoot);
dbPath = fullfile(repoRoot, 'bd', 'spacewise.db');
outDir = fullfile(projectRoot, 'output');

P = spacewise_params();
scs = dt_scenario.definitions();

conn = dt_db.open(dbPath);
devTable = conn.fetch('SELECT * FROM devices ORDER BY device_id');
fprintf('Dispositivos cargados desde BD: %d\n', height(devTable));

for i = 1:numel(scs)
    sc = scs(i);
    Psc = dt_scenario.mergeParams(P, sc.override);
    tStart = tic;

    [res, env, base, ctrl] = dt_engine.run(Psc, sc);

    scenario_id = dt_db.insertScenario(conn, sc.scenario_code, sc.name, sc.description, Psc, sc.is_baseline);
    sim_id = dt_db.insertSimulation(conn, scenario_id, dt_engine.version());

    [measT, envT, eventsT] = dt_measurements.generate(Psc, env, ctrl, devTable);
    dt_db.insertEnvironment(conn, sim_id, envT);
    dt_db.insertMeasurements(conn, sim_id, measT);
    dt_db.insertProfiles(conn, sim_id, dt_analysis.profilesTable(base, ctrl, env));
    dt_db.insertResults(conn, sim_id, dt_analysis.resultsTable(res, Psc, base, ctrl));
    dt_db.insertEvents(conn, sim_id, eventsT);
    dt_db.finishSimulation(conn, sim_id, 'DONE', sprintf('scenario %s', sc.scenario_code));

    dt_plot.figures(base, ctrl, env, res, fullfile(outDir, sc.scenario_code));

    fprintf('[%s] ahorro=%5.2f%%  peak %6.1f->%6.1f kW  payback=%4.2f años  VAN=%10.0f USD  (%.1fs)\n', ...
        sc.scenario_code, res.savPct, res.peakBase, res.peakCtrl, res.payback, res.VAN, toc(tStart));
end

dt_db.close(conn);
fprintf('\nSimulaciones completadas en: %s\n', dbPath);
fprintf('Gráficos guardados en: %s\n', outDir);
