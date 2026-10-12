classdef sim_export
    %SIM_EXPORT Funciones de exportación de resultados de simulación.
    %   Exporta datos a CSV, Excel y reportes de texto.
    %
    %   Ejemplo:
    %       sim_export.exportToCSV(sim_id, conn, 'results.csv');
    %       sim_export.exportToExcel(sim_id, conn, 'results.xlsx');

    methods (Static)

        function exportToCSV(sim_id, conn, outputPath, startDate, endDate)
            %EXPORTTOCSV Exporta mediciones a archivo CSV.
            %   sim_export.exportToCSV(sim_id, conn, outputPath)
            %   sim_export.exportToCSV(sim_id, conn, outputPath, startDate, endDate)
            
            if nargin < 3 || isempty(outputPath)
                error('SIM:MissingOutputPath', 'Output path is required');
            end
            if nargin < 4 || isempty(startDate)
                startDate = '';
            end
            if nargin < 5 || isempty(endDate)
                endDate = '';
            end
            
            % Validate path
            if contains(outputPath, '..')
                error('SIM:UnsafePath', 'Output path cannot contain ".."');
            end
            
            % Build query
            sql = sprintf(...
                ['SELECT mm.ts, mm.hour_index, m.machine_code, m.name, m.category, ' ...
                 'mm.active_power_kw, mm.energy_kwh, mm.load_factor, ' ...
                 'mm.operation_state, mm.cycle_phase ' ...
                 'FROM machine_measurements mm ' ...
                 'JOIN machines m ON mm.machine_id = m.machine_id ' ...
                 'WHERE mm.simulation_id = %d'], ...
                sim_id);
            
            % Add date filters if provided
            if ~isempty(startDate)
                sql = [sql, sprintf(' AND mm.ts >= ''%s''', sim_db.escapeSQL(startDate))];
            end
            if ~isempty(endDate)
                sql = [sql, sprintf(' AND mm.ts <= ''%s''', sim_db.escapeSQL(endDate))];
            end
            
            sql = [sql, ' ORDER BY mm.ts, m.machine_code'];
            
            % Execute query
            data = conn.fetch(sql);
            
            if isempty(data)
                warning('SIM:NoData', 'No data to export for simulation %d', sim_id);
                return;
            end
            
            % Write to CSV
            writetable(data, outputPath);
            fprintf('Exported %d rows to %s\n', height(data), outputPath);
        end

        function exportToExcel(sim_id, conn, outputPath)
            %EXPORTTOEXCEL Exporta resultados a Excel con múltiples hojas.
            %   sim_export.exportToExcel(sim_id, conn, outputPath)
            
            if nargin < 3 || isempty(outputPath)
                error('SIM:MissingOutputPath', 'Output path is required');
            end
            
            if contains(outputPath, '..')
                error('SIM:UnsafePath', 'Output path cannot contain ".."');
            end
            
            fprintf('Exporting simulation %d to Excel...\n', sim_id);
            
            % Sheet 1: Summary
            sqlSummary = sprintf(...
                'SELECT * FROM simulation_results WHERE simulation_id = %d', sim_id);
            summary = conn.fetch(sqlSummary);
            
            % Sheet 2: Hourly totals
            sqlHourly = sprintf(...
                'SELECT * FROM hourly_totals WHERE simulation_id = %d ORDER BY hour_index', ...
                sim_id);
            hourly = conn.fetch(sqlHourly);
            
            % Sheet 3: Machine results
            sqlMachineResults = sprintf(...
                ['SELECT m.machine_code, m.name, m.category, mr.* ' ...
                 'FROM machine_results mr ' ...
                 'JOIN machines m ON mr.machine_id = m.machine_id ' ...
                 'WHERE mr.simulation_id = %d ' ...
                 'ORDER BY mr.total_energy_kwh DESC'], ...
                sim_id);
            machineResults = conn.fetch(sqlMachineResults);
            
            % Sheet 4: Top consumers
            topMachines = sim_analysis.getTopMachines(sim_id, conn, 20);
            
            % Write to Excel
            if ~isempty(summary)
                writetable(summary, outputPath, 'Sheet', 'Summary');
            end
            if ~isempty(hourly)
                writetable(hourly, outputPath, 'Sheet', 'Hourly');
            end
            if ~isempty(machineResults)
                writetable(machineResults, outputPath, 'Sheet', 'ByMachine');
            end
            if ~isempty(topMachines)
                writetable(topMachines, outputPath, 'Sheet', 'TopConsumers');
            end
            
            fprintf('Exported to %s\n', outputPath);
        end

        function exportSummary(sim_id, conn, outputPath)
            %EXPORTSUMMARY Exporta reporte de texto con resumen ejecutivo.
            %   sim_export.exportSummary(sim_id, conn, outputPath)
            
            if nargin < 3 || isempty(outputPath)
                error('SIM:MissingOutputPath', 'Output path is required');
            end
            
            if contains(outputPath, '..')
                error('SIM:UnsafePath', 'Output path cannot contain ".."');
            end
            
            % Query simulation metadata
            sqlSim = sprintf('SELECT * FROM simulations WHERE simulation_id = %d', sim_id);
            simData = conn.fetch(sqlSim);
            
            % Query results
            sqlResults = sprintf('SELECT * FROM simulation_results WHERE simulation_id = %d', sim_id);
            results = conn.fetch(sqlResults);
            
            if isempty(results)
                error('SIM:NoResults', 'No results found for simulation %d', sim_id);
            end
            
            % Build report
            report = {};
            report{end+1} = '=================================================================';
            report{end+1} = 'SIMULATION REPORT - INDUSTRIAL MACHINERY SIMULATOR';
            report{end+1} = '=================================================================';
            report{end+1} = '';
            report{end+1} = sprintf('Simulation Code: %s', simData.simulation_code{1});
            report{end+1} = sprintf('Name: %s', simData.name{1});
            report{end+1} = sprintf('Description: %s', simData.description{1});
            report{end+1} = sprintf('Status: %s', simData.status{1});
            report{end+1} = sprintf('Engine Version: %s', simData.engine_version{1});
            report{end+1} = sprintf('Start Time: %s', simData.start_time{1});
            report{end+1} = sprintf('End Time: %s', simData.end_time{1});
            report{end+1} = sprintf('Total Machines: %d', simData.total_machines);
            report{end+1} = sprintf('Total Hours: %d', simData.total_hours);
            report{end+1} = '';
            report{end+1} = '-----------------------------------------------------------------';
            report{end+1} = 'ENERGY SUMMARY';
            report{end+1} = '-----------------------------------------------------------------';
            report{end+1} = sprintf('Total Energy Consumption: %.2f kWh', results.total_energy_kwh);
            report{end+1} = sprintf('Average Power: %.2f kW', results.avg_power_kw);
            report{end+1} = sprintf('Peak Power: %.2f kW', results.peak_power_kw);
            report{end+1} = sprintf('Peak Timestamp: %s', results.peak_ts);
            report{end+1} = '';
            report{end+1} = '-----------------------------------------------------------------';
            report{end+1} = 'ENERGY BY CATEGORY';
            report{end+1} = '-----------------------------------------------------------------';
            
            % Parse category breakdown
            if ~isempty(results.energy_by_category_json)
                energyByCat = jsondecode(results.energy_by_category_json{1});
                catFields = fieldnames(energyByCat);
                for i = 1:numel(catFields)
                    catName = catFields{i};
                    catEnergy = energyByCat.(catName);
                    report{end+1} = sprintf('  %-20s: %12.2f kWh', catName, catEnergy);
                end
            end
            
            report{end+1} = '';
            report{end+1} = '-----------------------------------------------------------------';
            report{end+1} = 'TOP 10 ENERGY CONSUMERS';
            report{end+1} = '-----------------------------------------------------------------';
            
            topMachines = sim_analysis.getTopMachines(sim_id, conn, 10);
            for i = 1:height(topMachines)
                report{end+1} = sprintf('%2d. %-30s (%s): %10.2f kWh', ...
                    i, topMachines.name{i}, topMachines.machine_code{i}, ...
                    topMachines.total_energy_kwh(i));
            end
            
            report{end+1} = '';
            report{end+1} = '=================================================================';
            report{end+1} = sprintf('Report generated: %s', datestr(now));
            report{end+1} = '=================================================================';
            
            % Write to file
            fid = fopen(outputPath, 'w');
            if fid == -1
                error('SIM:CannotWriteFile', 'Cannot write to %s', outputPath);
            end
            for i = 1:numel(report)
                fprintf(fid, '%s\n', report{i});
            end
            fclose(fid);
            
            fprintf('Summary report exported to %s\n', outputPath);
        end

    end

end
