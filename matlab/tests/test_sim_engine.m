classdef test_sim_engine < matlab.unittest.TestCase
    %TEST_SIM_ENGINE Pruebas del orquestador de simulación completa.
    %   Tests the full simulation orchestrator that coordinates all components.
    
    properties
        matlabRoot char
    end
    
    methods (TestMethodSetup)
        function setupTest(testCase)
            % Add paths
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            testCase.matlabRoot = p;
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
        end
    end
    
    methods (Test)
        
        function testRunCompletesWithoutErrors(testCase)
            % testRunCompletesWithoutErrors - run() completes successfully
            % Use a temporary database path
            tempDbPath = fullfile(tempdir, sprintf('test_engine_%d.db', randi(1e9)));
            if exist(tempDbPath, 'file'), delete(tempDbPath); end
            
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            % Override DB_PATH temporarily
            origDbPath = simulacion_params.DB_PATH;
            try
                % Note: We can't easily override simulacion_params constants,
                % so we just run with the default and clean up after
                [sim_id, summary] = sim_engine.run('TEST-ENG-001', 'Test Engine', ...
                    'Unit test', 42);
                
                testCase.verifyGreaterThan(sim_id, 0, 'sim_id should be positive');
                testCase.verifyNotEmpty(summary, 'summary should not be empty');
                testCase.verifyEqual(summary.status, 'COMPLETED', ...
                    'Simulation should complete successfully');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testSimulationIdValid(testCase)
            % testSimulationIdValid - output simulation_id is valid
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, ~] = sim_engine.run('TEST-ENG-ID', 'Test ID', '', 42);
                
                testCase.verifyTrue(isnumeric(sim_id) && isscalar(sim_id), ...
                    'sim_id should be numeric scalar');
                testCase.verifyGreaterThan(sim_id, 0, 'sim_id should be positive');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testDatabaseContainsCorrectMachines(testCase)
            % testDatabaseContainsCorrectMachines - DB has all 110 machines
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, ~] = sim_engine.run('TEST-ENG-MACH', 'Test Machines', '', 42);
                
                conn = sqlite(simulacion_params.DB_PATH);
                result = conn.fetch('SELECT COUNT(*) AS c FROM machines');
                conn.close();
                
                testCase.verifyEqual(double(result.c), 110, ...
                    'Database should contain 110 machines');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testDatabaseContains8760RowsPerMachine(testCase)
            % testDatabaseContains8760RowsPerMachine - machine_measurements has correct rows
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, ~] = sim_engine.run('TEST-ENG-ROWS', 'Test Rows', '', 42);
                
                conn = sqlite(simulacion_params.DB_PATH);
                result = conn.fetch(sprintf(...
                    'SELECT COUNT(*) AS c FROM machine_measurements WHERE simulation_id = %d', ...
                    sim_id));
                conn.close();
                
                expectedRows = 110 * 8760;  % 110 machines × 8760 hours
                testCase.verifyEqual(double(result.c), expectedRows, ...
                    'machine_measurements should have 110 × 8760 rows');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testHourlyTotalsHas8760Rows(testCase)
            % testHourlyTotalsHas8760Rows - hourly_totals has 8760 rows
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, ~] = sim_engine.run('TEST-ENG-HOURLY', 'Test Hourly', '', 42);
                
                conn = sqlite(simulacion_params.DB_PATH);
                result = conn.fetch(sprintf(...
                    'SELECT COUNT(*) AS c FROM hourly_totals WHERE simulation_id = %d', ...
                    sim_id));
                conn.close();
                
                testCase.verifyEqual(double(result.c), 8760, ...
                    'hourly_totals should have 8760 rows');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testTotalEnergyReasonable(testCase)
            % testTotalEnergyReasonable - total energy is reasonable
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, summary] = sim_engine.run('TEST-ENG-ENERGY', 'Test Energy', '', 42);
                
                % Total energy should be positive and reasonable
                % With 110 machines averaging ~100kW for 8760 hours,
                % expected total is roughly 110 * 100 * 8760 * 0.5 (load factor) ≈ 48M kWh
                % Allow wide range: 10M to 100M kWh
                testCase.verifyGreaterThan(summary.total_energy_kwh, 1e7, ...
                    'Total energy should be at least 10M kWh');
                testCase.verifyLessThan(summary.total_energy_kwh, 1e8, ...
                    'Total energy should be less than 100M kWh');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testPeakPowerWithinRange(testCase)
            % testPeakPowerWithinRange - peak power is within expected range
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, summary] = sim_engine.run('TEST-ENG-PEAK', 'Test Peak', '', 42);
                
                % Peak power should be reasonable
                % With 110 machines, peak could be 2000-8000 kW
                testCase.verifyGreaterThan(summary.peak_power_kw, 1000, ...
                    'Peak power should be at least 1000 kW');
                testCase.verifyLessThan(summary.peak_power_kw, 10000, ...
                    'Peak power should be less than 10000 kW');
                
                % Peak should be >= average
                testCase.verifyGreaterThan(summary.peak_power_kw, summary.avg_power_kw, ...
                    'Peak power should be >= average power');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testReproducibility(testCase)
            % testReproducibility - same seed produces identical results
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                % Run 1
                [sim_id1, summary1] = sim_engine.run('TEST-REPRO-1', 'Repro 1', '', 42);
                
                % Cleanup DB
                dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
                if exist(dbPath, 'file'), delete(dbPath); end
                
                % Run 2 with same seed
                [sim_id2, summary2] = sim_engine.run('TEST-REPRO-2', 'Repro 2', '', 42);
                
                % Compare key metrics
                testCase.verifyEqual(summary1.total_energy_kwh, summary2.total_energy_kwh, ...
                    'RelTol', 1e-9, 'Same seed should produce identical total energy');
                testCase.verifyEqual(summary1.peak_power_kw, summary2.peak_power_kw, ...
                    'RelTol', 1e-9, 'Same seed should produce identical peak power');
                testCase.verifyEqual(summary1.avg_power_kw, summary2.avg_power_kw, ...
                    'RelTol', 1e-9, 'Same seed should produce identical average power');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testSimulationResultsPopulated(testCase)
            % testSimulationResultsPopulated - simulation_results table is populated
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, ~] = sim_engine.run('TEST-ENG-RES', 'Test Results', '', 42);
                
                conn = sqlite(simulacion_params.DB_PATH);
                result = conn.fetch(sprintf(...
                    'SELECT COUNT(*) AS c FROM simulation_results WHERE simulation_id = %d', ...
                    sim_id));
                conn.close();
                
                testCase.verifyEqual(double(result.c), 1, ...
                    'simulation_results should have 1 row');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testMachineResultsPopulated(testCase)
            % testMachineResultsPopulated - machine_results table is populated
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, ~] = sim_engine.run('TEST-ENG-MRES', 'Test Machine Results', '', 42);
                
                conn = sqlite(simulacion_params.DB_PATH);
                result = conn.fetch(sprintf(...
                    'SELECT COUNT(*) AS c FROM machine_results WHERE simulation_id = %d', ...
                    sim_id));
                conn.close();
                
                testCase.verifyEqual(double(result.c), 110, ...
                    'machine_results should have 110 rows (one per machine)');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
        function testErrorHandling_MissingSimCode(testCase)
            % testErrorHandling_MissingSimCode - missing sim code should error
            testCase.verifyError(@() sim_engine.run('', 'Test', '', 42), ...
                'SIM:MissingSimCode');
        end
        
        function testErrorHandling_InvalidSeed(testCase)
            % testErrorHandling_InvalidSeed - invalid seed should error
            testCase.verifyError(@() sim_engine.run('TEST', 'Test', '', -1), ...
                'SIM:InvalidSeed');
            testCase.verifyError(@() sim_engine.run('TEST', 'Test', '', 3.14), ...
                'SIM:InvalidSeed');
        end
        
        function testSummaryStructure(testCase)
            % testSummaryStructure - summary has all required fields
            origDir = pwd;
            repoRoot = fileparts(fileparts(testCase.matlabRoot));
            cd(repoRoot);
            
            try
                [sim_id, summary] = sim_engine.run('TEST-ENG-SUM', 'Test Summary', '', 42);
                
                requiredFields = {'simulation_id', 'simulation_code', 'total_machines', ...
                    'total_hours', 'total_energy_kwh', 'avg_power_kw', 'peak_power_kw', ...
                    'peak_ts', 'elapsed_seconds', 'status'};
                
                summaryFields = fieldnames(summary);
                for i = 1:numel(requiredFields)
                    testCase.verifyTrue(ismember(requiredFields{i}, summaryFields), ...
                        sprintf('Summary should have field "%s"', requiredFields{i}));
                end
                
                testCase.verifyEqual(summary.total_machines, 110);
                testCase.verifyEqual(summary.total_hours, 8760);
                testCase.verifyEqual(summary.status, 'COMPLETED');
                
            catch ME
                testCase.verifyFail(sprintf('run() should not error: %s', ME.message));
            end
            
            cd(origDir);
            
            % Cleanup
            dbPath = fullfile(repoRoot, simulacion_params.DB_PATH);
            if exist(dbPath, 'file')
                delete(dbPath);
            end
        end
        
    end
    
end
