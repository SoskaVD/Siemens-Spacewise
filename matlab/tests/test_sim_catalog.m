classdef test_sim_catalog < matlab.unittest.TestCase
    %TEST_SIM_CATALOG Pruebas del parser de catálogo de equipos industriales.
    %   Tests the catalog loader that discovers the 110 machine modules from
    %   the folder-per-machine catalog in machines/<CODE>/machine.json
    
    properties
        MachinesDir char
        OrigDir char
        RepoRoot char
    end
    
    methods (TestMethodSetup)
        function setupTest(testCase)
            % Add paths and cd to repo root so relative paths resolve
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
            testCase.OrigDir = pwd;
            testCase.RepoRoot = fileparts(p);  % Siemens-Spacewise/
            cd(testCase.RepoRoot);
            
            % Build absolute machines dir path from repo root
            testCase.MachinesDir = fullfile(testCase.RepoRoot, 'machines');
        end
    end
    
    methods (TestMethodTeardown)
        function teardownTest(testCase)
            cd(testCase.OrigDir);
        end
    end
    
    methods (Test)
        
        function testLoadCatalog(testCase)
            % testLoadCatalog - Test that catalog loads successfully
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            testCase.assertNotEmpty(machines, 'Catalog should not be empty');
        end
        
        function testExactly110Machines(testCase)
            % testExactly110Machines - Test that exactly 110 machines are loaded
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            testCase.verifyEqual(height(machines), 110, ...
                'Catalog should contain exactly 110 machines');
        end
        
        function testRequiredFieldsPresent(testCase)
            % testRequiredFieldsPresent - Test all required fields are present
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            requiredFields = {'machine_code', 'name', 'category', 'rated_power_kw', ...
                'voltage_v', 'current_a', 'power_factor', 'phases', 'thd_pct', ...
                'hours_per_day', 'days_per_week', 'load_factor', 'criticality', ...
                'work_cycles_json', 'startup_time_s', 'startup_multiplier'};
            
            fieldNames = machines.Properties.VariableNames;
            for i = 1:numel(requiredFields)
                testCase.verifyTrue(ismember(requiredFields{i}, fieldNames), ...
                    sprintf('Required field "%s" missing', requiredFields{i}));
            end
        end
        
        function testDataTypesCorrect(testCase)
            % testDataTypesCorrect - Test data types are correct
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            % Numeric fields should be numeric
            testCase.verifyTrue(isnumeric(machines.rated_power_kw), 'rated_power_kw should be numeric');
            testCase.verifyTrue(isnumeric(machines.voltage_v), 'voltage_v should be numeric');
            testCase.verifyTrue(isnumeric(machines.current_a), 'current_a should be numeric');
            testCase.verifyTrue(isnumeric(machines.power_factor), 'power_factor should be numeric');
            testCase.verifyTrue(isnumeric(machines.phases), 'phases should be numeric');
            testCase.verifyTrue(isnumeric(machines.thd_pct), 'thd_pct should be numeric');
            testCase.verifyTrue(isnumeric(machines.hours_per_day), 'hours_per_day should be numeric');
            testCase.verifyTrue(isnumeric(machines.days_per_week), 'days_per_week should be numeric');
            testCase.verifyTrue(isnumeric(machines.load_factor), 'load_factor should be numeric');
            testCase.verifyTrue(isnumeric(machines.startup_time_s), 'startup_time_s should be numeric');
            testCase.verifyTrue(isnumeric(machines.startup_multiplier), 'startup_multiplier should be numeric');
            
            % String fields should be cell arrays
            testCase.verifyTrue(iscellstr(machines.machine_code), 'machine_code should be cellstr');
            testCase.verifyTrue(iscellstr(machines.name), 'name should be cellstr');
            testCase.verifyTrue(iscellstr(machines.category), 'category should be cellstr');
            testCase.verifyTrue(iscellstr(machines.criticality), 'criticality should be cellstr');
            testCase.verifyTrue(iscellstr(machines.work_cycles_json), 'work_cycles_json should be cellstr');
        end
        
        function testCriticalityValuesValid(testCase)
            % testCriticalityValuesValid - Test criticality values are valid
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            validCriticalities = {'CRITICA', 'ESENCIAL', 'FLEXIBLE', 'NO_CRITICA'};
            
            for i = 1:height(machines)
                crit = machines.criticality{i};
                testCase.verifyTrue(ismember(crit, validCriticalities), ...
                    sprintf('Machine %d has invalid criticality: %s', i, crit));
            end
        end
        
        function testWorkCyclesJsonValid(testCase)
            % testWorkCyclesJsonValid - Test work_cycles_json is valid JSON
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            for i = 1:min(10, height(machines))  % Test first 10 for speed
                jsonStr = machines.work_cycles_json{i};
                if ~isempty(jsonStr)
                    try
                        cycles = jsondecode(jsonStr);
                        testCase.verifyTrue(isstruct(cycles), ...
                            sprintf('Machine %d: decoded JSON should be struct', i));
                    catch ME
                        testCase.verifyFail(sprintf('Machine %d: invalid JSON: %s', i, ME.message));
                    end
                end
            end
        end
        
        function testErrorHandling_DirNotFound(testCase)
            % testErrorHandling_DirNotFound - Test error when machines dir is missing
            testCase.verifyError(@() sim_catalog.load('nonexistent_machines_dir_xyz'), ...
                'SIM:CatalogNotFound');
        end
        
        function testErrorHandling_NotADirectory(testCase)
            % testErrorHandling_NotADirectory - A plain file is not a machines dir
            % (the markdown file must NOT be parsed at load time anymore)
            tempFile = fullfile(tempdir, 'not_a_machines_dir.md');
            fid = fopen(tempFile, 'w');
            fprintf(fid, '# Not a catalog\nHVAC-001|x|y|1|2|3|0.9|8|5|0.5|CRITICA\n');
            fclose(fid);
            
            try
                testCase.verifyError(@() sim_catalog.load(tempFile), 'SIM:CatalogNotFound');
            finally
                if exist(tempFile, 'file')
                    delete(tempFile);
                end
            end
        end
        
        function testSpecificMachine_HVAC001(testCase)
            % testSpecificMachine_HVAC001 - Spot check HVAC-001 values
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            hvacIdx = find(strcmp(machines.machine_code, 'HVAC-001'));
            testCase.verifyNotEmpty(hvacIdx, 'HVAC-001 should exist');
            
            idx = hvacIdx(1);
            testCase.verifyEqual(machines.name{idx}, 'Chiller Centrifugo CVHE', ...
                'HVAC-001 name mismatch');
            testCase.verifyEqual(machines.rated_power_kw(idx), 350.0, 'RelTol', 0.01, ...
                'HVAC-001 rated power should be 350 kW');
            testCase.verifyEqual(machines.voltage_v(idx), 400, 'RelTol', 0.01, ...
                'HVAC-001 voltage should be 400V');
            testCase.verifyEqual(machines.criticality{idx}, 'CRITICA', ...
                'HVAC-001 should be CRITICA');
        end
        
        function testSpecificMachine_COMP015(testCase)
            % testSpecificMachine_COMP015 - Spot check COMP-015 exists
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            compIdx = find(strcmp(machines.machine_code, 'COMP-015'));
            testCase.verifyNotEmpty(compIdx, 'COMP-015 should exist');
            
            idx = compIdx(1);
            testCase.verifyGreaterThan(machines.rated_power_kw(idx), 0, ...
                'COMP-015 should have positive power');
        end
        
        function testSpecificMachine_MOT020(testCase)
            % testSpecificMachine_MOT020 - Spot check MOT-020 exists
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            motIdx = find(strcmp(machines.machine_code, 'MOT-020'));
            testCase.verifyNotEmpty(motIdx, 'MOT-020 should exist');
            
            idx = motIdx(1);
            testCase.verifyGreaterThan(machines.rated_power_kw(idx), 0, ...
                'MOT-020 should have positive power');
        end
        
        function testNumericRangesValid(testCase)
            % testNumericRangesValid - Test numeric values are in valid ranges
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            % Rated power should be positive
            testCase.verifyTrue(all(machines.rated_power_kw > 0), ...
                'All machines should have positive rated power');
            
            % Voltage should be positive
            testCase.verifyTrue(all(machines.voltage_v > 0), ...
                'All machines should have positive voltage');
            
            % Current should be positive
            testCase.verifyTrue(all(machines.current_a > 0), ...
                'All machines should have positive current');
            
            % Power factor should be in (0, 1]
            testCase.verifyTrue(all(machines.power_factor > 0) && all(machines.power_factor <= 1), ...
                'Power factor should be in (0, 1]');
            
            % Phases should be 1, 2, or 3
            testCase.verifyTrue(all(ismember(machines.phases, [1, 2, 3])), ...
                'Phases should be 1, 2, or 3');
            
            % Hours per day should be in [0, 24]
            testCase.verifyTrue(all(machines.hours_per_day >= 0) && all(machines.hours_per_day <= 24), ...
                'Hours per day should be in [0, 24]');
            
            % Days per week should be in [0, 7]
            testCase.verifyTrue(all(machines.days_per_week >= 0) && all(machines.days_per_week <= 7), ...
                'Days per week should be in [0, 7]');
            
            % Load factor should be in [0, 1]
            testCase.verifyTrue(all(machines.load_factor >= 0) && all(machines.load_factor <= 1), ...
                'Load factor should be in [0, 1]');
            
            % Startup multiplier should be >= 1
            testCase.verifyTrue(all(machines.startup_multiplier >= 1), ...
                'Startup multiplier should be >= 1');
        end
        
        function testMachineCodesUnique(testCase)
            % testMachineCodesUnique - Test all machine codes are unique
            catalogPath = testCase.MachinesDir;
            machines = sim_catalog.load(catalogPath);
            
            uniqueCodes = unique(machines.machine_code);
            testCase.verifyEqual(numel(uniqueCodes), height(machines), ...
                'All machine codes should be unique');
        end
        
    end
    
end
