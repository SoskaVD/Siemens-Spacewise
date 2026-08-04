classdef dt_analysis
    %DT_ANALYSIS Construcción de tablas de resultados y perfiles para BD.
    %   Convierte la salida del motor (dt_engine.run) en tablas listas
    %   para insertar en simulation_results y subsystem_profiles.

    methods (Static)

        function T = resultsTable(res, P, base, ctrl)
            %RESULTSTABLE Tabla de KPIs por subsistema y TOTAL.
            FE = P.factor_co2_kg_kwh;
            subs = {'HVAC'; 'LAB'; 'IT'; 'ILUM'; 'BOMB'; 'AUX'; 'TOTAL'};
            n = numel(subs);
            subsystem = cell(n,1);
            Ebase = zeros(n,1); Ectrl = zeros(n,1); sav = zeros(n,1); savPct = zeros(n,1);
            peakB = zeros(n,1); peakC = zeros(n,1);
            co2B = zeros(n,1); co2C = zeros(n,1); co2A = zeros(n,1);
            rmse = NaN(n,1); mae = NaN(n,1); r2 = NaN(n,1);
            payback = NaN(n,1); van = NaN(n,1); tir = NaN(n,1);
            data = cell(n,1);

            for i = 1:numel(subs)
                s = subs{i};
                subsystem{i} = s;
                if strcmp(s, 'TOTAL')
                    Ebase(i) = res.Ebase; Ectrl(i) = res.Ectrl; sav(i) = res.Esav;
                    savPct(i) = res.savPct; peakB(i) = res.peakBase;
                    peakC(i) = res.peakCtrl; co2B(i) = res.co2Base; co2C(i) = res.co2Ctrl;
                    co2A(i) = res.co2Evitado;
                    rmse(i) = res.RMSE; mae(i) = res.MAE; r2(i) = res.R2;
                    payback(i) = res.payback; van(i) = res.VAN; tir(i) = res.TIR;
                    data{i} = jsonencode(struct('mode', res.mode, ...
                        'engine_version', res.engine_version, ...
                        'Ebase_kwh', res.Ebase, 'Ectrl_kwh', res.Ectrl, ...
                        'savings_kwh', res.Esav, 'savings_pct', res.savPct, ...
                        'peak_base_kw', res.peakBase, 'peak_ctrl_kw', res.peakCtrl, ...
                        'peak_reduction_pct', res.peakRedPct, ...
                        'co2_base_ton', res.co2Base, 'co2_ctrl_ton', res.co2Ctrl, ...
                        'co2_avoided_ton', res.co2Evitado, ...
                        'RMSE_kw', res.RMSE, 'MAE_kw', res.MAE, 'R2', res.R2, ...
                        'payback_years', res.payback, 'VAN_usd', res.VAN, ...
                        'TIR_pct', 100*res.TIR, 'flujo_usd', res.flujo));
                else
                    Ebase(i) = res.(['Ebase_' s]); Ectrl(i) = res.(['Ectrl_' s]);
                    sav(i) = res.(['sav_' s]); savPct(i) = res.(['savPct_' s]);
                    peakB(i) = max(base.(s)); peakC(i) = max(ctrl.(s));
                    co2B(i) = Ebase(i)*FE/1000; co2C(i) = Ectrl(i)*FE/1000;
                    co2A(i) = sav(i)*FE/1000;
                    data{i} = jsonencode(struct('savings_pct', savPct(i), ...
                        'peak_base_kw', peakB(i), 'peak_ctrl_kw', peakC(i)));
                end
            end

            T = table(subsystem, Ebase, Ectrl, sav, savPct, peakB, peakC, ...
                co2B, co2C, co2A, rmse, mae, r2, payback, van, tir, data, ...
                'VariableNames', {'subsystem','energy_base_kwh','energy_ctrl_kwh', ...
                'savings_kwh','savings_pct','peak_base_kw','peak_ctrl_kw', ...
                'co2_base_ton','co2_ctrl_ton','co2_avoided_ton', ...
                'rmse_kw','mae_kw','r2','payback_years','van_usd','tir_pct','data_json'});
        end

        function T = profilesTable(base, ctrl, env)
            %PROFILESTABLE Perfiles horarios por subsistema (formato largo).
            N = numel(env.hour);
            ts = string(env.ts, 'yyyy-MM-dd HH:mm:ss');
            subs = {'HVAC'; 'LAB'; 'IT'; 'ILUM'; 'BOMB'; 'AUX'; 'TOTAL'};
            nRows = numel(subs)*N;
            subCol = strings(nRows,1); tsCol = strings(nRows,1);
            pb = zeros(nRows,1); pc = zeros(nRows,1);
            row = 0;
            for i = 1:numel(subs)
                s = subs{i};
                if strcmp(s, 'TOTAL')
                    b = base.TOTAL; c = ctrl.total_final;
                else
                    b = base.(s); c = ctrl.(s);
                end
                idx = (1:N) + row;
                subCol(idx) = repmat(s, N, 1);
                tsCol(idx) = ts;
                pb(idx) = b; pc(idx) = c;
                row = row + N;
            end
            T = table(subCol, tsCol, pb, pc, ...
                'VariableNames', {'subsystem','ts','power_base_kw','power_ctrl_kw'});
        end

    end

end
