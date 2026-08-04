classdef test_dt_db < matlab.unittest.TestCase
    %TEST_DT_DB Pruebas de la capa de persistencia SQLite.

    properties
        dbPath char
        conn
    end

    methods (TestMethodSetup)
        function setup(testCase)
            testCase.dbPath = fullfile(tempdir, 'test_spacewise.db');
            if exist(testCase.dbPath, 'file')
                delete(testCase.dbPath);
            end
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
            testCase.conn = dt_db.init(testCase.dbPath);
        end
    end

    methods (TestMethodTeardown)
        function teardown(testCase)
            dt_db.close(testCase.conn);
            if exist(testCase.dbPath, 'file')
                delete(testCase.dbPath);
            end
        end
    end

    methods (Test)

        function schemaTables(testCase)
            tbl = testCase.conn.fetch("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name");
            names = string(tbl.name);
            expected = ["device_types"; "devices"; "environment"; "events"; ...
                "measurements"; "scenarios"; "simulation_results"; ...
                "simulations"; "subsystem_profiles"];
            for i = 1:numel(expected)
                testCase.verifyTrue(any(names == expected(i)), expected(i));
            end
        end

        function insertDevices(testCase)
            dt_db.insertDeviceTypes(testCase.conn, dt_device.types());
            dt_db.insertDevices(testCase.conn, dt_device.catalog());
            n = testCase.conn.fetch('SELECT COUNT(*) AS c FROM devices').c;
            testCase.verifyEqual(double(n), 22);
        end

        function scenarioRoundTrip(testCase)
            P = spacewise_params();
            sid = dt_db.insertScenario(testCase.conn, 'TEST1', 'Prueba', 'desc', P, 1);
            testCase.verifyGreaterThan(sid, 0);
            row = testCase.conn.fetch("SELECT * FROM scenarios WHERE scenario_id=" + sid);
            testCase.verifyEqual(string(row.scenario_code), "TEST1");
        end

        function fullSimulationPersist(testCase)
            dt_db.insertDeviceTypes(testCase.conn, dt_device.types());
            dt_db.insertDevices(testCase.conn, dt_device.catalog());
            devT = testCase.conn.fetch('SELECT * FROM devices');

            P = spacewise_params();
            P.measurement_days = 30;  % ventana corta para la prueba
            scs = dt_scenario.definitions();
            sc = scs(6);  % E5
            Psc = dt_scenario.mergeParams(P, sc.override);
            [res, env, base, ctrl] = dt_engine.run(Psc, sc);

            sid = dt_db.insertScenario(testCase.conn, sc.scenario_code, sc.name, sc.description, Psc, sc.is_baseline);
            simid = dt_db.insertSimulation(testCase.conn, sid, dt_engine.version());
            [measT, envT, eventsT] = dt_measurements.generate(Psc, env, ctrl, devT);
            dt_db.insertEnvironment(testCase.conn, simid, envT);
            dt_db.insertMeasurements(testCase.conn, simid, measT);
            dt_db.insertProfiles(testCase.conn, simid, dt_analysis.profilesTable(base, ctrl, env));
            dt_db.insertResults(testCase.conn, simid, dt_analysis.resultsTable(res, Psc, base, ctrl));
            dt_db.insertEvents(testCase.conn, simid, eventsT);

            nMeas = testCase.conn.fetch('SELECT COUNT(*) AS c FROM measurements').c;
            testCase.verifyEqual(double(nMeas), height(measT));
            nRes = testCase.conn.fetch(sprintf('SELECT COUNT(*) AS c FROM simulation_results WHERE simulation_id=%d', simid)).c;
            testCase.verifyEqual(double(nRes), 7);  % 6 subsistemas + TOTAL
            tot = testCase.conn.fetch(sprintf("SELECT savings_pct FROM simulation_results WHERE simulation_id=%d AND subsystem='TOTAL'", simid));
            testCase.verifyGreaterThan(tot.savings_pct(1), 20);
        end

    end

end
