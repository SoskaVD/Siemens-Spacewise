%% migrate_catalog.m - Migración única: docs/CATALOGO_EQUIPOS.md -> machines/<CODE>/machine.json
% One-shot migration tool. Parses the legacy markdown catalog with the
% historical parser (kept here as local functions ONLY — it no longer runs
% at load time) and writes one machine module per machine into the folder
% catalog: machines/<CODE>/machine.json.
%
% Usage:
%   matlab -batch "run('matlab/scripts/migrate_catalog.m')"
%   (or run from anywhere: the script cd's to the repo root itself)
%
% Output contract:
%   - 110 folders machines/<CODE>/ each containing a machine.json
%   - Fields per machines/_TEMPLATE/_README.md; machine_id is NOT stored
%     (sim_catalog.load assigns it by sorted machine_code)
%   - work_cycles_json string column becomes a work_cycles JSON object
%   - Idempotent: re-running overwrites the generated files

% Resolve repo root from this script's location and cd there so that the
% relative paths in simulacion_params (CATALOG_PATH, MACHINES_DIR) resolve.
scriptDir = fileparts(mfilename('fullpath'));
rootDir = fullfile(scriptDir, '..', '..');
cd(rootDir);
rootDir = pwd;  % Canonicalize path after cd
addpath(fullfile(rootDir, 'matlab', 'src'));
addpath(fullfile(rootDir, 'matlab', 'config'));

catalogPath = simulacion_params.CATALOG_PATH;
machinesDir = simulacion_params.MACHINES_DIR;

if ~exist(catalogPath, 'file')
    error('SIM:CatalogNotFound', 'Legacy catalog file not found: %s', catalogPath);
end

fprintf('=== Migrando catálogo markdown a módulos por carpeta ===\n');
fprintf('Fuente: %s\nDestino: %s/<CODE>/machine.json\n\n', catalogPath, machinesDir);

content = fileread(catalogPath);

% Legacy pipeline (same logic the old sim_catalog.load() ran)
baseTable = parseCSVTable(content);
detailData = parseDetailedSections(content);
machines = mergeAndEnrich(baseTable, detailData);

n = height(machines);
fprintf('Máquinas parseadas: %d\n', n);

if ~exist(machinesDir, 'dir')
    mkdir(machinesDir);
end

written = 0;
for i = 1:n
    code = machines.machine_code{i};
    if isempty(regexp(code, '^[A-Z]{2,10}-\d{1,5}$', 'once'))
        error('SIM:ModuleInvalid', 'Machine code "%s" does not match backend contract', code);
    end

    % Build the module struct: all stored contract fields except machine_id,
    % with work_cycles_json re-expressed as a JSON object.
    s = struct();
    s.machine_code = code;
    s.name = machines.name{i};
    s.category = machines.category{i};
    s.manufacturer = machines.manufacturer{i};
    s.model = machines.model{i};
    s.rated_power_kw = machines.rated_power_kw(i);
    s.voltage_v = machines.voltage_v(i);
    s.current_a = machines.current_a(i);
    s.power_factor = machines.power_factor(i);
    s.phases = double(machines.phases(i));
    s.thd_pct = machines.thd_pct(i);
    s.hours_per_day = machines.hours_per_day(i);
    s.days_per_week = machines.days_per_week(i);
    s.load_factor = machines.load_factor(i);
    s.seasonal_variability = machines.seasonal_variability{i};
    if isempty(machines.work_cycles_json{i})
        s.work_cycles = struct('RUNNING', 1.0);
    else
        s.work_cycles = jsondecode(machines.work_cycles_json{i});
    end
    s.startup_time_s = machines.startup_time_s(i);
    s.startup_multiplier = machines.startup_multiplier(i);
    s.standby_pct = machines.standby_pct(i);
    s.flexibility = double(machines.flexibility(i));
    s.application = machines.application{i};
    s.criticality = machines.criticality{i};
    s.dependencies = machines.dependencies{i};
    s.environmental_notes = machines.environmental_notes{i};
    s.active = double(machines.active(i));

    % Guard: jsonencode would emit invalid JSON for NaN/Inf values
    numFields = {'rated_power_kw', 'voltage_v', 'current_a', 'power_factor', ...
        'phases', 'thd_pct', 'hours_per_day', 'days_per_week', 'load_factor', ...
        'startup_time_s', 'startup_multiplier', 'standby_pct', 'flexibility', 'active'};
    for f = numFields
        val = s.(f{1});
        if ~isfinite(val)
            error('SIM:ModuleInvalid', ...
                'Machine %s: numeric field %s is not finite; refusing to write invalid JSON', ...
                code, f{1});
        end
    end

    moduleDir = fullfile(machinesDir, code);
    if ~exist(moduleDir, 'dir')
        mkdir(moduleDir);
    end
    jsonStr = jsonencode(s, 'PrettyPrint', true);
    fid = fopen(fullfile(moduleDir, 'machine.json'), 'w');
    if fid < 0
        error('SIM:MigrationFailed', 'Could not write %s', fullfile(moduleDir, 'machine.json'));
    end
    fwrite(fid, [jsonStr, newline]);
    fclose(fid);
    written = written + 1;
end

fprintf('✓ Módulos escritos: %d en %s/\n', written, machinesDir);
fprintf('Verificación: sim_catalog.load() debe devolver %d máquinas.\n', n);

% -------------------------------------------------------------------------
% Local functions: legacy markdown parser, moved out of sim_catalog.m.
% This pipeline runs ONLY here, as a one-shot migration tool.
% -------------------------------------------------------------------------

function T = parseCSVTable(content)
    %PARSECXTABLE Extrae la tabla CSV resumen del markdown.
    %   La tabla CSV tiene formato pipe-delimited al final del archivo.

    % Find lines with machine data (start with HVAC-, COMP-, MOT-, etc.)
    rawLines = strsplit(content, newline);

    % Find the first data line (contains HVAC-001 or similar pattern)
    dataStartIdx = 0;
    for i = 1:numel(rawLines)
        line = strtrim(rawLines{i});
        % Check if line starts with a machine code pattern
        if regexp(line, '^(HVAC|COMP|MOT|BOMB|ILUM|LAB|MAN|SERV|AUX)-\d{3}\|')
            dataStartIdx = i;
            break;
        end
    end

    if dataStartIdx == 0
        error('SIM:CSVNotFound', 'Could not find CSV data table in catalog');
    end

    % Collect all data lines, joining broken lines (some have category split across lines)
    dataLines = {};
    accumulator = '';
    for i = dataStartIdx:numel(rawLines)
        line = strtrim(rawLines{i});
        if isempty(line), continue; end

        % Stop if we hit the closing code block marker
        if strcmp(line, '```')
            % Finalize the last accumulator before breaking
            if ~isempty(accumulator)
                fields = strsplit(accumulator, '|');
                if numel(fields) == 11
                    dataLines{end+1} = accumulator; %#ok<AGROW>
                end
            end
            break;
        end

        % Check if this is a new machine line (starts with code pattern)
        isNewMachine = ~isempty(regexp(line, '^(HVAC|COMP|MOT|BOMB|ILUM|LAB|MAN|TI|SERV|AUX)-\d{3}\|', 'once'));

        if isNewMachine && ~isempty(accumulator)
            % Previous accumulator is complete, add it
            fields = strsplit(accumulator, '|');
            if numel(fields) == 11
                dataLines{end+1} = accumulator; %#ok<AGROW>
            end
            accumulator = line;
        elseif isNewMachine
            % First machine line
            accumulator = line;
        else
            % Continuation line, append to accumulator
            accumulator = [accumulator, ' ', line];
        end
    end

    if isempty(dataLines)
        error('SIM:CSVNotFound', 'No valid CSV data lines found');
    end

    % Parse each line into fields
    nLines = numel(dataLines);
    codes = cell(nLines, 1);
    names = cell(nLines, 1);
    categories = cell(nLines, 1);
    powers = zeros(nLines, 1);
    voltages = zeros(nLines, 1);
    phases = zeros(nLines, 1);
    pfs = zeros(nLines, 1);
    hoursPerDay = zeros(nLines, 1);
    daysPerWeek = zeros(nLines, 1);
    loadFactors = zeros(nLines, 1);
    criticalities = cell(nLines, 1);

    for i = 1:nLines
        fields = strsplit(dataLines{i}, '|');
        if numel(fields) < 11
            warning('SIM:MalformedCSVLine', 'Line %d has %d fields, expected 11', i, numel(fields));
            continue;
        end

        codes{i} = strtrim(fields{1});
        names{i} = strtrim(fields{2});
        categories{i} = strtrim(fields{3});
        powers(i) = safeParseDouble(fields{4});
        voltages(i) = safeParseDouble(fields{5});
        phases(i) = safeParseDouble(fields{6});
        pfs(i) = safeParseDouble(fields{7});
        hoursPerDay(i) = safeParseDouble(fields{8});
        daysPerWeek(i) = safeParseDouble(fields{9});
        loadFactors(i) = safeParseDouble(fields{10});
        criticalities{i} = strtrim(fields{11});
    end

    % Remove any empty rows
    validRows = ~cellfun('isempty', codes);
    codes = codes(validRows);
    names = names(validRows);
    categories = categories(validRows);
    powers = powers(validRows);
    voltages = voltages(validRows);
    phases = phases(validRows);
    pfs = pfs(validRows);
    hoursPerDay = hoursPerDay(validRows);
    daysPerWeek = daysPerWeek(validRows);
    loadFactors = loadFactors(validRows);
    criticalities = criticalities(validRows);

    T = table(codes, names, categories, powers, voltages, phases, ...
        pfs, hoursPerDay, daysPerWeek, loadFactors, criticalities, ...
        'VariableNames', {'machine_code', 'name', 'raw_category', ...
        'rated_power_kw', 'voltage_v', 'phases', 'power_factor', ...
        'hours_per_day', 'days_per_week', 'load_factor', 'criticality'});
end

function details = parseDetailedSections(content)
    %PARSEDETAILEDSECTIONS Extrae datos detallados de las secciones markdown.
    %   Busca patrones ### CODE — Name y extrae specs, perfil, dinámica.

    % Find all section headers: ### CODE — Name
    headerPattern = '### ([A-Z]+-\d+)\s*[—-]\s*(.+)$';
    tokens = regexp(content, headerPattern, 'tokens', 'lineanchors');

    details = containers.Map('KeyType', 'char', 'ValueType', 'any');

    for t = 1:numel(tokens)
        code = strtrim(tokens{t}{1});
        name = strtrim(tokens{t}{2});

        % Extract section content (until next ### or ##)
        sectionStart = strfind(content, ['### ', code]);
        if isempty(sectionStart), continue; end
        sectionStart = sectionStart(1);

        % Find end of section
        remaining = content(sectionStart+4:end);
        nextHeader = regexp(remaining, '\n###\s+[A-Z]+-\d+', 'once');
        if isempty(nextHeader)
            nextHeader = regexp(remaining, '\n## [A-Z]', 'once');
        end
        if isempty(nextHeader)
            sectionContent = remaining;
        else
            sectionContent = remaining(1:nextHeader-1);
        end

        detail = struct();
        detail.name = name;

        % Extract manufacturer/model
        detail.manufacturer = '';
        detail.model = '';
        mfrMatch = regexp(sectionContent, ...
            'Fabricante/Modelo\s*\|\s*([^\|]+)', 'tokens', 'once');
        if ~isempty(mfrMatch)
            mfrStr = strtrim(mfrMatch{1});
            % Split manufacturer and model on first space
            spaceMatch = regexp(mfrStr, '^\s*(\S+)\s+(.*)$', 'tokens', 'once');
            if ~isempty(spaceMatch)
                detail.manufacturer = spaceMatch{1};
                detail.model = strtrim(spaceMatch{2});
            else
                detail.manufacturer = mfrStr;
            end
        end

        % Extract THD
        detail.thd_pct = NaN;
        thdMatch = regexp(sectionContent, ...
            'THD esperado\s*\|\s*([\d.]+)', 'tokens', 'once');
        if ~isempty(thdMatch)
            detail.thd_pct = safeParseDouble(thdMatch{1});
        end

        % Extract current
        detail.current_a = NaN;
        currentMatch = regexp(sectionContent, ...
            'Corriente nominal\s*\|\s*([\d.]+)', 'tokens', 'once');
        if ~isempty(currentMatch)
            detail.current_a = safeParseDouble(currentMatch{1});
        end

        % Extract startup behavior
        detail.startup_time_s = NaN;
        detail.startup_multiplier = NaN;
        startupMatch = regexp(sectionContent, ...
            'Arranque[:\s]*([\d.]+)\s*s[^,]*,\s*consumo\s*([\d.]+)', ...
            'tokens', 'once');
        if ~isempty(startupMatch)
            detail.startup_time_s = safeParseDouble(startupMatch{1});
            detail.startup_multiplier = safeParseDouble(startupMatch{2});
        else
            % Try alternative format
            startupMatch2 = regexp(sectionContent, ...
                '([0-9.]+)x\s*nominal\s*\((\d+)s', 'tokens', 'once');
            if ~isempty(startupMatch2)
                detail.startup_multiplier = safeParseDouble(startupMatch2{1});
                detail.startup_time_s = safeParseDouble(startupMatch2{2});
            else
                startupMatch3 = regexp(sectionContent, ...
                    '([0-9.]+)x\s*nominal', 'tokens', 'once');
                if ~isempty(startupMatch3)
                    detail.startup_multiplier = safeParseDouble(startupMatch3{1});
                end
            end
        end

        % Extract standby
        detail.standby_pct = NaN;
        standbyMatch = regexp(sectionContent, ...
            'Standby[:\s]*(\d+)\s*%', 'tokens', 'once');
        if ~isempty(standbyMatch)
            detail.standby_pct = safeParseDouble(standbyMatch{1});
        end

        % Extract flexibility
        detail.flexibility = 0;
        if contains(sectionContent, 'Flexibilidad') && ...
           (contains(sectionContent, 'sí') || contains(sectionContent, 'si'))
            detail.flexibility = 1;
        end

        % Extract seasonal variability
        detail.seasonal_variability = '';
        if contains(sectionContent, 'Variabilidad estacional')
            if contains(sectionContent, 'Alta') || contains(sectionContent, 'Muy alta') || contains(sectionContent, 'Muy dependiente')
                detail.seasonal_variability = 'Alta';
            elseif contains(sectionContent, 'Moderada') || contains(sectionContent, 'Moderado')
                detail.seasonal_variability = 'Moderada';
            elseif contains(sectionContent, 'Nula') || contains(sectionContent, 'Ninguna') || contains(sectionContent, 'Constante')
                detail.seasonal_variability = 'Baja';
            else
                detail.seasonal_variability = 'Moderada';
            end
        end

        % Extract work cycles as JSON
        detail.work_cycles_json = '';
        cycleMatch = regexp(sectionContent, ...
            'Ciclos de trabajo[:\s]*(.+?)(?:\n|$)', 'tokens', 'once');
        if ~isempty(cycleMatch)
            cycleText = strtrim(cycleMatch{1});
            % Extract percentages
            pctValues = regexp(cycleText, '(\d+)\s*%', 'tokens'); %#ok<NASGU>
            % Extract state names
            stateNames = regexp(cycleText, '([A-Za-z\s/]+?)\s*\((\d+)%\)', 'tokens');

            if ~isempty(stateNames)
                cycleStruct = struct();
                for s = 1:numel(stateNames)
                    stateName = strtrim(stateNames{s}{1});
                    statePct = str2double(stateNames{s}{2}) / 100;
                    safeName = regexprep(stateName, '[^a-zA-Z0-9]', '_');
                    cycleStruct.(safeName) = statePct;
                end
                detail.work_cycles_json = char(jsonencode(cycleStruct));
            end
        end

        % Extract application
        detail.application = '';
        appMatch = regexp(sectionContent, ...
            'Aplicaci[oó]n t[ií]pica[:\s]*(.+?)(?:\.|$)', 'tokens', 'once');
        if ~isempty(appMatch)
            detail.application = strtrim(appMatch{1});
        end

        % Extract dependencies
        detail.dependencies = '';
        depMatch = regexp(sectionContent, ...
            'Dependencias[:\s]*(.+?)(?:\n|$)', 'tokens', 'once');
        if ~isempty(depMatch)
            detail.dependencies = strtrim(depMatch{1});
        end

        % Extract environmental notes
        detail.environmental_notes = '';
        envMatch = regexp(sectionContent, ...
            'Condiciones ambientales[:\s]*(.+?)(?:\n|$)', 'tokens', 'once');
        if ~isempty(envMatch)
            detail.environmental_notes = strtrim(envMatch{1});
        end

        details(code) = detail;
    end
end

function machines = mergeAndEnrich(baseTable, detailData)
    %MERGEANDENRICH Combina tabla base con datos detallados y calcula derivados.
    n = height(baseTable);

    % Preallocate columns
    machine_ids = (1:n)';
    manufacturers = cell(n, 1);
    models = cell(n, 1);
    currents = zeros(n, 1);
    thds = zeros(n, 1);
    seasonalVars = cell(n, 1);
    workCyclesJson = cell(n, 1);
    startupTimes = zeros(n, 1);
    startupMults = ones(n, 1);
    standbyPcts = zeros(n, 1);
    flexibilityFlags = zeros(n, 1);
    applications = cell(n, 1);
    dependencies = cell(n, 1);
    envNotes = cell(n, 1);
    dbCategories = cell(n, 1);
    actives = ones(n, 1);

    for i = 1:n
        code = baseTable.machine_code{i};

        % Map category
        dbCategories{i} = mapCategory(baseTable.raw_category{i});

        % Lookup detailed data
        if detailData.isKey(code)
            d = detailData(code);
            manufacturers{i} = d.manufacturer;
            models{i} = d.model;

            if ~isnan(d.current_a)
                currents(i) = d.current_a;
            else
                currents(i) = computeCurrent( ...
                    baseTable.rated_power_kw(i), baseTable.voltage_v(i), ...
                    baseTable.power_factor(i), baseTable.phases(i));
            end

            if ~isnan(d.thd_pct)
                thds(i) = d.thd_pct;
            else
                thds(i) = defaultTHD(dbCategories{i});
            end

            seasonalVars{i} = d.seasonal_variability;
            if isempty(seasonalVars{i})
                seasonalVars{i} = defaultSeasonal(dbCategories{i});
            end

            workCyclesJson{i} = d.work_cycles_json;
            if isempty(workCyclesJson{i})
                workCyclesJson{i} = defaultWorkCycles( ...
                    baseTable.load_factor(i));
            end

            if ~isnan(d.startup_time_s)
                startupTimes(i) = d.startup_time_s;
            else
                startupTimes(i) = defaultStartupTime(dbCategories{i});
            end

            if ~isnan(d.startup_multiplier)
                startupMults(i) = d.startup_multiplier;
            else
                startupMults(i) = defaultStartupMult(dbCategories{i});
            end

            if ~isnan(d.standby_pct)
                standbyPcts(i) = d.standby_pct;
            end

            flexibilityFlags(i) = d.flexibility;
            applications{i} = d.application;
            dependencies{i} = d.dependencies;
            envNotes{i} = d.environmental_notes;
        else
            % No detailed data: use defaults
            manufacturers{i} = '';
            models{i} = '';
            currents(i) = computeCurrent( ...
                baseTable.rated_power_kw(i), baseTable.voltage_v(i), ...
                baseTable.power_factor(i), baseTable.phases(i));
            thds(i) = defaultTHD(dbCategories{i});
            seasonalVars{i} = defaultSeasonal(dbCategories{i});
            workCyclesJson{i} = defaultWorkCycles( ...
                baseTable.load_factor(i));
            startupTimes(i) = defaultStartupTime(dbCategories{i});
            startupMults(i) = defaultStartupMult(dbCategories{i});
            applications{i} = '';
            dependencies{i} = '';
            envNotes{i} = '';
        end
    end

    % Build output table matching DB schema
    machines = table();
    machines.machine_id = machine_ids;
    machines.machine_code = baseTable.machine_code;
    machines.name = baseTable.name;
    machines.category = dbCategories;
    machines.manufacturer = manufacturers;
    machines.model = models;
    machines.rated_power_kw = baseTable.rated_power_kw;
    machines.voltage_v = baseTable.voltage_v;
    machines.current_a = currents;
    machines.power_factor = baseTable.power_factor;
    machines.phases = int32(baseTable.phases);
    machines.thd_pct = thds;
    machines.hours_per_day = baseTable.hours_per_day;
    machines.days_per_week = baseTable.days_per_week;
    machines.load_factor = baseTable.load_factor;
    machines.seasonal_variability = seasonalVars;
    machines.work_cycles_json = workCyclesJson;
    machines.startup_time_s = startupTimes;
    machines.startup_multiplier = startupMults;
    machines.standby_pct = standbyPcts;
    machines.flexibility = int32(flexibilityFlags);
    machines.application = applications;
    machines.criticality = baseTable.criticality;
    machines.dependencies = dependencies;
    machines.environmental_notes = envNotes;
    machines.active = int32(actives);
end

function val = safeParseDouble(str)
    %SAFEPARSEDOUBLE Parsea un string a double, devuelve NaN si falla.
    str = strtrim(str);
    % Remove unit suffixes and annotations
    str = regexprep(str, '\s*(kW|kw|V|A|%|h|s|d[ií]a|seg|segundos).*$', '', 'once');
    str = regexprep(str, '[^\d.\-eE+]', '');
    if isempty(str)
        val = NaN;
    else
        val = str2double(str);
    end
end

function cat = mapCategory(rawCat)
    %MAPCATEGORY Mapea categoría del CSV a categoría de la DB.
    rawLower = lower(rawCat);
    if contains(rawLower, 'hvac')
        cat = 'HVAC';
    elseif contains(rawLower, 'compresor') || contains(rawLower, 'neumatica') || contains(rawLower, 'neumática')
        cat = 'Compresores';
    elseif contains(rawLower, 'motor')
        cat = 'Motores';
    elseif contains(rawLower, 'bomba') || contains(rawLower, 'hidraulica') || contains(rawLower, 'hidráulica')
        cat = 'Bombas';
    elseif contains(rawLower, 'iluminac')
        cat = 'Iluminacion';
    elseif contains(rawLower, 'laboratorio')
        cat = 'Laboratorios';
    elseif contains(rawLower, 'manufactura')
        cat = 'Manufactura';
    elseif contains(rawLower, 'servidor') || ~isempty(regexp(rawLower, '\bti\b', 'once'))
        cat = 'TI';
    elseif contains(rawLower, 'auxiliar')
        cat = 'Auxiliares';
    else
        cat = 'Auxiliares';  % fallback
    end
end

function current = computeCurrent(power_kw, voltage_v, pf, phases)
    %COMPUTECURRENT Calcula corriente nominal desde potencia.
    if voltage_v <= 0 || pf <= 0
        current = 0;
        return;
    end
    power_w = power_kw * 1000;
    if phases >= 3
        current = power_w / (sqrt(3) * voltage_v * pf);
    else
        current = power_w / (voltage_v * pf);
    end
end

function thd = defaultTHD(category)
    %DEFAULTTHD Devuelve THD por defecto según categoría.
    switch category
        case 'HVAC'
            thd = 10.0;
        case 'Compresores'
            thd = 5.0;
        case 'Motores'
            thd = 5.0;
        case 'Bombas'
            thd = 3.0;
        case 'Iluminacion'
            thd = 10.0;
        case 'Laboratorios'
            thd = 5.0;
        case 'Manufactura'
            thd = 10.0;
        case 'TI'
            thd = 5.0;
        otherwise
            thd = 5.0;
    end
end

function sv = defaultSeasonal(category)
    %DEFAULTSEASONAL Devuelve variabilidad estacional por defecto.
    switch category
        case 'HVAC'
            sv = 'Alta';
        case 'Compresores'
            sv = 'Baja';
        case 'Motores'
            sv = 'Baja';
        case 'Bombas'
            sv = 'Baja';
        case 'Iluminacion'
            sv = 'Moderada';
        case 'Laboratorios'
            sv = 'Baja';
        case 'Manufactura'
            sv = 'Baja';
        case 'TI'
            sv = 'Baja';
        otherwise
            sv = 'Baja';
    end
end

function json = defaultWorkCycles(loadFactor)
    %DEFAULTWORKCYCLES Genera JSON de ciclos de trabajo por defecto.
    running = min(loadFactor * 1.2, 1.0);
    standby = 1.0 - running;
    cycleStruct = struct('RUNNING', running, 'STANDBY', standby);
    json = char(jsonencode(cycleStruct));
end

function t = defaultStartupTime(category)
    %DEFAULTSTARTUPTIME Tiempo de arranque por defecto (segundos).
    switch category
        case 'HVAC'
            t = 30;
        case 'Compresores'
            t = 10;
        case 'Motores'
            t = 10;
        case 'Bombas'
            t = 5;
        case 'Iluminacion'
            t = 1;
        case 'Laboratorios'
            t = 5;
        case 'Manufactura'
            t = 10;
        case 'TI'
            t = 2;
        otherwise
            t = 5;
    end
end

function m = defaultStartupMult(category)
    %DEFAULTSTARTUPMULT Multiplicador de arranque por defecto.
    switch category
        case 'HVAC'
            m = 4.0;
        case 'Compresores'
            m = 5.0;
        case 'Motores'
            m = 5.0;
        case 'Bombas'
            m = 5.0;
        case 'Iluminacion'
            m = 1.5;
        case 'Laboratorios'
            m = 1.5;
        case 'Manufactura'
            m = 2.0;
        case 'TI'
            m = 1.2;
        otherwise
            m = 3.0;
    end
end
