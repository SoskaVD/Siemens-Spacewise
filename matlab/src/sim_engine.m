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
                
                % Step 4: Generate profiles for each machine
                fprintf('  [4/8] Generating hourly profiles...\n');
                allMeasurements = {};
                machineResults = cell(nMachines, 1);
                startDate = datetime(2026, 1, 1);
                
                for i = 1:nMachines
                    fprintf('         Processing machine %d/%d: %s\n', ...
                        i, nMachines, machines.machine_code{i});
                    
                    % Generate profile
                    profile = sim_machine.generate(machines(i,:), seed, startDate);
                    
                    % Add machine metadata to profile
                    profile.machine_id = repmat(int32(machines.machine_id(i)), height(profile), 1);
                    profile.machine_code = repmat(machines.machine_code(i), height(profile), 1);
                    profile.category = repmat(machines.category{i}, height(profile), 1);
                    
                    % Insert measurements
                    sim_db.insertMeasurements(conn, sim_id, machines.machine_id(i), profile);
                    
                    allMeasurements{end+1} = profile; %#ok<AGROW>
                    
                    % Calculate machine results
                    machineResult = sim_analysis.calculateMachineResults( ...
                        sim_id, machines.machine_id(i), conn);
                    machineResult.rank_by_energy = int32(i);  % Will be sorted later
                    machineResults{i} = machineResult;
                end
                
                % Step 5: Combine all measurements
                fprintf('  [5/8] Combining measurements...\n');
                allMeasTable = vertcat(allMeasurements{:});
                
                % Step 6: Calculate hourly totals
                fprintf('  [6/8] Calculating hourly totals...\n');
                hourlyTotals = sim_analysis.calculateHourlyTotals(allMeasTable);
                sim_db.insertHourlyTotals(conn, sim_id, hourlyTotals);
                
                % Step 7: Calculate simulation results
                fprintf('  [7/8] Calculating simulation results...\n');
                results = sim_analysis.calculateSimulationResults(sim_id, conn);
                sim_db.insertSimulationResults(conn, sim_id, results);
                
                % Insert machine results
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
