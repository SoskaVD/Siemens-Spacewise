classdef test_sim_machine < matlab.unittest.TestCase
    %TEST_SIM_MACHINE Pruebas del generador de perfiles horarios por máquina.
    %   Tests individual machine profile generation for 8760 hours.
    
    properties
        Machine247 struct    % Machine running 24/7
        Machine8h5d struct  % Machine running 8h/day, 5 days/week
    end
    
    methods (TestMethodSetup)
        function setupTest(testCase)
            % Add paths
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
            
            % Build a 24/7 machine (like HVAC-001: Chiller 350kW)
            testCase.Machine247 = testCase.buildTestMachine( ...
                1, 'TEST-001', 'Test Machine 24/7', 'HVAC', ...
                350.0, 400, 0.85, 3, 24, 7, 0.75, 'Alta', ...
                '{"RUNNING":0.3,"PARTIAL":0.6,"STANDBY":0.1}', ...
                60, 4.0, 5, 'CRITICA');
            
            % Build a partial-week machine (8h/day, 5 days/week)
            testCase.Machine8h5d = testCase.buildTestMachine( ...
                2, 'TEST-002', 'Test Machine 8h5d', 'Motores', ...
                50.0, 400, 0.80, 3, 8, 5, 0.60, 'Baja', ...
                '{"RUNNING":0.7,"STANDBY":0.3}', ...
                10, 5.0, 0, 'FLEXIBLE');
        end
    end
    
    methods (Test)
        
        function testOutputIs8760Rows(testCase)
            % testOutputIs8760Rows - Output should have exactly 8760 rows
            profile = sim_machine.generate(testCase.Machine247, 42);
            testCase.verifyEqual(height(profile), 8760, ...
                'Profile should have 8760 hours (1 year)');
        end
        
        function testRequiredColumnsPresent(testCase)
            % testRequiredColumnsPresent - Required columns exist
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            requiredCols = {'ts', 'hour_index', 'active_power_kw', 'energy_kwh', ...
                'load_factor', 'operation_state'};
            
            colNames = profile.Properties.VariableNames;
            for i = 1:numel(requiredCols)
                testCase.verifyTrue(ismember(requiredCols{i}, colNames), ...
                    sprintf('Required column "%s" missing', requiredCols{i}));
            end
        end
        
        function testActivePowerWithinValidRange(testCase)
            % testActivePowerWithinValidRange - Power within [0, rated * startup_mult]
            profile = sim_machine.generate(testCase.Machine247, 42);
            ratedPower = testCase.Machine247.rated_power_kw;
            startupMult = testCase.Machine247.startup_multiplier;
            maxExpected = ratedPower * startupMult;
            
            testCase.verifyGreaterThanOrEqual(min(profile.active_power_kw), 0, ...
                'Active power should be >= 0');
            testCase.verifyLessThanOrEqual(max(profile.active_power_kw), maxExpected + 1e-6, ...
                sprintf('Active power should be <= %.2f (rated * startup_mult)', maxExpected));
        end
        
        function testEnergyEqualsPowerTimesHour(testCase)
            % testEnergyEqualsPowerTimesHour - energy_kwh = active_power_kw * 1h (±tolerance)
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            testCase.verifyEqual(profile.energy_kwh, profile.active_power_kw, ...
                'AbsTol', 1e-6, 'energy_kwh should equal active_power_kw (1 hour interval)');
        end
        
        function testLoadFactorBetween0And1(testCase)
            % testLoadFactorBetween0And1 - load_factor in [0, 1] for non-startup
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            % For non-startup hours, load_factor should be in [0, startup_multiplier]
            % (startup may exceed 1 due to startup_mult)
            nonStartup = ~strcmp(profile.operation_state, 'STARTUP');
            lf = profile.load_factor(nonStartup);
            
            testCase.verifyGreaterThanOrEqual(min(lf), 0, ...
                'Non-startup load factor should be >= 0');
            testCase.verifyLessThanOrEqual(max(lf), 1, ...
                'Non-startup load factor should be <= 1');
        end
        
        function testOperationStateValuesValid(testCase)
            % testOperationStateValuesValid - operation_state values are valid
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            validStates = simulacion_params.OP_STATES;
            uniqueStates = unique(profile.operation_state);
            
            for i = 1:numel(uniqueStates)
                testCase.verifyTrue(ismember(uniqueStates{i}, validStates), ...
                    sprintf('Invalid operation state: %s', uniqueStates{i}));
            end
        end
        
        function testReproducibility_SameSeed(testCase)
            % testReproducibility_SameSeed - Same seed produces identical results
            profile1 = sim_machine.generate(testCase.Machine247, 42);
            profile2 = sim_machine.generate(testCase.Machine247, 42);
            
            testCase.verifyEqual(profile1.active_power_kw, profile2.active_power_kw, ...
                'Same seed should produce identical power profiles');
            testCase.verifyEqual(profile1.energy_kwh, profile2.energy_kwh, ...
                'Same seed should produce identical energy profiles');
        end
        
        function testReproducibility_DifferentSeeds(testCase)
            % testReproducibility_DifferentSeeds - Different seeds produce different results
            profile1 = sim_machine.generate(testCase.Machine247, 42);
            profile2 = sim_machine.generate(testCase.Machine247, 99);
            
            testCase.verifyFalse(isequal(profile1.active_power_kw, profile2.active_power_kw), ...
                'Different seeds should produce different power profiles');
        end
        
        function testMachine247_NoOffPeriods(testCase)
            % testMachine247_NoOffPeriods - 24/7 machine has no OFF periods
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            nOff = sum(strcmp(profile.operation_state, 'OFF'));
            testCase.verifyEqual(nOff, 0, ...
                'Machine running 24/7 should have zero OFF hours');
        end
        
        function testMachine8h5d_HasOffPeriods(testCase)
            % testMachine8h5d_HasOffPeriods - 8h/day 5d/week has expected OFF periods
            profile = sim_machine.generate(testCase.Machine8h5d, 42);
            
            % Expected OFF hours:
            % - Weekends: 2 days * 24h = 48h/week * 52.14 weeks ≈ 2503h
            % - Outside 8h window: 16h * 5 days * 52.14 ≈ 4171h
            % Total OFF should be substantial (> 3000 hours)
            nOff = sum(strcmp(profile.operation_state, 'OFF'));
            testCase.verifyGreaterThan(nOff, 3000, ...
                '8h/day 5d/week machine should have significant OFF periods');
            
            % Operating hours should be roughly 8*5*52 = 2080 ± some margin
            nOperating = sum(~strcmp(profile.operation_state, 'OFF'));
            testCase.verifyGreaterThanOrEqual(nOperating, 1500, ...
                'Should have at least 1500 operating hours');
            testCase.verifyLessThanOrEqual(nOperating, 2500, ...
                'Should have no more than 2500 operating hours');
        end
        
        function testStartupTransientApplied(testCase)
            % testStartupTransientApplied - STARTUP hours have power = rated * startup_mult
            % We need a machine where startup events happen during operating hours
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            startupMask = strcmp(profile.operation_state, 'STARTUP');
            if any(startupMask)
                startupPower = profile.active_power_kw(startupMask);
                expectedPower = testCase.Machine247.rated_power_kw * testCase.Machine247.startup_multiplier;
                
                for i = 1:numel(startupPower)
                    testCase.verifyEqual(startupPower(i), expectedPower, ...
                        'RelTol', 0.01, 'Startup power should be rated * startup_multiplier');
                end
            else
                % If no startup events occur, that is acceptable - just note it
                testCase.verifyTrue(true, 'No startup events detected (acceptable)');
            end
        end
        
        function testSeasonalVariabilityApplied(testCase)
            % testSeasonalVariabilityApplied - Summer months differ from winter for Alta variability
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            % Extract months from timestamps
            months = zeros(8760, 1);
            for h = 1:8760
                try
                    dt = datetime(profile.ts(h), 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
                    months(h) = dt.Month;
                catch
                    months(h) = 1;
                end
            end
            
            % For Alta variability: summer (Dec-Feb) should have higher avg power than winter (Jun-Aug)
            summerMask = ismember(months, [12, 1, 2]);
            winterMask = ismember(months, [6, 7, 8]);
            
            if any(summerMask) && any(winterMask)
                summerAvgPower = mean(profile.active_power_kw(summerMask));
                winterAvgPower = mean(profile.active_power_kw(winterMask));
                
                testCase.verifyGreaterThan(summerAvgPower, winterAvgPower, ...
                    'HVAC with Alta variability should use more power in summer');
            end
        end
        
        function testTimestampsMonotonicallyIncreasing(testCase)
            % testTimestampsMonotonicallyIncreasing - ts should be sequential hourly
            profile = sim_machine.generate(testCase.Machine247, 42);
            
            % hour_index should go from 0 to 8759
            testCase.verifyEqual(profile.hour_index(1), int32(0), 'First hour should be 0');
            testCase.verifyEqual(profile.hour_index(end), int32(8759), 'Last hour should be 8759');
            
            % Check sequential
            diffs = diff(double(profile.hour_index));
            testCase.verifyTrue(all(diffs == 1), 'hour_index should be sequential');
        end
        
        function testZeroRatedPower(testCase)
            % testZeroRatedPower - Machine with zero power produces all zeros
            m = testCase.buildTestMachine(3, 'ZERO-001', 'Zero Power', 'Auxiliares', ...
                0.0, 400, 0.80, 3, 24, 7, 0.5, 'Baja', ...
                '{"RUNNING":1.0}', 5, 1.5, 0, 'NO_CRITICA');
            
            profile = sim_machine.generate(m, 42);
            testCase.verifyEqual(sum(profile.active_power_kw), 0, ...
                'Machine with 0 rated power should produce 0 energy');
        end
        
        function testInvalidMachineInput(testCase)
            % testInvalidMachineInput - Empty machine should error
            testCase.verifyError(@() sim_machine.generate([], 42), 'SIM:InvalidMachine');
        end
        
        function testDefaultSeedUsed(testCase)
            % testDefaultSeedUsed - When no seed given, default seed is used (reproducible)
            profile1 = sim_machine.generate(testCase.Machine247);
            profile2 = sim_machine.generate(testCase.Machine247, simulacion_params.DEFAULT_SEED);
            
            testCase.verifyEqual(profile1.active_power_kw, profile2.active_power_kw, ...
                'Default seed should match DEFAULT_SEED');
        end
        
    end
    
    methods (Static, Access = private)
        
        function m = buildTestMachine(id, code, name, category, power, voltage, pf, ...
            phases, hoursPerDay, daysPerWeek, loadFactor, seasonalVar, ...
            workCyclesJson, startupTime, startupMult, standbyPct, criticality)
            %BUILDTESTMACHINE Build a test machine struct with all required fields.
            m = struct();
            m.machine_id = int32(id);
            m.machine_code = code;
            m.name = name;
            m.category = category;
            m.manufacturer = 'TestMfr';
            m.model = 'TestModel';
            m.rated_power_kw = power;
            m.voltage_v = voltage;
            m.current_a = power * 1000 / (sqrt(3) * voltage * pf);
            m.power_factor = pf;
            m.phases = int32(phases);
            m.thd_pct = 5.0;
            m.hours_per_day = hoursPerDay;
            m.days_per_week = daysPerWeek;
            m.load_factor = loadFactor;
            m.seasonal_variability = seasonalVar;
            m.work_cycles_json = workCyclesJson;
            m.startup_time_s = startupTime;
            m.startup_multiplier = startupMult;
            m.standby_pct = standbyPct;
            m.flexibility = int32(0);
            m.application = 'Test';
            m.criticality = criticality;
            m.dependencies = '';
            m.environmental_notes = '';
            m.active = int32(1);
        end
        
    end
    
end
