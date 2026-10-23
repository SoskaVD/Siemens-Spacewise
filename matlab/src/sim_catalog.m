classdef sim_catalog
    %SIM_CATALOG Cargador del catálogo modular de equipos industriales.
    %   Autodescubrimiento por carpetas: cada máquina vive en
    %   machines/<CODE>/machine.json. Añadir una carpeta añade una máquina;
    %   eliminarla la quita del catálogo. Las carpetas cuyo nombre empieza
    %   con '_' o '.' se ignoran (p. ej. machines/_TEMPLATE/).
    %
    %   Ejemplo:
    %       machines = sim_catalog.load();
    %       fprintf('Loaded %d machines\n', height(machines));
    %
    %   Contrato: load() devuelve la tabla de 26 columnas esperada por
    %   sim_engine, sim_machine y sim_db.ensureMachines. machine_id se
    %   asigna secuencialmente (1..N) ordenando por machine_code ascendente.
    %   work_cycles (objeto JSON en machine.json) se re-serializa a la
    %   columna string work_cycles_json. 'active' omite -> 1 por defecto.
    %
    %   Seguridad:
    %       - Sin eval()
    %       - Validación de tipos, rangos y claves requeridas por módulo
    %         (errores SIM:ModuleInvalid que nombran la carpeta/archivo)
    %       - machine_code debe cumplir ^[A-Z]{2,10}-\d{1,5}$ (contrato backend)

    methods (Static)

        function machines = load(machinesDir)
            %LOAD Descubre y valida los módulos de máquina del catálogo.
            %   machines = sim_catalog.load() usa simulacion_params.MACHINES_DIR.
            %   machines = sim_catalog.load(dir) usa un directorio específico.
            if nargin < 1 || isempty(machinesDir)
                machinesDir = simulacion_params.MACHINES_DIR;
            end

            if ~exist(machinesDir, 'dir')
                error('SIM:CatalogNotFound', ...
                    'Machines directory not found: %s', machinesDir);
            end

            folders = sim_catalog.discoverFolders(machinesDir);
            if isempty(folders)
                error('SIM:CatalogNotFound', ...
                    'No machine modules found in %s (folders starting with ''_'' or ''.'' are skipped)', ...
                    machinesDir);
            end

            % Cargar y validar cada módulo
            modules = cell(size(folders));
            for k = 1:numel(folders)
                modules{k} = sim_catalog.loadModule(machinesDir, folders{k});
            end

            % Ordenar por machine_code y asignar machine_id secuencial
            codes = cellfun(@(m) m.machine_code, modules, 'UniformOutput', false);
            [sortedCodes, sortIdx] = sort(codes);
            if any(strcmp(sortedCodes(1:end-1), sortedCodes(2:end)))
                dupIdx = find(strcmp(sortedCodes(1:end-1), sortedCodes(2:end)));
                error('SIM:ModuleInvalid', ...
                    'Duplicate machine_code "%s" found in the machines directory', ...
                    sortedCodes{dupIdx(1)});
            end
            modules = modules(sortIdx);

            machines = sim_catalog.buildTable(modules);
        end

    end

    methods (Static, Access = private)

        function folders = discoverFolders(machinesDir)
            %DISCOVERFOLDERS Lista subcarpetas candidatas a módulo.
            %   Omite entradas cuyo nombre empieza con '_' o '.'
            %   (incluidos '.' y '..'), de modo que _TEMPLATE/ y las
            %   carpetas ocultas nunca se cargan como máquinas.
            entries = dir(machinesDir);
            entries = entries([entries.isdir]);
            allNames = {entries.name};
            keep = false(size(allNames));
            for k = 1:numel(allNames)
                name = allNames{k};
                keep(k) = ~isempty(name) && name(1) ~= '_' && name(1) ~= '.';
            end
            folders = allNames(keep);
        end

        function m = loadModule(machinesDir, folder)
            %LOADMODULE Lee y valida machines/<folder>/machine.json.
            modulePath = fullfile(machinesDir, folder);
            jsonPath = fullfile(modulePath, 'machine.json');

            if ~exist(jsonPath, 'file')
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s" is missing machine.json (expected %s)', ...
                    folder, jsonPath);
            end

            raw = fileread(jsonPath);
            try
                decoded = jsondecode(raw);
            catch ME
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": machine.json is not valid JSON (%s): %s', ...
                    folder, jsonPath, ME.message);
            end

            if ~isstruct(decoded) || numel(decoded) ~= 1
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": machine.json (%s) must contain a single JSON object', ...
                    folder, jsonPath);
            end

            m = sim_catalog.validateModule(decoded, folder, jsonPath);
        end

        function m = validateModule(s, folder, jsonPath)
            %VALIDATEMODULE Verifica claves, tipos y rangos del módulo.
            requiredFields = sim_catalog.requiredFields();
            present = fieldnames(s);
            missing = setdiff(requiredFields, present);
            if ~isempty(missing)
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": machine.json (%s) missing required field(s): %s', ...
                    folder, jsonPath, strjoin(missing, ', '));
            end

            m = s;

            % --- Campos de texto ---
            charFields = {'machine_code', 'name', 'category', 'manufacturer', ...
                'model', 'seasonal_variability', 'application', 'criticality', ...
                'dependencies', 'environmental_notes'};
            nonEmptyFields = {'machine_code', 'name', 'category', ...
                'seasonal_variability', 'criticality'};
            for i = 1:numel(charFields)
                f = charFields{i};
                if ~ischar(m.(f))
                    error('SIM:ModuleInvalid', ...
                        'Machine folder "%s": field "%s" in %s must be a string', ...
                        folder, f, jsonPath);
                end
                if any(strcmp(nonEmptyFields, f)) && isempty(m.(f))
                    error('SIM:ModuleInvalid', ...
                        'Machine folder "%s": field "%s" in %s must be non-empty', ...
                        folder, f, jsonPath);
                end
            end

            % machine_code: contrato del backend
            if isempty(regexp(m.machine_code, '^[A-Z]{2,10}-\d{1,5}$', 'once'))
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": machine_code "%s" does not match ^[A-Z]{2,10}-\\d{1,5}$ (%s)', ...
                    folder, m.machine_code, jsonPath);
            end

            % Enumeraciones de dominio
            if ~ismember(m.category, simulacion_params.CATEGORIES)
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": category "%s" is not one of %s (%s)', ...
                    folder, m.category, strjoin(simulacion_params.CATEGORIES, ', '), jsonPath);
            end
            if ~ismember(m.criticality, simulacion_params.CRITICALITY_LEVELS)
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": criticality "%s" is not one of %s (%s)', ...
                    folder, m.criticality, strjoin(simulacion_params.CRITICALITY_LEVELS, ', '), jsonPath);
            end
            if ~ismember(m.seasonal_variability, {'Alta', 'Moderada', 'Baja'})
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": seasonal_variability "%s" must be Alta, Moderada or Baja (%s)', ...
                    folder, m.seasonal_variability, jsonPath);
            end

            % --- Campos numéricos con rango ---
            numericFields = {'rated_power_kw', 'voltage_v', 'current_a', ...
                'power_factor', 'phases', 'thd_pct', 'hours_per_day', ...
                'days_per_week', 'load_factor', 'startup_time_s', ...
                'startup_multiplier', 'standby_pct', 'flexibility'};
            for i = 1:numel(numericFields)
                f = numericFields{i};
                sim_catalog.validateNumericField(m.(f), f, folder, jsonPath);
            end

            % active es opcional; defecto 1
            if ~isfield(m, 'active')
                m.active = 1;
            end
            sim_catalog.validateNumericField(m.active, 'active', folder, jsonPath);

            % --- work_cycles: objeto de fracciones [0,1] que suman ~1 ---
            if ~isstruct(m.work_cycles) || isempty(fieldnames(m.work_cycles))
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": work_cycles in %s must be a JSON object of state fractions', ...
                    folder, jsonPath);
            end
            wcNames = fieldnames(m.work_cycles);
            wcSum = 0;
            for i = 1:numel(wcNames)
                val = m.work_cycles.(wcNames{i});
                if ~isnumeric(val) || ~isscalar(val) || ~isfinite(val) || val < 0 || val > 1
                    error('SIM:ModuleInvalid', ...
                        'Machine folder "%s": work_cycles."%s" in %s must be a finite number in [0, 1]', ...
                        folder, wcNames{i}, jsonPath);
                end
                wcSum = wcSum + val;
            end
            if abs(wcSum - 1) > 0.02
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": work_cycles fractions in %s must sum to 1 (got %.4g)', ...
                    folder, jsonPath, wcSum);
            end
        end

        function names = requiredFields()
            %REQUIREDFIELDS Claves obligatorias de machine.json.
            names = {'machine_code', 'name', 'category', 'manufacturer', 'model', ...
                'rated_power_kw', 'voltage_v', 'current_a', 'power_factor', ...
                'phases', 'thd_pct', 'hours_per_day', 'days_per_week', ...
                'load_factor', 'seasonal_variability', 'work_cycles', ...
                'startup_time_s', 'startup_multiplier', 'standby_pct', ...
                'flexibility', 'application', 'criticality', 'dependencies', ...
                'environmental_notes'};
        end

        function validateNumericField(val, fieldName, folder, jsonPath)
            %VALIDATENUMERICFIELD Tipo, finiteza y rango por campo numérico.
            if ~isnumeric(val) || ~isscalar(val) || ~isfinite(val)
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": field "%s" in %s must be a finite numeric scalar', ...
                    folder, fieldName, jsonPath);
            end
            ok = true;
            switch fieldName
                case 'rated_power_kw'
                    ok = val > 0;
                case 'voltage_v'
                    ok = val > 0;
                case 'current_a'
                    ok = val >= 0;
                case 'power_factor'
                    ok = val > 0 && val <= 1;
                case 'phases'
                    ok = val == floor(val) && ismember(val, [1, 2, 3]);
                case 'thd_pct'
                    ok = val >= 0;
                case 'hours_per_day'
                    ok = val >= 0 && val <= 24;
                case 'days_per_week'
                    ok = val >= 0 && val <= 7;
                case 'load_factor'
                    ok = val >= 0 && val <= 1;
                case 'startup_time_s'
                    ok = val >= 0;
                case 'startup_multiplier'
                    ok = val >= 1;
                case 'standby_pct'
                    ok = val >= 0 && val <= 100;
                case {'flexibility', 'active'}
                    ok = val == floor(val) && ismember(val, [0, 1]);
                otherwise
                    ok = true;
            end
            if ~ok
                error('SIM:ModuleInvalid', ...
                    'Machine folder "%s": field "%s" in %s has invalid value %.6g', ...
                    folder, fieldName, jsonPath, val);
            end
        end

        function machines = buildTable(modules)
            %BUILDTABLE Construye la tabla-contrato de 26 columnas.
            n = numel(modules);

            machine_ids = (1:n)';
            codes = cell(n, 1);
            names = cell(n, 1);
            categories = cell(n, 1);
            manufacturers = cell(n, 1);
            models = cell(n, 1);
            powers = zeros(n, 1);
            voltages = zeros(n, 1);
            currents = zeros(n, 1);
            pfs = zeros(n, 1);
            phases = zeros(n, 1);
            thds = zeros(n, 1);
            hoursPerDay = zeros(n, 1);
            daysPerWeek = zeros(n, 1);
            loadFactors = zeros(n, 1);
            seasonalVars = cell(n, 1);
            workCyclesJson = cell(n, 1);
            startupTimes = zeros(n, 1);
            startupMults = zeros(n, 1);
            standbyPcts = zeros(n, 1);
            flexibilityFlags = zeros(n, 1);
            applications = cell(n, 1);
            criticalities = cell(n, 1);
            dependencies = cell(n, 1);
            envNotes = cell(n, 1);
            actives = ones(n, 1);

            for i = 1:n
                m = modules{i};
                codes{i} = m.machine_code;
                names{i} = m.name;
                categories{i} = m.category;
                manufacturers{i} = m.manufacturer;
                models{i} = m.model;
                powers(i) = m.rated_power_kw;
                voltages(i) = m.voltage_v;
                currents(i) = m.current_a;
                pfs(i) = m.power_factor;
                phases(i) = m.phases;
                thds(i) = m.thd_pct;
                hoursPerDay(i) = m.hours_per_day;
                daysPerWeek(i) = m.days_per_week;
                loadFactors(i) = m.load_factor;
                seasonalVars{i} = m.seasonal_variability;
                workCyclesJson{i} = char(jsonencode(m.work_cycles));
                startupTimes(i) = m.startup_time_s;
                startupMults(i) = m.startup_multiplier;
                standbyPcts(i) = m.standby_pct;
                flexibilityFlags(i) = m.flexibility;
                applications{i} = m.application;
                criticalities{i} = m.criticality;
                dependencies{i} = m.dependencies;
                envNotes{i} = m.environmental_notes;
                actives(i) = m.active;
            end

            % Tabla de salida idéntica al contrato histórico (26 columnas)
            machines = table();
            machines.machine_id = machine_ids;
            machines.machine_code = codes;
            machines.name = names;
            machines.category = categories;
            machines.manufacturer = manufacturers;
            machines.model = models;
            machines.rated_power_kw = powers;
            machines.voltage_v = voltages;
            machines.current_a = currents;
            machines.power_factor = pfs;
            machines.phases = int32(phases);
            machines.thd_pct = thds;
            machines.hours_per_day = hoursPerDay;
            machines.days_per_week = daysPerWeek;
            machines.load_factor = loadFactors;
            machines.seasonal_variability = seasonalVars;
            machines.work_cycles_json = workCyclesJson;
            machines.startup_time_s = startupTimes;
            machines.startup_multiplier = startupMults;
            machines.standby_pct = standbyPcts;
            machines.flexibility = int32(flexibilityFlags);
            machines.application = applications;
            machines.criticality = criticalities;
            machines.dependencies = dependencies;
            machines.environmental_notes = envNotes;
            machines.active = int32(actives);
        end

    end

end
