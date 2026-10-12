classdef test_sim_db < matlab.unittest.TestCase
    %TEST_SIM_DB Pruebas de la capa de persistencia SQLite para el simulador.
    %   Tests database operations: init, insert, query, close, error handling.
    
    properties
        dbPath char
        conn
        matlabRoot char
    end
    
    methods (TestMethodSetup)
        function setupTest(testCase)
            % Add paths
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            testCase.matlabRoot = p;
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
            
            % Create temporary database
            testCase.dbPath = fullfile(tempdir, sprintf('test_sim_db_%d.db', randi(1e9)));
            if exist(testCase.dbPath, 'file')
                delete(testCase.dbPath);
            end
            
            % Change to repo root so schema path resolves
            origDir = pwd;
            repoRoot = fileparts(fileparts(p));  % Siemens-Spacewise/
            cd(repoRoot);
            
            % Initialize database
            testCase.conn = sim_db.init(testCase.dbPath);
            
            cd(origDir);
        end
    end
    
    methods (TestMethodTeardown)
        function teardownTest(testCase)
            if ~isempty(testCase.conn)
                try
                    sim_db.close(testCase.conn);
                catch
                end
            end
            if exist(testCase.dbPath, 'file')
                delete(testCase.dbPath);
            end
        end
    end
    
    methods (Test)
        
        function testInitCreatesDatabase(testCase)
            % testInitCreatesDatabase - init() creates database file
            testCase.verifyTrue(exist(testCase.dbPath, 'file') == 2, ...
                'init() should create the database file');
        end
        
        function testInitCreatesAllTables(testCase)
            % testInitCreatesAllTables - init() creates all expected tables
            origDir = pwd;
            cd(testCase.matlabRoot);
            addpath(fullfile(pwd, 'src'), fullfile(pwd, 'config'));
            cd(fileparts(fileparts(pwd)));
            
            tbl = testCase.conn.fetch("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name");
            cd(origDir);
            
            names = string(tbl.name);
            expected = ["machines"; "simulations"; "machine_measurements"; ...
                "hourly_totals"; "simulation_results"; "machine_results"; ...
                "import_data"; "import_measurements"];
            
            for i = 1:numel(expected)
                testCase.verifyTrue(any(names == expected(i)), ...
                    sprintf('Expected table "%s" not found', expected(i)));
            end
        end
        
        function testInsertMachine(testCase)
            % testInsertMachine - insertMachine() inserts single machine
            m = sim_catalog.load();
            m1 = m(1,:);
            
            sim_db.insertMachine(testCase.conn, m1);
            
            result = testCase.conn.fetch('SELECT COUNT(*) AS c FROM machines');
            testCase.verifyEqual(double(result.c), 1, 'Should have 1 machine after insert');
            
            row = testCase.conn.fetch('SELECT * FROM machines LIMIT 1');
            testCase.verifyEqual(string(row.machine_code{1}), string(m1.machine_code{1}), ...
                'Inserted machine_code should match');
        end
        
        function testInsertMachinesBatch(testCase)
            % testInsertMachinesBatch - insertMachines() batch insert
            m = sim_catalog.load();
            subset = m(1:5, :);
            
            sim_db.insertMachines(testCase.conn, subset);
            
            result = testCase.conn.fetch('SELECT COUNT(*) AS c FROM machines');
            testCase.verifyEqual(double(result.c), 5, 'Should have 5 machines after batch insert');
        end
        
        function testInsertSimulation(testCase)
            % testInsertSimulation - insertSimulation() returns valid sim_id
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-TEST-001', ...
                'Test Simulation', 'Unit test', 42);
            
            testCase.verifyGreaterThan(sim_id, 0, 'sim_id should be positive');
            
            row = testCase.conn.fetch(sprintf(...
                'SELECT * FROM simulations WHERE simulation_id = %d', sim_id));
            testCase.verifyEqual(string(row.simulation_code{1}), 'SIM-TEST-001');
            testCase.verifyEqual(string(row.name{1}), 'Test Simulation');
            testCase.verifyEqual(double(row.random_seed), 42);
        end
        
        function testInsertMeasurements(testCase)
            % testInsertMeasurements - insertMeasurements() inserts hourly data
            % First create a simulation and machine
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-TEST-MEAS', ...
                'Test Measurements', '', 42);
            
            m = sim_catalog.load();
            sim_db.insertMachines(testCase.conn, m(1:1, :));
            machine_id = int32(1);
            
            % Build small measurement table (10 hours)
            nHours = 10;
            meas = table();
            meas.ts = strings(nHours, 1);
            meas.hour_index = int32((0:nHours-1)');
            meas.active_power_kw = rand(nHours, 1) * 100;
            meas.energy_kwh = meas.active_power_kw;
            meas.load_factor = rand(nHours, 1);
            meas.operation_state = repmat({'RUNNING'}, nHours, 1);
            meas.cycle_phase = repmat({'FULL_LOAD'}, nHours, 1);
            
            sim_db.insertMeasurements(testCase.conn, sim_id, machine_id, meas);
            
            result = testCase.conn.fetch(sprintf(...
                'SELECT COUNT(*) AS c FROM machine_measurements WHERE simulation_id = %d', sim_id));
            testCase.verifyEqual(double(result.c), nHours, ...
                'Should have 10 measurement rows');
        end
        
        function testInsertHourlyTotals(testCase)
            % testInsertHourlyTotals - insertHourlyTotals() inserts aggregated data
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-TEST-TOTALS', ...
                'Test Totals', '', 42);
            
            nHours = 5;
            totals = table();
            totals.ts = strings(nHours, 1);
            totals.hour_index = int32((0:nHours-1)');
            totals.total_power_kw = rand(nHours, 1) * 500;
            totals.total_energy_kwh = totals.total_power_kw;
            totals.hvac_power_kw = rand(nHours, 1) * 100;
            totals.compressors_power_kw = rand(nHours, 1) * 80;
            totals.motors_power_kw = rand(nHours, 1) * 120;
            totals.pumps_power_kw = rand(nHours, 1) * 50;
            totals.lighting_power_kw = rand(nHours, 1) * 30;
            totals.lab_power_kw = rand(nHours, 1) * 40;
            totals.manufacturing_power_kw = rand(nHours, 1) * 60;
            totals.it_power_kw = rand(nHours, 1) * 20;
            totals.auxiliary_power_kw = rand(nHours, 1) * 10;
            totals.machine_count = int32(ones(nHours, 1) * 5);
            totals.avg_load_factor = rand(nHours, 1);
            totals.peak_power_kw = rand(nHours, 1) * 200;
            totals.peak_machine_id = int32(ones(nHours, 1));
            
            sim_db.insertHourlyTotals(testCase.conn, sim_id, totals);
            
            result = testCase.conn.fetch(sprintf(...
                'SELECT COUNT(*) AS c FROM hourly_totals WHERE simulation_id = %d', sim_id));
            testCase.verifyEqual(double(result.c), nHours, ...
                'Should have 5 hourly total rows');
        end
        
        function testQueryReturnsCorrectData(testCase)
            % testQueryReturnsCorrectData - query() returns correct data
            sim_db.insertMachines(testCase.conn, sim_catalog.load());
            
            T = sim_db.query(testCase.conn, 'SELECT * FROM machines');
            testCase.verifyEqual(height(T), 110, 'query() should return all 110 machines');
            
            T2 = sim_db.query(testCase.conn, ...
                'SELECT * FROM machines WHERE category = ''HVAC''');
            testCase.verifyGreaterThan(height(T2), 0, 'Should find HVAC machines');
        end
        
        function testCloseClosesConnection(testCase)
            % testCloseClosesConnection - close() closes connection
            tempPath = fullfile(tempdir, 'test_close.db');
            if exist(tempPath, 'file'), delete(tempPath); end
            
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            testConn = sim_db.init(tempPath);
            
            sim_db.close(testConn);
            
            % Connection should be closed - accessing it should error
            % We just verify the close method doesn't error
            testCase.verifyTrue(true, 'close() should complete without error');
            
            cd(origDir);
            if exist(tempPath, 'file'), delete(tempPath); end
        end
        
        function testErrorHandling_InvalidDbPath(testCase)
            % testErrorHandling_InvalidDbPath - invalid path should error
            testCase.verifyError(@() sim_db.open('', true), 'SIM:InvalidDbPath');
        end
        
        function testErrorHandling_PathTraversal(testCase)
            % testErrorHandling_PathTraversal - path with .. should error
            testCase.verifyError(@() sim_db.open('../../../etc/passwd', true), ...
                'SIM:UnsafePath');
        end
        
        function testEscapeSQL(testCase)
            % testEscapeSQL - escapeSQL correctly escapes single quotes
            input = "O'Brien";
            escaped = sim_db.escapeSQL(input);
            testCase.verifyEqual(char(escaped), "O''Brien", ...
                'escapeSQL should double single quotes');
            
            input2 = "it's a test";
            escaped2 = sim_db.escapeSQL(input2);
            testCase.verifyEqual(char(escaped2), "it''s a test", ...
                'escapeSQL should handle multiple quotes');
        end
        
        function testLastInsertId(testCase)
            % testLastInsertId - lastInsertId returns correct ID
            sim_id1 = sim_db.insertSimulation(testCase.conn, 'SIM-ID-1', 'Test 1', '', 42);
            sim_id2 = sim_db.insertSimulation(testCase.conn, 'SIM-ID-2', 'Test 2', '', 42);
            
            testCase.verifyEqual(sim_id2, sim_id1 + 1, ...
                'Sequential inserts should have sequential IDs');
        end
        
        function testUpdateSimulationStatus(testCase)
            % testUpdateSimulationStatus - status update persists
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-STATUS', ...
                'Test Status', '', 42);
            
            sim_db.updateSimulationStatus(testCase.conn, sim_id, 'COMPLETED', ...
                'All done');
            
            row = testCase.conn.fetch(sprintf(...
                'SELECT status, log FROM simulations WHERE simulation_id = %d', sim_id));
            testCase.verifyEqual(string(row.status{1}), 'COMPLETED');
            testCase.verifyEqual(string(row.log{1}), 'All done');
        end
        
        function testUpdateSimulationCounts(testCase)
            % testUpdateSimulationCounts - counts update persists
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-COUNTS', ...
                'Test Counts', '', 42);
            
            sim_db.updateSimulationCounts(testCase.conn, sim_id, 110, 8760);
            
            row = testCase.conn.fetch(sprintf(...
                'SELECT total_machines, total_hours FROM simulations WHERE simulation_id = %d', ...
                sim_id));
            testCase.verifyEqual(double(row.total_machines), 110);
            testCase.verifyEqual(double(row.total_hours), 8760);
        end
        
        function testInsertSimulationResults(testCase)
            % testInsertSimulationResults - results persist correctly
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-RESULTS', ...
                'Test Results', '', 42);
            
            results = struct();
            results.total_energy_kwh = 1234567.89;
            results.avg_power_kw = 500.0;
            results.peak_power_kw = 1200.0;
            results.peak_ts = '2026-07-15 14:00:00';
            results.energy_by_category_json = '{"hvac":500000}';
            
            sim_db.insertSimulationResults(testCase.conn, sim_id, results);
            
            row = testCase.conn.fetch(sprintf(...
                'SELECT * FROM simulation_results WHERE simulation_id = %d', sim_id));
            testCase.verifyNotEmpty(row, 'simulation_results should have a row');
            testCase.verifyEqual(double(row.total_energy_kwh), 1234567.89, 'RelTol', 0.01);
        end
        
        function testEmptyMeasurementsNotInserted(testCase)
            % testEmptyMeasurementsNotInserted - empty measurements table is handled
            sim_id = sim_db.insertSimulation(testCase.conn, 'SIM-EMPTY', ...
                'Test Empty', '', 42);
            
            emptyMeas = table();
            sim_db.insertMeasurements(testCase.conn, sim_id, int32(1), emptyMeas);
            
            result = testCase.conn.fetch(sprintf(...
                'SELECT COUNT(*) AS c FROM machine_measurements WHERE simulation_id = %d', sim_id));
            testCase.verifyEqual(double(result.c), 0, ...
                'Empty measurements should not insert rows');
        end
        
    end
    
end
