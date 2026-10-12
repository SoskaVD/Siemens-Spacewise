classdef sim_machine
    %SIM_MACHINE Genera perfiles horarios de consumo para una máquina individual.
    %   Simula 8760 horas de operación considerando:
    %   - Horarios de operación (hours_per_day, days_per_week)
    %   - Variabilidad estacional
    %   - Ciclos de trabajo (RUNNING, PARTIAL, STANDBY)
    %   - Transitorios de arranque
    %   - Ruido aleatorio para realismo
    %
    %   Ejemplo:
    %       profile = sim_machine.generate(machine, seed);
    %       fprintf('Generated %d hours\n', height(profile));

    methods (Static)

        function profile = generate(machine, seed, startDate)
            %GENERATE Genera perfil horario de 8760 horas para una máquina.
            %   profile = sim_machine.generate(machine) usa seed por defecto.
            %   profile = sim_machine.generate(machine, seed) usa seed específico.
            %   profile = sim_machine.generate(machine, seed, startDate) usa fecha inicio.
            
            % Input validation
            if nargin < 1 || isempty(machine)
                error('SIM:InvalidMachine', 'Machine struct is required');
            end
            if nargin < 2 || isempty(seed)
                seed = simulacion_params.DEFAULT_SEED;
            end
            if nargin < 3 || isempty(startDate)
                startDate = datetime(2026, 1, 1);
            end
            
            simulacion_params.validateSeed(seed);
            
            % Set seed for reproducibility (machine-specific)
            machineID = machine.machine_id;
            if ismissing(machineID) || isnan(machineID)
                machineID = 1;
            end
            rng(seed + machineID);
            
            % Constants
            H = simulacion_params.HOURS_PER_YEAR;
            
            % Preallocate output arrays
            ts = strings(H, 1);
            hourIndex = (0:H-1)';
            activePower = zeros(H, 1);
            energy = zeros(H, 1);
            loadFactorOut = zeros(H, 1);
            opState = cell(H, 1);
            cyclePhase = cell(H, 1);
            
            % Extract machine parameters
            ratedPower = machine.rated_power_kw;
            hoursPerDay = machine.hours_per_day;
            daysPerWeek = machine.days_per_week;
            avgLoadFactor = machine.load_factor;
            seasonalVar = machine.seasonal_variability;
            startupTime = machine.startup_time_s;
            startupMult = machine.startup_multiplier;
            standbyPct = machine.standby_pct;
            
            % Parse work cycles JSON
            workCycles = sim_machine.parseWorkCycles(machine.work_cycles_json);
            
            % Generate timestamps
            for h = 0:H-1
                ts(h+1) = char(startDate + hours(h));
            end
            
            % Generate hourly profiles
            for h = 0:H-1
                hourOfDay = mod(h, 24);
                dayOfWeek = mod(floor(h / 24), 7) + 1;  % 1=Monday, 7=Sunday
                dayOfYear = floor(h / 24) + 1;
                month = sim_machine.getHourMonth(dayOfYear);
                
                % Determine if machine should be running
                isOperatingHour = sim_machine.isOperatingHour( ...
                    hourOfDay, dayOfWeek, hoursPerDay, daysPerWeek);
                
                if ~isOperatingHour
                    % Machine is OFF
                    activePower(h+1) = 0;
                    energy(h+1) = 0;
                    loadFactorOut(h+1) = 0;
                    opState{h+1} = 'OFF';
                    cyclePhase{h+1} = 'OFF';
                else
                    % Machine is operating - determine cycle phase
                    [phase, phaseLoad] = sim_machine.determineCyclePhase( ...
                        h, workCycles, avgLoadFactor);
                    
                    % Apply seasonal variability
                    seasonalMult = sim_machine.getSeasonalMultiplier( ...
                        month, seasonalVar);
                    
                    % Apply load factor with noise
                    noise = randn() * simulacion_params.NOISE_STD_DEV;
                    adjustedLoad = phaseLoad * seasonalMult + noise;
                    adjustedLoad = max(0, min(1, adjustedLoad));  % Clamp to [0,1]
                    
                    % Calculate power
                    if strcmp(phase, 'STARTUP')
                        % Startup transient
                        activePower(h+1) = ratedPower * startupMult;
                        loadFactorOut(h+1) = startupMult;
                        opState{h+1} = 'STARTUP';
                        cyclePhase{h+1} = 'STARTUP';
                    elseif strcmp(phase, 'STANDBY')
                        % Standby mode
                        activePower(h+1) = ratedPower * (standbyPct / 100);
                        loadFactorOut(h+1) = standbyPct / 100;
                        opState{h+1} = 'STANDBY';
                        cyclePhase{h+1} = 'STANDBY';
                    elseif strcmp(phase, 'PARTIAL')
                        % Partial load
                        activePower(h+1) = ratedPower * adjustedLoad;
                        loadFactorOut(h+1) = adjustedLoad;
                        opState{h+1} = 'PARTIAL';
                        cyclePhase{h+1} = 'PARTIAL_LOAD';
                    else
                        % Full load (RUNNING)
                        activePower(h+1) = ratedPower * adjustedLoad;
                        loadFactorOut(h+1) = adjustedLoad;
                        opState{h+1} = 'RUNNING';
                        cyclePhase{h+1} = 'FULL_LOAD';
                    end
                    
                    % Energy = power * 1 hour
                    energy(h+1) = activePower(h+1);
                end
            end
            
            % Build output table
            profile = table();
            profile.ts = ts;
            profile.hour_index = int32(hourIndex);
            profile.active_power_kw = activePower;
            profile.energy_kwh = energy;
            profile.load_factor = loadFactorOut;
            profile.operation_state = opState;
            profile.cycle_phase = cyclePhase;
        end

    end

    methods (Static, Access = private)

        function cycles = parseWorkCycles(jsonStr)
            %PARSEWORKCYCLES Parsea JSON de ciclos de trabajo.
            if isempty(jsonStr) || jsonStr == "''"
                % Default: 100% running at average load
                cycles = struct('RUNNING', 1.0);
                return;
            end
            
            try
                cycles = jsondecode(jsonStr);
            catch
                % If parsing fails, use default
                cycles = struct('RUNNING', 1.0);
            end
        end

        function flag = isOperatingHour(hourOfDay, dayOfWeek, hoursPerDay, daysPerWeek)
            %ISOPERATINGHOUR Determina si la máquina opera en esta hora.
            %   hourOfDay: 0-23
            %   dayOfWeek: 1-7 (1=Monday, 7=Sunday)
            
            % Check day of week (assume work days are Monday-Friday + extra)
            workDays = min(daysPerWeek, 7);
            if dayOfWeek > workDays
                flag = false;
                return;
            end
            
            % Check hour of day
            if hoursPerDay >= 24
                flag = true;
            elseif hoursPerDay <= 0
                flag = false;
            else
                % Assume operation starts at hour 6 (6 AM) and continues
                startHour = 6;
                endHour = startHour + hoursPerDay;
                
                if endHour <= 24
                    flag = (hourOfDay >= startHour) && (hourOfDay < endHour);
                else
                    % Wraps around midnight
                    flag = (hourOfDay >= startHour) || (hourOfDay < mod(endHour, 24));
                end
            end
        end

        function [phase, load] = determineCyclePhase(hourIdx, cycles, avgLoadFactor)
            %DETERMINECYCLEPHASE Determina fase del ciclo de trabajo.
            %   Uses deterministic assignment based on cycle fractions.
            
            fields = fieldnames(cycles);
            nPhases = numel(fields);
            
            % Use hour index to deterministically assign phase
            phaseIdx = mod(hourIdx, 100);  % 0-99
            
            cumProb = 0;
            for i = 1:nPhases
                fieldName = fields{i};
                prob = cycles.(fieldName) * 100;  % Convert to percentage
                
                if phaseIdx < (cumProb + prob)
                    phase = upper(fieldName);
                    
                    % Assign load based on phase
                    if contains(phase, 'FULL') || contains(phase, 'RUNNING')
                        load = avgLoadFactor;
                    elseif contains(phase, 'PARTIAL')
                        load = avgLoadFactor * 0.7;
                    elseif contains(phase, 'STANDBY')
                        load = 0.05;
                    elseif contains(phase, 'OFF')
                        load = 0;
                    else
                        load = avgLoadFactor;
                    end
                    return;
                end
                
                cumProb = cumProb + prob;
            end
            
            % Fallback to RUNNING
            phase = 'RUNNING';
            load = avgLoadFactor;
        end

        function mult = getSeasonalMultiplier(month, seasonalVar)
            %GETSEASONALMULTIPLIER Aplica variación estacional.
            %   month: 1-12
            %   seasonalVar: 'Alta', 'Moderada', 'Baja'
            
            if strcmp(seasonalVar, 'Alta')
                % Peak in summer (Dec-Feb), low in winter (Jun-Aug)
                % Southern hemisphere seasonality
                switch month
                    case {12, 1, 2}  % Summer
                        mult = 1.3;
                    case {3, 4, 11}  % Shoulder
                        mult = 1.0;
                    case {5, 6, 7, 8, 9, 10}  % Winter
                        mult = 0.8;
                    otherwise
                        mult = 1.0;
                end
            elseif strcmp(seasonalVar, 'Moderada')
                % Milder variation
                switch month
                    case {12, 1, 2}
                        mult = 1.15;
                    case {3, 4, 11}
                        mult = 1.0;
                    case {5, 6, 7, 8, 9, 10}
                        mult = 0.9;
                    otherwise
                        mult = 1.0;
                end
            else
                % Low or no seasonal variation
                mult = 1.0;
            end
        end

        function month = getHourMonth(dayOfYear)
            %GETHOURMONTH Convierte día del año a mes (1-12).
            %   Simplified: assumes 30.44 days per month on average.
            month = min(12, floor((dayOfYear - 1) / 30.44) + 1);
        end

    end

end
