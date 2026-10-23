classdef test_sim_catalog_modules < matlab.unittest.TestCase
    %TEST_SIM_CATALOG_MODULES Tests for folder-per-machine catalog discovery.
    %   Covers machines/<CODE>/machine.json auto-discovery, skipping of
    %   underscore/dot folders, module validation errors, machine_id
    %   assignment by sorted machine_code, work-cycle round-trip and the
    %   26-column table contract returned by sim_catalog.load().
    %
    %   All scratch machines dirs are created under tempdir and removed on
    %   teardown; nothing is written inside the repository.

    properties
        ScratchRoot char
    end

    methods (TestMethodSetup)
        function setupTest(testCase)
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
            salt = regexprep(tempname, '[^a-zA-Z0-9]', '');
            testCase.ScratchRoot = fullfile(tempdir, ['simcat_mod_' salt]);
            if ~exist(testCase.ScratchRoot, 'dir')
                mkdir(testCase.ScratchRoot);
            end
        end
    end

    methods (TestMethodTeardown)
        function teardownTest(testCase)
            if ~isempty(testCase.ScratchRoot) && exist(testCase.ScratchRoot, 'dir')
                rmdir(testCase.ScratchRoot, 's');
            end
        end
    end

    methods (Test)

        function testDiscoversMachineFolders(testCase)
            % Two valid module folders are discovered and loaded.
            scratchDir = testCase.makeScratchDir('discover');
            testCase.writeModule(scratchDir, 'ABC-001');
            testCase.writeModule(scratchDir, 'ABC-002', struct('name', 'Second'));
            machines = sim_catalog.load(scratchDir);
            testCase.verifyEqual(height(machines), 2, ...
                'Both machine folders should be discovered');
            testCase.verifyTrue(isequal(machines.machine_code, {'ABC-001'; 'ABC-002'}), ...
                'Codes should be present and sorted');
        end

        function testTemplateAndHiddenFoldersSkipped(testCase)
            % Folders whose name starts with '_' or '.' are not machines.
            scratchDir = testCase.makeScratchDir('skip');
            testCase.writeModule(scratchDir, 'ABC-001');
            testCase.writeModule(scratchDir, 'ABC-002');
            % Copy a full valid module into _TEMPLATE and .hidden to prove
            % the skip is by folder name, not by file content.
            copyfile(fullfile(scratchDir, 'ABC-001'), fullfile(scratchDir, '_TEMPLATE'));
            copyfile(fullfile(scratchDir, 'ABC-001'), fullfile(scratchDir, '.hidden'));
            machines = sim_catalog.load(scratchDir);
            testCase.verifyEqual(height(machines), 2, ...
                '_TEMPLATE and dot-prefixed folders must be skipped');
        end

        function testMissingMachineJsonErrors(testCase)
            % A machine folder without machine.json is a module error that
            % names the offending folder/file.
            scratchDir = testCase.makeScratchDir('nojson');
            testCase.writeModule(scratchDir, 'ABC-001');
            mkdir(fullfile(scratchDir, 'ABC-002'));  % folder present, no machine.json
            err = testCase.captureError(@() sim_catalog.load(scratchDir));
            testCase.verifyEqual(err.identifier, 'SIM:ModuleInvalid');
            testCase.verifyTrue(contains(err.message, 'ABC-002'), ...
                'Error message should name the offending folder');
        end

        function testInvalidMachineJsonErrors(testCase)
            % Malformed JSON content is a module error naming the file.
            scratchDir = testCase.makeScratchDir('badjson');
            testCase.writeModule(scratchDir, 'ABC-001');
            fid = fopen(fullfile(scratchDir, 'ABC-001', 'machine.json'), 'w');
            fprintf(fid, '{ this is not valid json ');
            fclose(fid);
            err = testCase.captureError(@() sim_catalog.load(scratchDir));
            testCase.verifyEqual(err.identifier, 'SIM:ModuleInvalid');
            testCase.verifyTrue(contains(err.message, 'machine.json'), ...
                'Error message should name machine.json');
        end

        function testMissingRequiredKeyErrors(testCase)
            % A module missing a required key fails with SIM:ModuleInvalid.
            scratchDir = testCase.makeScratchDir('nokey');
            s = testCase.baseModule('ABC-001');
            s = rmfield(s, 'name');
            testCase.writeModuleStruct(scratchDir, 'ABC-001', s);
            err = testCase.captureError(@() sim_catalog.load(scratchDir));
            testCase.verifyEqual(err.identifier, 'SIM:ModuleInvalid');
            testCase.verifyTrue(contains(err.message, 'name'), ...
                'Error should name the missing field');
            testCase.verifyTrue(contains(err.message, 'ABC-001'), ...
                'Error should name the offending folder');
        end

        function testOutOfRangeValueErrors(testCase)
            % Values outside validated ranges fail with SIM:ModuleInvalid.
            scratchDir = testCase.makeScratchDir('range');
            testCase.writeModule(scratchDir, 'ABC-001', struct('rated_power_kw', -5));
            testCase.verifyError(@() sim_catalog.load(scratchDir), 'SIM:ModuleInvalid');

            scratchDir2 = testCase.makeScratchDir('range2');
            testCase.writeModule(scratchDir2, 'ABC-001', struct('phases', 4));
            testCase.verifyError(@() sim_catalog.load(scratchDir2), 'SIM:ModuleInvalid');

            scratchDir3 = testCase.makeScratchDir('range3');
            testCase.writeModule(scratchDir3, 'ABC-001', struct('power_factor', 1.5));
            testCase.verifyError(@() sim_catalog.load(scratchDir3), 'SIM:ModuleInvalid');
        end

        function testInvalidMachineCodeErrors(testCase)
            % machine_code must satisfy the backend regex ^[A-Z]{2,10}-\d{1,5}$.
            scratchDir = testCase.makeScratchDir('badcode');
            testCase.writeModule(scratchDir, 'ABC-001', struct('machine_code', 'lowercase'));
            testCase.verifyError(@() sim_catalog.load(scratchDir), 'SIM:ModuleInvalid');

            scratchDir2 = testCase.makeScratchDir('badcode2');
            testCase.writeModule(scratchDir2, 'ABC-001', struct('machine_code', 'TOO BAD'));
            testCase.verifyError(@() sim_catalog.load(scratchDir2), 'SIM:ModuleInvalid');
        end

        function testCalibrationBlockTolerated(testCase)
            % The web calibration loop appends an optional "_calibration" trace
            % block to machine.json. sim_catalog only enforces REQUIRED fields,
            % so a calibrated module must keep loading with an intact contract.
            % "_calibration" cannot be a MATLAB struct field name, so the key
            % is injected into the JSON text exactly as the Python writer does.
            scratchDir = testCase.makeScratchDir('calib');
            testCase.writeModule(scratchDir, 'ABC-001');
            testCase.writeModule(scratchDir, 'ABC-002', ...
                struct('load_factor', 0.52));
            filePath = fullfile(scratchDir, 'ABC-002', 'machine.json');
            txt = fileread(filePath);
            traceJson = [ ...
                ',"_calibration":{"calibrated_at":"2026-10-23T12:00:00+00:00",' ...
                '"before":{"load_factor":0.4},"after":{"load_factor":0.52},' ...
                '"calibrated_from":{"source":"import","import_id":7}}'];
            assert(txt(end) == '}', 'machine.json must end with a closing brace');
            fid = fopen(filePath, 'w');
            testCase.verifyNotEqual(fid, -1);
            fwrite(fid, [txt(1:end-1) traceJson '}']);
            fclose(fid);

            machines = sim_catalog.load(scratchDir);
            testCase.verifyEqual(height(machines), 2, ...
                'Module with _calibration block must load like any other');
            testCase.verifyEqual(machines.load_factor(2), 0.52, ...
                'Calibrated top-level values must flow into the catalog');
        end

        function testDuplicateCodesRejected(testCase)
            % Two folders claiming the same machine_code must be rejected.
            scratchDir = testCase.makeScratchDir('dup');
            testCase.writeModule(scratchDir, 'AAA-001');
            testCase.writeModule(scratchDir, 'BBB-001', struct('machine_code', 'AAA-001'));
            testCase.verifyError(@() sim_catalog.load(scratchDir), 'SIM:ModuleInvalid');
        end

        function testMachineIdAssignedBySortedCode(testCase)
            % machine_id is sequential over machine_code sorted ascending.
            scratchDir = testCase.makeScratchDir('ids');
            testCase.writeModule(scratchDir, 'ZZZ-003');
            testCase.writeModule(scratchDir, 'AAA-001');
            testCase.writeModule(scratchDir, 'MMM-002');
            machines = sim_catalog.load(scratchDir);
            testCase.verifyTrue(isequal(machines.machine_code, ...
                {'AAA-001'; 'MMM-002'; 'ZZZ-003'}), ...
                'Rows should be ordered by machine_code');
            testCase.verifyEqual(machines.machine_id, [1; 2; 3], ...
                'machine_id should be sequential by sorted code');
        end

        function testActiveDefaultsToOne(testCase)
            % 'active' may be omitted; the loader defaults it to 1.
            scratchDir = testCase.makeScratchDir('active');
            s = testCase.baseModule('ABC-001');
            testCase.writeModuleStruct(scratchDir, 'ABC-001', s);  % no 'active' key
            machines = sim_catalog.load(scratchDir);
            testCase.verifyEqual(machines.active(1), int32(1), ...
                'Missing active should default to int32(1)');

            testCase.writeModule(scratchDir, 'ABC-002', struct('active', 0));
            machines = sim_catalog.load(scratchDir);
            row = find(strcmp(machines.machine_code, 'ABC-002'));
            testCase.verifyEqual(machines.active(row), int32(0), ...
                'Explicit active=0 should be preserved');
        end

        function testWorkCyclesRoundTrip(testCase)
            % work_cycles object is re-serialized to the work_cycles_json
            % string column with identical state values.
            scratchDir = testCase.makeScratchDir('cycles');
            wc = struct('RUNNING', 0.3, 'PARTIAL', 0.6, 'STANDBY', 0.1);
            testCase.writeModule(scratchDir, 'ABC-001', struct('work_cycles', wc));
            machines = sim_catalog.load(scratchDir);
            decoded = jsondecode(machines.work_cycles_json{1});
            testCase.verifyTrue(isequal(fieldnames(decoded)', ...
                {'RUNNING', 'PARTIAL', 'STANDBY'}), ...
                'Cycle state names should round-trip');
            testCase.verifyEqual(struct2array(decoded), [0.3, 0.6, 0.1], ...
                'AbsTol', 1e-12, 'Cycle fractions should round-trip');
        end

        function testContractColumnsAndDtypes(testCase)
            % The loader returns the exact 26-column contract, same order
            % and same dtypes as the historical markdown parser.
            scratchDir = testCase.makeScratchDir('contract');
            testCase.writeModule(scratchDir, 'ABC-001');
            machines = sim_catalog.load(scratchDir);

            expectedNames = {'machine_id', 'machine_code', 'name', 'category', ...
                'manufacturer', 'model', 'rated_power_kw', 'voltage_v', ...
                'current_a', 'power_factor', 'phases', 'thd_pct', 'hours_per_day', ...
                'days_per_week', 'load_factor', 'seasonal_variability', ...
                'work_cycles_json', 'startup_time_s', 'startup_multiplier', ...
                'standby_pct', 'flexibility', 'application', 'criticality', ...
                'dependencies', 'environmental_notes', 'active'};
            testCase.verifyTrue(isequal(machines.Properties.VariableNames, expectedNames), ...
                'Table must expose the 26-column contract in order');

            testCase.verifyTrue(isnumeric(machines.machine_id), ...
                'machine_id should be numeric');
            testCase.verifyTrue(isnumeric(machines.rated_power_kw), ...
                'rated_power_kw should be numeric');
            testCase.verifyTrue(isa(machines.phases, 'int32'), ...
                'phases should be int32');
            testCase.verifyTrue(isa(machines.flexibility, 'int32'), ...
                'flexibility should be int32');
            testCase.verifyTrue(isa(machines.active, 'int32'), ...
                'active should be int32');
            testCase.verifyTrue(iscellstr(machines.machine_code), ...
                'machine_code should be cellstr');
            testCase.verifyTrue(iscellstr(machines.work_cycles_json), ...
                'work_cycles_json should be cellstr');
        end

        function testMissingMachinesDirErrors(testCase)
            % A nonexistent directory keeps the historical error id.
            testCase.verifyError( ...
                @() sim_catalog.load(fullfile(tempdir, 'definitely_missing_dir_xyz')), ...
                'SIM:CatalogNotFound');
        end

        function testRepoMachinesDirLoads110(testCase)
            % The repository machines/ folder holds exactly 110 modules and
            % _TEMPLATE is not counted as a machine.
            p = fileparts(fileparts(mfilename('fullpath')));   % matlab/
            repoRoot = fileparts(p);                           % project root
            scratchDir = fullfile(repoRoot, 'machines');
            testCase.verifyTrue(exist(scratchDir, 'dir') == 7, ...
                'Repository machines/ directory should exist (run migrate_catalog)');
            machines = sim_catalog.load(scratchDir);
            testCase.verifyEqual(height(machines), 110, ...
                'Catalog contract requires exactly 110 machines');
            testCase.verifyTrue(~any(strcmp(machines.machine_code, 'NEW-001')), ...
                'Template module must not be loaded');
        end

    end

    methods (Access = private)

        function err = captureError(~, operation)
            %CAPTUREERROR Run operation and return the caught MException.
            err = MException('Test:NoError', 'no error thrown');
            try
                operation();
            catch ME
                err = ME;
            end
        end

        function outDir = makeScratchDir(testCase, name)
            outDir = fullfile(testCase.ScratchRoot, name);
            if exist(outDir, 'dir')
                rmdir(outDir, 's');
            end
            mkdir(outDir);
        end

        function s = baseModule(~, code)
            %BASEMODULE A fully valid module struct with all required keys.
            s = struct();
            s.machine_code = code;
            s.name = 'Bomba de prueba';
            s.category = 'Bombas';
            s.manufacturer = 'TestMfr';
            s.model = 'TestModel';
            s.rated_power_kw = 7.5;
            s.voltage_v = 400;
            s.current_a = 14.3;
            s.power_factor = 0.85;
            s.phases = 3;
            s.thd_pct = 3.0;
            s.hours_per_day = 16;
            s.days_per_week = 5;
            s.load_factor = 0.6;
            s.seasonal_variability = 'Baja';
            s.work_cycles = struct('RUNNING', 0.6, 'STANDBY', 0.4);
            s.startup_time_s = 5;
            s.startup_multiplier = 5.0;
            s.standby_pct = 2;
            s.flexibility = 0;
            s.application = 'Prueba unitaria';
            s.criticality = 'ESENCIAL';
            s.dependencies = '';
            s.environmental_notes = '';
        end

        function writeModuleStruct(~, scratchDir, folderName, s)
            mkdir(scratchDir, folderName);
            jsonStr = jsonencode(s);
            fid = fopen(fullfile(scratchDir, folderName, 'machine.json'), 'w');
            if fid < 0
                error('TestSetup:CannotWrite', ...
                    'Could not open scratch machine.json for writing');
            end
            fwrite(fid, jsonStr);
            fclose(fid);
        end

        function writeModule(testCase, scratchDir, folderName, overrides)
            %WRITEMODULE Write a valid module, applying optional field overrides.
            if nargin < 4
                overrides = struct();
            end
            s = testCase.baseModule(folderName);
            fn = fieldnames(overrides);
            for i = 1:numel(fn)
                s.(fn{i}) = overrides.(fn{i});
            end
            testCase.writeModuleStruct(scratchDir, folderName, s);
        end

    end

end
