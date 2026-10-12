classdef sim_analysis
    %SIM_ANALYSIS Funciones de análisis y agregación de resultados de simulación.
    %   Proporciona cálculos de totales horarios, KPIs globales, patrones
    %   temporales y ranking de máquinas.
    %
    %   Ejemplo:
    %       totals = sim_analysis.calculateHourlyTotals(allMeasurements);
    %       results = sim_analysis.calculateSimulationResults(sim_id, conn);

    methods (Static)

        function totals = calculateHourlyTotals(allMeasurements)
            %CALCULATEHOURLYTOTALES Agrega mediciones por hora.
            %   totals = sim_analysis.calculateHourlyTotals(allMeasurements)
            %   allMeasurements: table con ts, hour_index, active_power_kw, 
            %                    energy_kwh, load_factor, machine_id, category
            
            if isempty(allMeasurements) || height(allMeasurements) == 0
                totals = table();
                return;
            end
            
            % Get unique hours
            uniqueHours = unique(allMeasurements.hour_index);
            nHours = numel(uniqueHours);
            
            % Preallocate
            ts = strings(nHours, 1);
            totalPower = zeros(nHours, 1);
            totalEnergy = zeros(nHours, 1);
            machineCount = zeros(nHours, 1);
            avgLoadFactor = zeros(nHours, 1);
            peakPower = zeros(nHours, 1);
            peakMachineId = NaN(nHours, 1);
            
            % Category breakdown columns
            catCols = {'hvac_power_kw', 'compressors_power_kw', 'motors_power_kw', ...
                       'pumps_power_kw', 'lighting_power_kw', 'lab_power_kw', ...
                       'manufacturing_power_kw', 'it_power_kw', 'auxiliary_power_kw'};
            catData = zeros(nHours, numel(catCols));
            
            for i = 1:nHours
                hourIdx = uniqueHours(i);
                hourData = allMeasurements(allMeasurements.hour_index == hourIdx, :);
                
                ts(i) = hourData.ts(1);
                totalPower(i) = sum(hourData.active_power_kw);
                totalEnergy(i) = sum(hourData.energy_kwh);
                machineCount(i) = sum(hourData.active_power_kw > 0);
                avgLoadFactor(i) = mean(hourData.load_factor(hourData.active_power_kw > 0));
                
                % Find peak machine
                if ~isempty(hourData.active_power_kw)
                    [peakVal, peakIdx] = max(hourData.active_power_kw);
                    peakPower(i) = peakVal;
                    peakMachineId(i) = hourData.machine_id(peakIdx);
                end
                
                % Category breakdown
                if ismember('category', hourData.Properties.VariableNames)
                    catNames = sim_analysis.getCategoryNames();
                    for c = 1:numel(catNames)
                        catMask = strcmp(hourData.category, catNames{c});
                        catData(i, c) = sum(hourData.active_power_kw(catMask));
                    end
                end
            end
            
            % Build output table
            totals = table();
            totals.ts = ts;
            totals.hour_index = int32(uniqueHours);
            totals.total_power_kw = totalPower;
            totals.total_energy_kwh = totalEnergy;
            
            for c = 1:numel(catCols)
                totals.(catCols{c}) = catData(:, c);
            end
            
            totals.machine_count = int32(machineCount);
            totals.avg_load_factor = avgLoadFactor;
            totals.peak_power_kw = peakPower;
            totals.peak_machine_id = int32(peakMachineId);
        end

        function results = calculateSimulationResults(sim_id, conn)
            %CALCULATESIMULATIONRESULTS Calcula KPIs globales de la simulación.
            %   results = sim_analysis.calculateSimulationResults(sim_id, conn)
            
            % Query hourly totals
            % Use explicit columns to avoid NULL values in nullable columns
            % (machine_count, avg_load_factor, peak_power_kw, peak_machine_id)
            % which cause sqlite.fetch to crash.
            sql = sprintf(...
                ['SELECT ts, hour_index, total_power_kw, total_energy_kwh, ' ...
                 'hvac_power_kw, compressors_power_kw, motors_power_kw, ' ...
                 'pumps_power_kw, lighting_power_kw, lab_power_kw, ' ...
                 'manufacturing_power_kw, it_power_kw, auxiliary_power_kw ' ...
                 'FROM hourly_totals WHERE simulation_id = %d ' ...
                 'ORDER BY hour_index'], ...
                sim_id);
            hourlyTotals = conn.fetch(sql);
            
            if isempty(hourlyTotals)
                error('SIM:NoHourlyData', 'No hourly totals found for simulation %d', sim_id);
            end
            
            % Calculate KPIs
            totalEnergy = sum(hourlyTotals.total_energy_kwh);
            avgPower = mean(hourlyTotals.total_power_kw);
            [peakPower, peakIdx] = max(hourlyTotals.total_power_kw);
            peakTs = hourlyTotals.ts(peakIdx);
            
            % Category breakdown (sum across all hours)
            catCols = {'hvac_power_kw', 'compressors_power_kw', 'motors_power_kw', ...
                       'pumps_power_kw', 'lighting_power_kw', 'lab_power_kw', ...
                       'manufacturing_power_kw', 'it_power_kw', 'auxiliary_power_kw'};
            energyByCategory = struct();
            for c = 1:numel(catCols)
                colName = catCols{c};
                catKey = regexprep(colName, '_power_kw', '');
                energyByCategory.(catKey) = sum(hourlyTotals.(colName));
            end
            
            % Monthly pattern
            monthlyEnergy = sim_analysis.getMonthlyPattern(hourlyTotals);
            
            % Weekly pattern
            weeklyPattern = sim_analysis.getWeeklyPattern(hourlyTotals);
            
            % Daily pattern
            dailyPattern = sim_analysis.getDailyPattern(hourlyTotals);
            
            % Top machines
            topMachines = sim_analysis.getTopMachines(sim_id, conn, 10);
            
            % Energy by criticality
            energyByCriticality = sim_analysis.calculateEnergyByCriticality(sim_id, conn);
            
            % Flexibility potential
            flexibilityPotential = sim_analysis.calculateFlexibilityPotential(sim_id, conn);
            
            % Build results struct
            results = struct();
            results.total_energy_kwh = totalEnergy;
            results.avg_power_kw = avgPower;
            results.peak_power_kw = peakPower;
            results.peak_ts = char(peakTs);
            results.energy_by_category_json = char(jsonencode(energyByCategory));
            results.monthly_energy_json = char(jsonencode(monthlyEnergy));
            results.weekly_pattern_json = char(jsonencode(weeklyPattern));
            results.daily_pattern_json = char(jsonencode(dailyPattern));
            results.top_machines_json = char(jsonencode(topMachines));
            results.energy_by_criticality_json = char(jsonencode(energyByCriticality));
            results.flexibility_potential_kwh = flexibilityPotential;
            results.avg_power_factor = sim_analysis.calculateAvgPowerFactor(sim_id, conn);
            results.avg_thd_pct = sim_analysis.calculateAvgTHD(sim_id, conn);
        end

        function machineResult = calculateMachineResults(sim_id, machine_id, conn)
            %CALCULATEMACHINERESULTS Calcula KPIs para una máquina específica.
            %   machineResult = sim_analysis.calculateMachineResults(sim_id, machine_id, conn)
            
            % Query measurements for this machine
            % Use explicit columns to avoid NULL values in nullable columns
            % (power_factor, current_a, thd_pct, voltage_v, operation_state,
            % cycle_phase) which cause sqlite.fetch to crash.
            sql = sprintf(...
                ['SELECT ts, active_power_kw, energy_kwh, load_factor ' ...
                 'FROM machine_measurements WHERE simulation_id = %d ' ...
                 'AND machine_id = %d ORDER BY hour_index'], ...
                sim_id, machine_id);
            measurements = conn.fetch(sql);
            
            if isempty(measurements)
                error('SIM:NoMachineData', 'No data for machine %d in simulation %d', ...
                    machine_id, sim_id);
            end
            
            % Calculate KPIs
            totalEnergy = sum(measurements.energy_kwh);
            avgPower = mean(measurements.active_power_kw);
            [peakPower, peakIdx] = max(measurements.active_power_kw);
            peakTs = measurements.ts(peakIdx);
            operatingHours = sum(measurements.active_power_kw > 0);
            avgLoadFactor = mean(measurements.load_factor(measurements.active_power_kw > 0));
            
            % Rated power (query from machines table, fallback: estimate from measurements)
            % The machines catalog may not be inserted into the DB at this point.
            % Use the relationship: active_power ≈ rated_power * load_factor
            % so rated_power ≈ active_power / load_factor (median across operating hours).
            sqlMachine = sprintf('SELECT rated_power_kw FROM machines WHERE machine_id = %d', machine_id);
            machineData = conn.fetch(sqlMachine);
            if isempty(machineData) || isempty(machineData.rated_power_kw)
                runningMask = (measurements.load_factor > 0);
                if any(runningMask)
                    ratedPower = median(measurements.active_power_kw(runningMask) ./ ...
                                        measurements.load_factor(runningMask));
                else
                    ratedPower = peakPower;
                end
            else
                ratedPower = machineData.rated_power_kw(1);
            end
            
            % Capacity factor = actual energy / max possible energy
            maxPossibleEnergy = ratedPower * simulacion_params.HOURS_PER_YEAR;
            capacityFactor = totalEnergy / maxPossibleEnergy;
            
            % Monthly energy
            monthlyEnergy = sim_analysis.getMachineMonthlyPattern(measurements);
            
            % Hourly pattern (average by hour of day)
            hourlyPattern = sim_analysis.getMachineHourlyPattern(measurements);
            
            % Get total simulation energy for share calculation
            % simulation_results may not be populated yet (calculated after all machines).
            % Fallback: sum energy from machine_measurements directly.
            sqlTotal = sprintf(...
                'SELECT total_energy_kwh FROM simulation_results WHERE simulation_id = %d', sim_id);
            totalResult = conn.fetch(sqlTotal);
            if isempty(totalResult) || isempty(totalResult.total_energy_kwh)
                sqlTotalFallback = sprintf(...
                    'SELECT SUM(energy_kwh) as total FROM machine_measurements WHERE simulation_id = %d', sim_id);
                totalFallback = conn.fetch(sqlTotalFallback);
                if isempty(totalFallback) || isempty(totalFallback.total)
                    totalSimEnergy = totalEnergy;
                else
                    totalSimEnergy = totalFallback.total(1);
                end
            else
                totalSimEnergy = totalResult.total_energy_kwh(1);
            end
            energySharePct = (totalEnergy / totalSimEnergy) * 100;
            
            % Build result struct
            machineResult = struct();
            machineResult.machine_id = int32(machine_id);
            machineResult.total_energy_kwh = totalEnergy;
            machineResult.avg_power_kw = avgPower;
            machineResult.peak_power_kw = peakPower;
            machineResult.peak_ts = char(peakTs);
            machineResult.operating_hours = operatingHours;
            machineResult.avg_load_factor = avgLoadFactor;
            machineResult.capacity_factor = capacityFactor;
            machineResult.monthly_energy_json = char(jsonencode(monthlyEnergy));
            machineResult.hourly_pattern_json = char(jsonencode(hourlyPattern));
            machineResult.energy_share_pct = energySharePct;
        end

        function monthly = getMonthlyPattern(hourlyTotals)
            %GETMONTHLYPATTERN Agrega energía por mes.
            %   monthly = sim_analysis.getMonthlyPattern(hourlyTotals)
            
            monthly = struct();
            for m = 1:12
                % Extract month from timestamp
                monthMask = sim_analysis.extractMonth(hourlyTotals.ts) == m;
                monthlyEnergy = sum(hourlyTotals.total_energy_kwh(monthMask));
                monthly.(sprintf('month_%02d', m)) = monthlyEnergy;
            end
        end

        function weekly = getWeeklyPattern(hourlyTotals)
            %GETWEEKLYPATTERN Agrega energía por día de la semana.
            %   weekly = sim_analysis.getWeeklyPattern(hourlyTotals)
            
            dayNames = {'monday', 'tuesday', 'wednesday', 'thursday', ...
                        'friday', 'saturday', 'sunday'};
            weekly = struct();
            
            for d = 1:7
                dayMask = sim_analysis.extractDayOfWeek(hourlyTotals.ts) == d;
                weeklyEnergy = sum(hourlyTotals.total_energy_kwh(dayMask));
                weekly.(dayNames{d}) = weeklyEnergy;
            end
        end

        function daily = getDailyPattern(hourlyTotals)
            %GETDAILYPATTERN Agrega energía promedio por hora del día.
            %   daily = sim_analysis.getDailyPattern(hourlyTotals)
            
            daily = struct();
            for h = 0:23
                hourMask = sim_analysis.extractHourOfDay(hourlyTotals.ts) == h;
                avgPower = mean(hourlyTotals.total_power_kw(hourMask));
                daily.(sprintf('hour_%02d', h)) = avgPower;
            end
        end

        function topMachines = getTopMachines(sim_id, conn, n)
            %GETTOPMACHINES Devuelve top N máquinas por consumo.
            %   topMachines = sim_analysis.getTopMachines(sim_id, conn, 10)
            
            if nargin < 3 || isempty(n)
                n = 10;
            end
            
            sql = sprintf(...
                ['SELECT m.machine_code, m.name, m.category, ' ...
                 'SUM(mm.energy_kwh) as total_energy_kwh ' ...
                 'FROM machine_measurements mm ' ...
                 'JOIN machines m ON mm.machine_id = m.machine_id ' ...
                 'WHERE mm.simulation_id = %d ' ...
                 'GROUP BY mm.machine_id ' ...
                 'ORDER BY total_energy_kwh DESC ' ...
                 'LIMIT %d'], ...
                sim_id, n);
            
            topMachines = conn.fetch(sql);
        end

    end

    methods (Static, Access = private)

        function catNames = getCategoryNames()
            %GETCATEGORYNAMES Devuelve nombres de categorías en orden.
            catNames = {'HVAC', 'Compresores', 'Motores', 'Bombas', ...
                        'Iluminacion', 'Laboratorios', 'Manufactura', ...
                        'TI', 'Auxiliares'};
        end

        function months = extractMonth(tsArray)
            %EXTRACTMONTH Extrae mes (1-12) de array de timestamps.
            months = zeros(numel(tsArray), 1);
            for i = 1:numel(tsArray)
                try
                    dt = datetime(tsArray(i), 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
                    months(i) = dt.month;
                catch
                    months(i) = 1;  % Default to January if parsing fails
                end
            end
        end

        function days = extractDayOfWeek(tsArray)
            %EXTRACTDAYOFWEEK Extrae día de semana (1=Monday, 7=Sunday).
            days = zeros(numel(tsArray), 1);
            for i = 1:numel(tsArray)
                try
                    dt = datetime(tsArray(i), 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
                    days(i) = dt.DayOfWeek;  % 1=Sunday, 7=Saturday in MATLAB
                    % Convert to 1=Monday, 7=Sunday
                    days(i) = mod(days(i), 7) + 1;
                catch
                    days(i) = 1;
                end
            end
        end

        function hours = extractHourOfDay(tsArray)
            %EXTRACTHOUROFDAY Extrae hora del día (0-23).
            hours = zeros(numel(tsArray), 1);
            for i = 1:numel(tsArray)
                try
                    dt = datetime(tsArray(i), 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
                    hours(i) = dt.hour;
                catch
                    hours(i) = 0;
                end
            end
        end

        function monthly = getMachineMonthlyPattern(measurements)
            %GETMACHINEMONTHLYPATTERN Patrón mensual para una máquina.
            monthly = struct();
            for m = 1:12
                monthMask = sim_analysis.extractMonth(measurements.ts) == m;
                monthlyEnergy = sum(measurements.energy_kwh(monthMask));
                monthly.(sprintf('month_%02d', m)) = monthlyEnergy;
            end
        end

        function hourly = getMachineHourlyPattern(measurements)
            %GETMACHINEHOURLYPATTERN Patrón horario promedio para una máquina.
            hourly = struct();
            for h = 0:23
                hourMask = sim_analysis.extractHourOfDay(measurements.ts) == h;
                avgPower = mean(measurements.active_power_kw(hourMask));
                hourly.(sprintf('hour_%02d', h)) = avgPower;
            end
        end

        function energy = calculateEnergyByCriticality(sim_id, conn)
            %CALCULATEENERGYBYCRITICALITY Agrega energía por nivel de criticidad.
            sql = sprintf(...
                ['SELECT m.criticality, SUM(mm.energy_kwh) as total_energy ' ...
                 'FROM machine_measurements mm ' ...
                 'JOIN machines m ON mm.machine_id = m.machine_id ' ...
                 'WHERE mm.simulation_id = %d ' ...
                 'GROUP BY m.criticality'], ...
                sim_id);
            
            result = conn.fetch(sql);
            energy = struct();
            for i = 1:height(result)
                critKey = lower(result.criticality{i});
                energy.(critKey) = result.total_energy(i);
            end
        end

        function potential = calculateFlexibilityPotential(sim_id, conn)
            %CALCULATEFLEXIBILITYPOTENTIAL Calcula energía desplazable.
            sql = sprintf(...
                ['SELECT SUM(mm.energy_kwh) as flexible_energy ' ...
                 'FROM machine_measurements mm ' ...
                 'JOIN machines m ON mm.machine_id = m.machine_id ' ...
                 'WHERE mm.simulation_id = %d AND m.flexibility = 1'], ...
                sim_id);
            
            result = conn.fetch(sql);
            if isempty(result) || isempty(result.flexible_energy)
                potential = 0;
            else
                potential = result.flexible_energy;
            end
        end

        function avgPF = calculateAvgPowerFactor(sim_id, conn)
            %CALCULATEAVGPOWERFACTOR Calcula factor de potencia promedio.
            sql = sprintf(...
                'SELECT COALESCE(AVG(power_factor), 0) as avg_pf FROM machine_measurements WHERE simulation_id = %d', ...
                sim_id);
            
            result = conn.fetch(sql);
            if isempty(result) || result.avg_pf == 0
                avgPF = NaN;
            else
                avgPF = result.avg_pf;
            end
        end

        function avgTHD = calculateAvgTHD(sim_id, conn)
            %CALCULATEAVGTHD Calcula THD promedio.
            sql = sprintf(...
                'SELECT COALESCE(AVG(thd_pct), 0) as avg_thd FROM machine_measurements WHERE simulation_id = %d', ...
                sim_id);
            
            result = conn.fetch(sql);
            if isempty(result) || result.avg_thd == 0
                avgTHD = NaN;
            else
                avgTHD = result.avg_thd;
            end
        end

    end

end
