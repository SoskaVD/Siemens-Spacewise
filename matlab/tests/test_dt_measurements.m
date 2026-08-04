classdef test_dt_measurements < matlab.unittest.TestCase
    %TEST_DT_MEASUREMENTS Pruebas de generación de mediciones por dispositivo.

    methods (TestMethodSetup)
        function addPaths(testCase)
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
        end
    end

    methods (Test)

        function conservationPerSubsystem(testCase)
            % Sum(P_dev) == P_subsistema por hora (excluyendo medidores).
            P = spacewise_params();
            P.measurement_days = 30;
            scs = dt_scenario.definitions();
            sc = scs(6);
            Psc = dt_scenario.mergeParams(P, sc.override);
            [~, env, ~, ctrl] = dt_engine.run(Psc, sc);

            devT = dt_device.catalog();
            devT.device_id = (1:height(devT))';
            [measT, ~, ~] = dt_measurements.generate(Psc, env, ctrl, devT);

            firstTs = measT.ts(1);
            h = measT(measT.ts == firstTs, :);
            isMeter = strcmp(devT.type_code, 'meter');
            subs = {'HVAC'; 'LAB'; 'IT'; 'ILUM'; 'BOMB'; 'AUX'};
            for i = 1:numel(subs)
                s = subs{i};
                devs = find(strcmp(devT.subsystem, s) & ~isMeter);
                sumP = sum(h.active_power_kw(ismember(h.device_id, devs)));
                testCase.verifyEqual(sumP, ctrl.(s)(1), 'RelTol', 0.05, ...
                    sprintf('Conservación de energía en %s', s));
            end
        end

        function rowCounts(testCase)
            % Filas = dispositivos x horas de la ventana.
            P = spacewise_params();
            P.measurement_days = 14;
            scs = dt_scenario.definitions();
            sc = scs(1);
            [~, env, ~, ctrl] = dt_engine.run(P, sc);

            devT = dt_device.catalog();
            devT.device_id = (1:height(devT))';
            [measT, envT, ~] = dt_measurements.generate(P, env, ctrl, devT);
            expected = height(devT)*P.measurement_days*24;
            testCase.verifyEqual(height(measT), expected);
            testCase.verifyEqual(height(envT), P.measurement_days*24);
        end

        function magnitudesPositive(testCase)
            % Corriente, energía y THD deben ser positivos; PF en [0.7, 1].
            P = spacewise_params();
            P.measurement_days = 7;
            scs = dt_scenario.definitions();
            sc = scs(6);
            Psc = dt_scenario.mergeParams(P, sc.override);
            [~, env, ~, ctrl] = dt_engine.run(Psc, sc);

            devT = dt_device.catalog();
            devT.device_id = (1:height(devT))';
            [measT, ~, ~] = dt_measurements.generate(Psc, env, ctrl, devT);

            testCase.verifyGreaterThan(min(measT.current_a), 0);
            testCase.verifyGreaterThan(min(measT.energy_kwh), 0);
            testCase.verifyGreaterThanOrEqual(min(measT.power_factor), 0.70);
            testCase.verifyLessThanOrEqual(max(measT.power_factor), 1);
            testCase.verifyGreaterThan(min(measT.thd_pct), 0);
        end

    end

end
