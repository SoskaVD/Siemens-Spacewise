classdef sim_engine
    %SIM_ENGINE Orquestador principal del simulador de maquinaria industrial.
    %   Coordina la ejecución completa de una simulación:
    %   1. Carga catálogo de máquinas
    %   2. Crea registro de simulación en DB
    %   3. Genera perfiles horarios para cada máquina
    %   4. Inserta mediciones en DB
    %   5. Calcula totales horarios
    %   6. Calcula KPIs globales y por máquina
    %   7. Actualiza estado de simulación
    %
    %   Ejemplo:
    %       [sim_id, summary] = sim_engine.run('SIM-001', 'Baseline', 'Test run');
    %       fprintf('Completed: %d kWh\n', summary.total_energy_kwh);
    %
    %   Continuous mode:
    %       sim_engine.runContinuous('SIM-CONT', 'Continuous', 'Real-time', 42, 2, inf);

    methods (Static)

        function [sim_id, summary] = run(simCode, simName, simDesc, seed)
            %RUN Ejecuta simulación completa.
            %   [sim_id, summary] = sim_engine.run(code, name, desc, seed)
            
            % Input validation
            if nargin < 1 || isempty(simCode)
                error('SIM:MissingSimCode', 'Simulation code is required');
            end
            if nargin < 2 || isempty(simName)
                simName = simCode;
            end
            if nargin < 3 || isempty(simDesc)
                simDesc = '';
            end
            if nargin < 4 || isempty(seed)
                seed = simulacion_params.DEFAULT_SEED;
            end
            
            simulacion_params.validateSeed(seed);
            
            fprintf('Starting simulation: %s\n', simCode);
            startTime = tic;
            
            try
                % Step 1: Open database
                fprintf('  [1/8] Opening database...\n');
                conn = sim_db.open(simulacion_params.DB_PATH);
                
                % Step 2: Create simulation record
                fprintf('  [2/8] Creating simulation record...\n');
                sim_id = sim_db.insertSimulation(conn, simCode, simName, simDesc, seed);
                sim_db.updateSimulationStatus(conn, sim_id, 'RUNNING', 'Simulation started');
                
                % Step 3: Load catalog
                fprintf('  [3/8] Loading machine catalog...\n');
                machines = sim_catalog.load();
                nMachines = height(machines);
                fprintf('         Loaded %d machines\n', nMachines);
                sim_db.updateSimulationCounts(conn, sim_id, nMachines);
                
                % Step 4: Generate profiles for each machine (PARALLEL)
                fprintf('  [4/8] Generating hourly profiles (parallel)...\n');
                allMeasurements = cell(nMachines, 1);
                startDate = datetime(2026, 1, 1);
                
                % Parallel profile generation
                parfor i = 1:nMachines
                    if mod(i, 10) == 0
                        fprintf('         Progress: %d/%d machines\n', i, nMachines);
                    end
                    
                    % Generate profile
                    profile = sim_machine.generate(machines(i,:), seed, startDate);
                    
                    % Add machine metadata to profile
                    profile.machine_id = repmat(int32(machines.machine_id(i)), height(profile), 1);
                    profile.machine_code = repmat(machines.machine_code(i), height(profile), 1);
                    profile.category = repmat(machines.category{i}, height(profile), 1);
                    
                    allMeasurements{i} = profile;
                end
                fprintf('         All %d profiles generated\n', nMachines);
                
                % Step 5: Insert all measurements (sequential for DB safety)
                fprintf('  [5/8] Inserting measurements to database...\n');
                for i = 1:nMachines
                    profile = allMeasurements{i};
                    sim_db.insertMeasurements(conn, sim_id, machines.machine_id(i), profile);
                end
                
                % Step 6: Combine all measurements
                fprintf('  [6/8] Combining measurements...\n');
                allMeasTable = vertcat(allMeasurements{:});
                
                % Step 7: Calculate hourly totals and simulation results
                fprintf('  [7/8] Calculating hourly totals and results...\n');
                hourlyTotals = sim_analysis.calculateHourlyTotals(allMeasTable);
                sim_db.insertHourlyTotals(conn, sim_id, hourlyTotals);
                
                results = sim_analysis.calculateSimulationResults(sim_id, conn);
                sim_db.insertSimulationResults(conn, sim_id, results);
                
                % Calculate machine results
                machineResults = cell(nMachines, 1);
                parfor i = 1:nMachines
                    machineResult = sim_analysis.calculateMachineResults( ...
                        sim_id, machines.machine_id(i), conn);
                    machineResult.rank_by_energy = int32(i);
                    machineResults{i} = machineResult;
                end
                
                machineResultsTable = sim_engine.machineResultsToTable(machineResults);
                sim_db.insertMachineResults(conn, sim_id, machineResultsTable);
                
                % Step 8: Update status to COMPLETED
                fprintf('  [8/8] Finalizing...\n');
                elapsed = toc(startTime);
                logMsg = sprintf('Simulation completed in %.2f seconds', elapsed);
                sim_db.updateSimulationStatus(conn, sim_id, 'COMPLETED', logMsg);
                
                sim_db.close(conn);
                
                % Build summary
                summary = struct();
                summary.simulation_id = sim_id;
                summary.simulation_code = simCode;
                summary.total_machines = nMachines;
                summary.total_hours = simulacion_params.HOURS_PER_YEAR;
                summary.total_energy_kwh = results.total_energy_kwh;
                summary.avg_power_kw = results.avg_power_kw;
                summary.peak_power_kw = results.peak_power_kw;
                summary.peak_ts = results.peak_ts;
                summary.elapsed_seconds = elapsed;
                summary.status = 'COMPLETED';
                
                fprintf('\n✓ Simulation completed successfully!\n');
                fprintf('  Total energy: %.2f kWh\n', results.total_energy_kwh);
                fprintf('  Average power: %.2f kW\n', results.avg_power_kw);
                fprintf('  Peak power: %.2f kW at %s\n', ...
                    results.peak_power_kw, results.peak_ts);
                fprintf('  Elapsed time: %.2f seconds\n', elapsed);
                
            catch ME
                % Handle error
                if exist('conn', 'var') && ~isempty(conn) && conn.isopen
                    try
                        sim_db.updateSimulationStatus(conn, sim_id, 'FAILED', ME.message);
                        sim_db.close(conn);
                    catch
                    end
                end
                
                summary = struct();
                summary.simulation_id = sim_id;
                summary.status = 'FAILED';
                summary.error = ME.message;
                
                fprintf('\n✗ Simulation failed: %s\n', ME.message);
                rethrow(ME);
            end
        end

        function runContinuous(simCode, simName, simDesc, seed, intervalSeconds, maxHours)
            %RUNCONTINUOUS Ejecuta simulación continua en tiempo real.
            %   sim_engine.runContinuous(code, name, desc, seed, interval, maxHours)
            %   Genera datos hora por hora en intervalos de tiempo reales.
            
            % Input validation
            if nargin < 1 || isempty(simCode)
                error('SIM:MissingSimCode', 'Simulation code is required');
            end
            if nargin < 2 || isempty(simName)
                simName = simCode;
            end
            if nargin < 3 || isempty(simDesc)
                simDesc = '';
            end
            if nargin < 4 || isempty(seed)
                seed = simulacion_params.DEFAULT_SEED;
            end
            if nargin < 5 || isempty(intervalSeconds)
                intervalSeconds = 2;
            end
            if nargin < 6 || isempty(maxHours)
                maxHours = inf;
            end
            
            simulacion_params.validateSeed(seed);
            
            fprintf('Starting continuous simulation: %s\n', simCode);
            fprintf('Interval: %d seconds\n', intervalSeconds);
            
            conn = [];
            sim_id = -1;
            
            try
                % Step 1: Open database
                fprintf('  [1/6] Opening database...\n');
                conn = sim_db.open(simulacion_params.DB_PATH);
                
                % Step 2: Check for existing simulation to resume
                fprintf('  [2/6] Checking for existing simulation...\n');
                sql = sprintf(...
                    'SELECT simulation_id, status FROM simulations WHERE simulation_code = ''%s''', ...
                    sim_db.escapeSQL(simCode));
                existing = conn.fetch(sql);
                
                startHour = 0;
                if ~isempty(existing) && (strcmp(existing.status{1}, 'RUNNING') || strcmp(existing.status{1}, 'PAUSED'))
                    sim_id = existing.simulation_id;
                    % Resume from last hour
                    sql2 = sprintf(...
                        'SELECT MAX(hour_index) as max_hour FROM machine_measurements WHERE simulation_id = %d', ...
                        sim_id);
                    result = conn.fetch(sql2);
                    if isempty(result) || isnan(result.max_hour)
                        startHour = 0;
                    else
                        startHour = result.max_hour + 1;
                    end
                    fprintf('         Resuming simulation %d from hour %d\n', sim_id, startHour);
                    sim_db.updateSimulationStatus(conn, sim_id, 'RUNNING', 'Resumed continuous simulation');
                else
                    % Create new simulation
                    fprintf('  [3/6] Creating new simulation record...\n');
                    sim_id = sim_db.insertSimulation(conn, simCode, simName, simDesc, seed);
                    sim_db.updateSimulationStatus(conn, sim_id, 'RUNNING', 'Continuous simulation started');
                    fprintf('         Created simulation %d\n', sim_id);
                end
                
                % Step 3: Load catalog
                fprintf('  [4/6] Loading machine catalog...\n');
                machines = sim_catalog.load();
                nMachines = height(machines);
                fprintf('         Loaded %d machines\n', nMachines);
                sim_db.updateSimulationCounts(conn, sim_id, nMachines);
                
                % Step 4: Generate all profiles upfront (deterministic)
                fprintf('  [5/6] Generating hourly profiles (this may take a moment)...\n');
                profiles = cell(nMachines, 1);
                startDate = datetime(2026, 1, 1);
                
                for i = 1:nMachines
                    if mod(i, 10) == 0 || i == 1
                        fprintf('         Processing machine %d/%d: %s\n', ...
                            i, nMachines, machines.machine_code{i});
                    end
                    
                    profile = sim_machine.generate(machines(i,:), seed, startDate);
                    profile.machine_id = repmat(int32(machines.machine_id(i)), height(profile), 1);
                    profile.machine_code = repmat(machines.machine_code(i), height(profile), 1);
                    profile.category = repmat(machines.category{i}, height(profile), 1);
                    profiles{i} = profile;
                end
                fprintf('         All profiles generated\n');
                
                % Step 5: Continuous loop
                fprintf('  [6/6] Starting continuous data generation...\n');
                fprintf('         Press Ctrl+C to stop gracefully\n\n');
                
                currentHour = startHour;
                iterationCount = 0;
                maxHourLimit = min(maxHours, simulacion_params.HOURS_PER_YEAR);
                
                while currentHour < maxHourLimit
                    % Extract this hour's data for all machines
                    hourData = cell(nMachines, 1);
                    for i = 1:nMachines
                        hourData{i} = profiles{i}(currentHour + 1, :);
                    end
                    
                    % Insert measurements for each machine
                    for i = 1:nMachines
                        row = profiles{i}(currentHour + 1, :);
                        % Remove metadata columns (insertMeasurements will add them)
                        row.machine_id = [];
                        row.machine_code = [];
                        row.category = [];
                        sim_db.insertMeasurements(conn, sim_id, machines.machine_id(i), row);
                    end
                    
                    % Calculate and insert hourly totals
                    allHourMeas = vertcat(hourData{:});
                    hourlyTotal = sim_analysis.calculateHourlyTotals(allHourMeas);
                    sim_db.insertHourlyTotals(conn, sim_id, hourlyTotal);
                    
                    % Update total hours
                    sim_db.updateSimulationCounts(conn, sim_id, nMachines, currentHour + 1);
                    
                    % Write last_update.txt for frontend polling
                    try
                        fid = fopen('data/last_update.txt', 'w');
                        if fid > 0
                            fprintf(fid, '%d\n%s\n%d\n', sim_id, datestr(now), currentHour + 1);
                            fclose(fid);
                        end
                    catch
                        % Ignore errors writing update file
                    end
                    
                    % Progress output
                    iterationCount = iterationCount + 1;
                    if mod(iterationCount, 10) == 0 || iterationCount == 1
                        fprintf('[%s] Hour %d/%d | Iteration %d | Machines: %d\n', ...
                            datestr(now, 'HH:MM:SS'), currentHour, maxHourLimit, ...
                            iterationCount, nMachines);
                    end
                    
                    currentHour = currentHour + 1;
                    
                    % Wait for interval (except on last iteration)
                    if currentHour < maxHourLimit
                        pause(intervalSeconds);
                    end
                end
                
                % Step 6: Finalize
                fprintf('\n  Finalizing simulation...\n');
                logMsg = sprintf('Continuous simulation completed at hour %d', currentHour);
                sim_db.updateSimulationStatus(conn, sim_id, 'COMPLETED', logMsg);
                sim_db.close(conn);
                
                fprintf('\n✓ Continuous simulation completed successfully!\n');
                fprintf('  Total hours processed: %d\n', currentHour);
                fprintf('  Elapsed iterations: %d\n', iterationCount);
                
            catch ME
                % Handle error
                if exist('conn', 'var') && ~isempty(conn) && conn.isopen
                    try
                        if sim_id > 0
                            sim_db.updateSimulationStatus(conn, sim_id, 'STOPPED', ME.message);
                        end
                        sim_db.close(conn);
                    catch
                    end
                end
                
                fprintf('\n✗ Continuous simulation stopped: %s\n', ME.message);
                if sim_id > 0
                    fprintf('  Simulation %d can be resumed on next run\n', sim_id);
                end
                rethrow(ME);
            end
        end

    end

    methods (Static, Access = private)

        function T = machineResultsToTable(resultsCell)
            %MACHINERESULTSTOTABLE Convierte cell de structs a table.
            n = numel(resultsCell);
            if n == 0
                T = table();
                return;
            end
            
            % Get field names from first result
            fields = fieldnames(resultsCell{1});
            nFields = numel(fields);
            
            % Preallocate
            data = cell(n, nFields);
            for i = 1:n
                for j = 1:nFields
                    val = resultsCell{i}.(fields{j});
                    if ischar(val) || isstring(val)
                        data{i,j} = char(val);
                    elseif isnumeric(val)
                        data{i,j} = val;
                    else
                        data{i,j} = char(jsonencode(val));
                    end
                end
            end
            
            T = cell2table(data, 'VariableNames', fields);
        end

    end

end
