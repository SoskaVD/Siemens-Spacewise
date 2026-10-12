classdef sim_db
    %SIM_DB Capa de persistencia SQLite para el simulador de maquinaria.
    %   Proporciona métodos para crear el esquema, insertar datos y consultar
    %   la base de datos spacewise.db. Todas las operaciones usan sqlwrite
    %   para inserciones batch y escapeSQL para consultas SELECT.
    %
    %   Ejemplo:
    %       conn = sim_db.init('data/spacewise.db');
    %       sim_db.insertMachines(conn, machines_table);
    %       sim_db.close(conn);

    methods (Static)

        function conn = open(dbPath, createFlag)
            %OPEN Abre (y opcionalmente crea) la base SQLite.
            %   conn = sim_db.open(dbPath)         abre existente.
            %   conn = sim_db.open(dbPath, true)   crea si no existe.
            if nargin < 2 || isempty(createFlag)
                createFlag = false;
            end
            simulacion_params.validateDbPath(dbPath);
            
            % Ensure parent directory exists
            parentDir = fileparts(dbPath);
            if ~isempty(parentDir) && ~exist(parentDir, 'dir')
                mkdir(parentDir);
            end
            
            if createFlag && ~exist(dbPath, 'file')
                conn = sqlite(dbPath, 'create');
            else
                conn = sqlite(dbPath);
            end
        end

        function conn = init(dbPath)
            %INIT Crea la base y ejecuta el esquema SQL (idempotente).
            %   Lee el schema desde data/schema_simulator.sql.
            if exist(dbPath, 'file')
                delete(dbPath);
            end
            conn = sqlite(dbPath, 'create');
            sim_db.createSchema(conn);
        end

        function close(conn)
            %CLOSE Cierra la conexión si está abierta.
            if ~isempty(conn) && conn.isopen
                conn.close();
            end
        end

        function createSchema(conn)
            %CREATESCHEMA Ejecuta el DDL desde el archivo schema_simulator.sql.
            schemaPath = simulacion_params.SCHEMA_PATH;
            if ~exist(schemaPath, 'file')
                error('SIM:SchemaNotFound', 'Schema file not found: %s', schemaPath);
            end
            
            schemaContent = fileread(schemaPath);
            statements = sim_db.parseSQL(schemaContent);
            
            for k = 1:numel(statements)
                try
                    conn.execute(statements{k});
                catch ME
                    warning('SIM:SchemaError', 'Error executing schema statement %d: %s', k, ME.message);
                end
            end
        end

        function insertMachine(conn, m)
            %INSERTMACHINE Inserta una máquina individual en la tabla machines.
            %   m es un struct con los campos del catálogo.
            if isempty(m), return; end
            
            T = sim_db.machineToTable(m);
            sqlwrite(conn, 'machines', T);
        end

        function insertMachines(conn, machines)
            %INSERTMACHINES Inserta batch de máquinas desde un table o struct array.
            if isempty(machines), return; end
            
            if istable(machines)
                T = machines;
            else
                T = sim_db.machinesToTable(machines);
            end
            
            sqlwrite(conn, 'machines', T);
        end

        function n = ensureMachines(conn, machines)
            %ENSUREMACHINES Carga el catálogo en la tabla machines si está vacía.
            %   Ningún script del pipeline llenaba esta tabla, por lo que el
            %   backend (JOIN machines) y los análisis por categoría/criticidad
            %   quedaban sin datos. Es idempotente: si ya hay máquinas no hace nada.
            %   n = cantidad de máquinas insertadas (0 si ya existían).
            n = 0;
            r = conn.fetch('SELECT COUNT(*) AS cnt FROM machines');
            if r.cnt == 0
                sim_db.insertMachines(conn, machines);
                n = height(machines);
            end
        end

        function sim_id = insertSimulation(conn, code, name, desc, seed)
            %INSERTSIMULATION Crea registro de simulación y devuelve su ID.
            %   Si el código ya existe, agrega sufijo de versión automáticamente.
            if nargin < 5 || isempty(seed), seed = simulacion_params.DEFAULT_SEED; end
            if nargin < 4 || isempty(desc), desc = ''; end
            
            % Generate unique code if it already exists
            uniqueCode = code;
            version = 1;
            while true
                sqlCheck = sprintf('SELECT COUNT(*) as cnt FROM simulations WHERE simulation_code = ''%s''', ...
                    sim_db.escapeSQL(uniqueCode));
                result = conn.fetch(sqlCheck);
                if result.cnt == 0
                    break;
                end
                version = version + 1;
                uniqueCode = sprintf('%s-v%d', code, version);
            end
            
            % Use safe escaping for INSERT
            sql = sprintf(...
                ['INSERT INTO simulations (simulation_code, name, description, ' ...
                 'engine_version, start_time, status, random_seed) ' ...
                 'VALUES (''%s'', ''%s'', ''%s'', ''%s'', datetime(''now''), ''RUNNING'', %d)'], ...
                sim_db.escapeSQL(uniqueCode), sim_db.escapeSQL(name), ...
                sim_db.escapeSQL(desc), simulacion_params.ENGINE_VERSION, seed);
            conn.execute(sql);
            sim_id = sim_db.lastInsertId(conn);
        end

        function updateSimulationStatus(conn, sim_id, status, logtext)
            %UPDATESIMULATIONSTATUS Actualiza estado y log de la simulación.
            if nargin < 4 || isempty(logtext), logtext = ''; end
            
            if strcmp(status, 'COMPLETED') || strcmp(status, 'FAILED')
                sql = sprintf(...
                    ['UPDATE simulations SET status=''%s'', end_time=datetime(''now''), ' ...
                     'log=''%s'' WHERE simulation_id=%d'], ...
                    sim_db.escapeSQL(status), sim_db.escapeSQL(logtext), sim_id);
            else
                sql = sprintf(...
                    'UPDATE simulations SET status=''%s'', log=''%s'' WHERE simulation_id=%d', ...
                    sim_db.escapeSQL(status), sim_db.escapeSQL(logtext), sim_id);
            end
            conn.execute(sql);
        end

        function updateSimulationCounts(conn, sim_id, total_machines, total_hours)
            %UPDATESIMULATIONCOUNTS Actualiza contadores de la simulación.
            if nargin < 4, total_hours = simulacion_params.HOURS_PER_YEAR; end
            sql = sprintf(...
                ['UPDATE simulations SET total_machines=%d, total_hours=%d ' ...
                 'WHERE simulation_id=%d'], ...
                total_machines, total_hours, sim_id);
            conn.execute(sql);
        end

        function insertMeasurements(conn, sim_id, machine_id, measurements)
            %INSERTMEASUREMENTS Guarda mediciones horarias de una máquina.
            %   measurements es un table con columnas: ts, hour_index,
            %   active_power_kw, energy_kwh, load_factor, operation_state, cycle_phase
            if isempty(measurements) || height(measurements) == 0, return; end
            
            % Add FK columns
            measurements.simulation_id = repmat(int32(sim_id), height(measurements), 1);
            measurements.machine_id = repmat(int32(machine_id), height(measurements), 1);
            
            % Reorder to match schema
            cols = {'measurement_id', 'simulation_id', 'machine_id', 'ts', ...
                    'hour_index', 'active_power_kw', 'energy_kwh', 'load_factor', ...
                    'power_factor', 'current_a', 'operation_state', 'cycle_phase', ...
                    'thd_pct', 'voltage_v'};
            
            % Add optional columns if missing
            if ~ismember('power_factor', measurements.Properties.VariableNames)
                measurements.power_factor = NaN(height(measurements), 1);
            end
            if ~ismember('current_a', measurements.Properties.VariableNames)
                measurements.current_a = NaN(height(measurements), 1);
            end
            if ~ismember('thd_pct', measurements.Properties.VariableNames)
                measurements.thd_pct = NaN(height(measurements), 1);
            end
            if ~ismember('voltage_v', measurements.Properties.VariableNames)
                measurements.voltage_v = NaN(height(measurements), 1);
            end
            
            % Remove measurement_id (autoincrement)
            if ismember('measurement_id', measurements.Properties.VariableNames)
                measurements.measurement_id = [];
            end
            
            % Ensure correct column order (only include columns that exist in schema)
            desiredOrder = {'simulation_id', 'machine_id', 'ts', 'hour_index', ...
                'active_power_kw', 'energy_kwh', 'load_factor', 'power_factor', ...
                'current_a', 'operation_state', 'cycle_phase', 'thd_pct', 'voltage_v'};
            measurements = measurements(:, desiredOrder);
            
            % Batch insert in chunks for performance
            batchSize = simulacion_params.BATCH_SIZE;
            nRows = height(measurements);
            for startIdx = 1:batchSize:nRows
                endIdx = min(startIdx + batchSize - 1, nRows);
                chunk = measurements(startIdx:endIdx, :);
                sqlwrite(conn, 'machine_measurements', chunk);
            end
        end

        function insertHourlyTotals(conn, sim_id, totals)
            %INSERTHOURLYTOTALS Guarda totales horarios agregados.
            if isempty(totals) || height(totals) == 0, return; end
            
            totals.simulation_id = repmat(int32(sim_id), height(totals), 1);
            
            if ismember('total_id', totals.Properties.VariableNames)
                totals.total_id = [];
            end
            
            desiredOrder = {'simulation_id', 'ts', 'hour_index', ...
                'total_power_kw', 'total_energy_kwh', ...
                'hvac_power_kw', 'compressors_power_kw', 'motors_power_kw', ...
                'pumps_power_kw', 'lighting_power_kw', 'lab_power_kw', ...
                'manufacturing_power_kw', 'it_power_kw', 'auxiliary_power_kw', ...
                'machine_count', 'avg_load_factor', 'peak_power_kw', 'peak_machine_id'};
            
            % Ensure all columns exist
            for i = 1:numel(desiredOrder)
                col = desiredOrder{i};
                if ~ismember(col, totals.Properties.VariableNames)
                    if contains(col, '_power_kw')
                        totals.(col) = zeros(height(totals), 1);
                    elseif strcmp(col, 'machine_count')
                        totals.(col) = int32(zeros(height(totals), 1));
                    elseif strcmp(col, 'avg_load_factor')
                        totals.(col) = NaN(height(totals), 1);
                    elseif strcmp(col, 'peak_power_kw')
                        totals.(col) = NaN(height(totals), 1);
                    elseif strcmp(col, 'peak_machine_id')
                        totals.(col) = int32(NaN(height(totals), 1));
                    end
                end
            end
            
            totals = totals(:, desiredOrder);
            
            batchSize = simulacion_params.BATCH_SIZE;
            nRows = height(totals);
            for startIdx = 1:batchSize:nRows
                endIdx = min(startIdx + batchSize - 1, nRows);
                chunk = totals(startIdx:endIdx, :);
                sqlwrite(conn, 'hourly_totals', chunk);
            end
        end

        function insertSimulationResults(conn, sim_id, results)
            %INSERTSIMULATIONRESULTS Guarda KPIs globales de la simulación.
            %   results es un struct con campos que coinciden con simulation_results.
            
            % Convert numeric arrays to JSON strings where needed
            results.simulation_id = sim_id;
            
            % Build a 1-row table
            fieldNames = fieldnames(results);
            T = table('Size', [1, numel(fieldNames)], 'VariableTypes', ...
                cell(1, numel(fieldNames)), 'VariableNames', fieldNames);
            for i = 1:numel(fieldNames)
                val = results.(fieldNames{i});
                if ischar(val) || isstring(val)
                    T.(fieldNames{i}) = {char(val)};
                elseif isnumeric(val)
                    T.(fieldNames{i}) = val;
                else
                    T.(fieldNames{i}) = {char(jsonencode(val))};
                end
            end
            
            if ismember('result_id', T.Properties.VariableNames)
                T.result_id = [];
            end
            
            sqlwrite(conn, 'simulation_results', T);
        end

        function insertMachineResults(conn, sim_id, machineResults)
            %INSERTMACHINERESULTS Guarda KPIs por máquina.
            %   machineResults es un table con una fila por máquina.
            if isempty(machineResults) || height(machineResults) == 0, return; end
            
            machineResults.simulation_id = repmat(int32(sim_id), height(machineResults), 1);
            
            if ismember('machine_result_id', machineResults.Properties.VariableNames)
                machineResults.machine_result_id = [];
            end
            
            % Move simulation_id to front
            machineResults = movevars(machineResults, 'simulation_id', 'Before', 1);
            
            batchSize = simulacion_params.BATCH_SIZE;
            nRows = height(machineResults);
            for startIdx = 1:batchSize:nRows
                endIdx = min(startIdx + batchSize - 1, nRows);
                chunk = machineResults(startIdx:endIdx, :);
                sqlwrite(conn, 'machine_results', chunk);
            end
        end

        function T = query(conn, sql)
            %QUERY Ejecuta una consulta SELECT y devuelve una tabla.
            %   Las consultas SELECT no aceptan input del usuario sin escapar.
            T = conn.fetch(sql);
        end

        function id = lastInsertId(conn)
            %LASTINSERTID Devuelve el último rowid insertado.
            r = conn.fetch('SELECT last_insert_rowid() AS id');
            id = r.id;
        end

    end

    methods (Static, Access = private)

        function statements = parseSQL(content)
            %PARSESQL Parsea contenido SQL en sentencias individuales.
            %   Ignora comentarios (-- y /* */) y líneas vacías.
            lines = strsplit(content, newline);
            cleanLines = {};
            inBlockComment = false;
            
            for i = 1:numel(lines)
                line = strtrim(lines{i});
                
                % Handle block comments
                if inBlockComment
                    if contains(line, '*/')
                        inBlockComment = false;
                        line = strtrim(line(strfind(line, '*/')+2:end));
                    else
                        continue;
                    end
                end
                
                if startsWith(line, '/*')
                    if contains(line, '*/')
                        line = strtrim(line(strfind(line, '*/')+2:end));
                    else
                        inBlockComment = true;
                        continue;
                    end
                end
                
                % Skip line comments and empty lines
                if startsWith(line, '--') || isempty(line)
                    continue;
                end
                
                % Remove inline comments
                commentPos = strfind(line, '--');
                if ~isempty(commentPos)
                    line = strtrim(line(1:commentPos(1)-1));
                end
                
                if ~isempty(line)
                    cleanLines{end+1} = line; %#ok<AGROW>
                end
            end
            
            % Join and split by semicolons
            fullSQL = strjoin(cleanLines, ' ');
            rawStatements = strsplit(fullSQL, ';');
            
            statements = {};
            for i = 1:numel(rawStatements)
                stmt = strtrim(rawStatements{i});
                if ~isempty(stmt)
                    statements{end+1} = stmt; %#ok<AGROW>
                end
            end
        end

        function T = machineToTable(m)
            %MACHINETOTABLE Convierte un struct de máquina a table de 1 fila.
            T = sim_db.machinesToTable(struct2cell(m));
            % Convert cell array of structs back
            if iscell(m)
                T = sim_db.machinesToTable(m);
            end
        end

        function T = machinesToTable(machines)
            %MACHINESTOTABLE Convierte struct array o cell a table para SQL.
            if isstruct(machines) && ~isscalar(machines)
                machines = struct2cell(machines)';
            end
            
            % Expect cell array of structs or a single struct
            if iscell(machines) && isstruct(machines{1})
                fields = fieldnames(machines{1});
                nFields = numel(fields);
                nRows = numel(machines);
                
                data = cell(nRows, nFields);
                for i = 1:nRows
                    for j = 1:nFields
                        val = machines{i}.(fields{j});
                        if ischar(val) || isstring(val)
                            data{i,j} = char(val);
                        elseif isnumeric(val)
                            data{i,j} = val;
                        elseif islogical(val)
                            data{i,j} = int32(val);
                        elseif isempty(val)
                            data{i,j} = '';
                        else
                            data{i,j} = char(jsonencode(val));
                        end
                    end
                end
                
                T = cell2table(data, 'VariableNames', fields);
            elseif isstruct(machines) && isscalar(machines)
                T = struct2table(machines);
            else
                T = machines;
            end
        end

    end

    methods (Static, Access = public)

        function s = escapeSQL(s)
            %ESCAPESQL Escapa comillas simples para SQLite.
            if isstring(s)
                s = char(s);
            end
            s = strrep(s, "'", "''");
        end

    end

end
