classdef dt_scenario
    %DT_SCENARIO Definición de escenarios y variaciones del gemelo.
    %   Escenarios E0-E5 (Fase 6 de las directrices) y barridos de
    %   sensibilidad (S01-S05). Cada escenario contiene un conjunto de
    %   modificaciones (override) aplicadas a los parámetros base.

    methods (Static)

        function scs = definitions()
            %DEFINITIONS Devuelve el arreglo de escenarios predefinidos.
            scs = struct('scenario_code', {}, 'name', {}, 'description', {}, ...
                'mode', {}, 'peak_mgmt', {}, 'prediction', {}, ...
                'is_baseline', {}, 'override', {});
            add('E0', 'Operación actual (base)', 'Línea base sin control.', ...
                'base', false, false, true, struct());
            add('E1', 'Solo medición', 'Se registra la operación sin control (medición).', ...
                'base', false, false, false, struct());
            add('E2', 'Control horario', 'Horarios fijos de operación (día/tarde/noche/fin de semana).', ...
                'horario', false, false, false, struct());
            add('E3', 'Sensores y regulación', 'Regulación por ocupación y presencia.', ...
                'sensores', false, false, false, struct());
            add('E4', 'IA predictiva', 'Ahorros técnicos por subsistema + predicción de demanda.', ...
                'ahorro', false, true, false, struct());
            add('E5', 'Gemelo digital + control integral', ...
                'E4 + gestión de demanda (desplazamiento de peak) + predicción.', ...
                'integral', true, true, false, struct());
            add('S01', 'Sensibilidad EUI 200', 'Barrido: índice energético 200 kWh/m2-año.', ...
                'integral', true, true, false, struct('eui_kwh_m2_anio', 200));
            add('S02', 'Sensibilidad EUI 280', 'Barrido: índice energético 280 kWh/m2-año.', ...
                'integral', true, true, false, struct('eui_kwh_m2_anio', 280));
            add('S03', 'Sensibilidad ahorro HVAC 30%', 'Barrido: ahorro técnico HVAC 30%.', ...
                'integral', true, true, false, struct('ahorroHVAC', 0.30));
            add('S04', 'Sensibilidad tarifa 0.12', 'Barrido: tarifa 0,12 USD/kWh.', ...
                'integral', true, true, false, struct('tarifa_usd_kwh', 0.12));
            add('S05', 'Sensibilidad tarifa 0.18', 'Barrido: tarifa 0,18 USD/kWh.', ...
                'integral', true, true, false, struct('tarifa_usd_kwh', 0.18));

            function add(code, name, desc, mode, peak, pred, baseFlag, override)
                scs(end+1) = struct('scenario_code', code, 'name', name, ...
                    'description', desc, 'mode', mode, 'peak_mgmt', peak, ...
                    'prediction', pred, 'is_baseline', baseFlag, 'override', override); %#ok<AGROW>
            end
        end

        function P = mergeParams(P, override)
            %MERGEPARAMS Aplica las modificaciones de un escenario a los parámetros.
            %   P = dt_scenario.mergeParams(P, sc.override)
            if isempty(override)
                return;
            end
            fields = fieldnames(override);
            for k = 1:numel(fields)
                P.(fields{k}) = override.(fields{k});
            end
        end

    end

end
