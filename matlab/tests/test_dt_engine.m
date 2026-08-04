classdef test_dt_engine < matlab.unittest.TestCase
    %TEST_DT_ENGINE Pruebas del motor del gemelo digital.

    methods (TestMethodSetup)
        function addPaths(testCase)
            p = fileparts(fileparts(mfilename('fullpath')));  % matlab/
            addpath(fullfile(p, 'src'), fullfile(p, 'config'));
        end
    end

    methods (Test)

        function baselineEnergy(testCase)
            % E_base = Area * EUI = 2 880 000 kWh
            P = spacewise_params();
            scs = dt_scenario.definitions();
            sc = scs(1);  % E0
            [res] = dt_engine.run(P, sc);
            testCase.verifyEqual(res.Ebase, P.area_m2*P.eui_kwh_m2_anio, 'RelTol', 1e-6, ...
                'La línea base debe ser Area*EUI');
        end

        function savingsInRange(testCase)
            % El escenario integral (E5) debe ahorrar entre 20% y 30%.
            P = spacewise_params();
            scs = dt_scenario.definitions();
            sc = scs(6);
            [res] = dt_engine.run(P, sc);
            testCase.verifyGreaterThanOrEqual(res.savPct, 20);
            testCase.verifyLessThanOrEqual(res.savPct, 30);
        end

        function peakReduction(testCase)
            % E5 debe reducir la demanda máxima al menos 10%.
            P = spacewise_params();
            scs = dt_scenario.definitions();
            sc = scs(6);
            [res] = dt_engine.run(P, sc);
            testCase.verifyGreaterThanOrEqual(res.peakRedPct, 10);
        end

        function predictionQuality(testCase)
            % El predictor lineal debe tener R2 > 0.9 y RMSE modesto.
            P = spacewise_params();
            scs = dt_scenario.definitions();
            sc = scs(6);
            [res] = dt_engine.run(P, sc);
            testCase.verifyGreaterThan(res.R2, 0.9);
            testCase.verifyLessThan(res.RMSE, 30);
        end

        function baselineHasNoSavings(testCase)
            % E0/E1 (base) no deben presentar ahorro.
            P = spacewise_params();
            scs = dt_scenario.definitions();
            sc = scs(1);
            [res] = dt_engine.run(P, sc);
            testCase.verifyEqual(res.savPct, 0, 'AbsTol', 1e-6);
        end

        function scenarioOverrideChangesEbase(testCase)
            % S01 (EUI 200) debe reducir la línea base vs la base E5.
            scs = dt_scenario.definitions();
            P = spacewise_params();
            Psc = dt_scenario.mergeParams(P, scs(7).override);
            [res] = dt_engine.run(Psc, scs(7));
            testCase.verifyLessThan(res.Ebase, 2.88e6);
            testCase.verifyEqual(res.Ebase, 12000*200, 'RelTol', 1e-6);
        end

    end

end
