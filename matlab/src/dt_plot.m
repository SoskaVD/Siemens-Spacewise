classdef dt_plot
    %DT_PLOT Generación de gráficos y exportación de resultados.
    %   figuras  : gráficos a partir de la salida del motor (una corrida).
    %   fromDB   : comparación E0 vs E5 y reportes leyendo la base SQLite.
    %   exportCSV: exporta resultados de la base a CSV.

    methods (Static)

        function figures(base, ctrl, env, res, outDir)
            %FIGURES Genera y guarda los gráficos de una simulación.
            if ~exist(outDir, 'dir')
                mkdir(outDir);
            end
            T = 168; % primera semana
            t = env.ts(1:T);

            figure('Visible','off','Position',[100 100 900 500]);
            plot(t, base.TOTAL(1:T), 'LineWidth', 1.3); hold on;
            plot(t, ctrl.total_final(1:T), 'LineWidth', 1.3);
            grid on; xlabel('Fecha'); ylabel('Potencia [kW]');
            title(sprintf('SPACEWISE AI (%s): semana base vs control', res.mode));
            legend('Base', 'Control', 'Location','best');
            exportgraphics(gcf, fullfile(outDir, 'fig_semana.png'));
            close(gcf);

            figure('Visible','off','Position',[100 100 900 500]);
            subs = {'HVAC';'LAB';'IT';'ILUM';'BOMB';'AUX'};
            baseE = zeros(6,1); ctrlE = zeros(6,1);
            for i = 1:6
                baseE(i) = res.(['Ebase_' subs{i}])/1000;
                ctrlE(i) = res.(['Ectrl_' subs{i}])/1000;
            end
            bar([baseE ctrlE]);
            grid on; ylabel('Energía [MWh/año]');
            title(sprintf('SPACEWISE AI (%s): consumo por subsistema', res.mode));
            legend('Base','Control'); xticklabels(subs);
            exportgraphics(gcf, fullfile(outDir, 'fig_subsistemas.png'));
            close(gcf);

            if ~isempty(res.Ytest)
                figure('Visible','off','Position',[100 100 900 500]);
                plot(res.Ytest(1:T), 'LineWidth', 1.2); hold on;
                plot(res.Ypred(1:T), 'LineWidth', 1.2);
                grid on; xlabel('Hora'); ylabel('Potencia [kW]');
                title(sprintf('Predicción de demanda (RMSE %.1f kW, R2 %.3f)', res.RMSE, res.R2));
                legend('Real simulado','Predicción','Location','best');
                exportgraphics(gcf, fullfile(outDir, 'fig_prediccion.png'));
                close(gcf);
            end

            if isfield(res, 'flujo')
                figure('Visible','off','Position',[100 100 900 500]);
                bar(0:(numel(res.flujo)-1), res.flujo);
                grid on; xlabel('Año'); ylabel('Flujo de caja [USD]');
                title('Flujo económico SPACEWISE AI');
                exportgraphics(gcf, fullfile(outDir, 'fig_flujo.png'));
                close(gcf);
            end
        end

        function fromDB(dbPath, outDir)
            %FROMDB Reporte comparativo E0 vs E5 desde la base SQLite.
            if ~exist(outDir, 'dir')
                mkdir(outDir);
            end
            conn = dt_db.open(dbPath);
            sumT = dt_plot.summaryTable(conn);

            e0 = sumT(strcmp(sumT.scenario_code, 'E0'), :);
            e5 = sumT(strcmp(sumT.scenario_code, 'E5'), :);
            if isempty(e0) || isempty(e5)
                fprintf('No hay datos E0/E5 para graficar.\n');
                dt_db.close(conn);
                return;
            end
            simE0 = e0.simulation_id(1); simE5 = e5.simulation_id(1);

            % semana base vs control (E5)
            prof5 = conn.fetch(sprintf("SELECT ts, power_base_kw, power_ctrl_kw FROM subsystem_profiles WHERE simulation_id=%d AND subsystem='TOTAL' ORDER BY ts", simE5));
            t = datetime(prof5.ts);
            figure('Visible','off','Position',[100 100 900 500]);
            plot(t(1:168), prof5.power_base_kw(1:168), 'LineWidth', 1.3); hold on;
            plot(t(1:168), prof5.power_ctrl_kw(1:168), 'LineWidth', 1.3);
            grid on; xlabel('Fecha'); ylabel('Potencia [kW]');
            title('Semana E0 (base) vs E5 (gemelo integral)');
            legend('Base (E0)','Control (E5)','Location','best');
            exportgraphics(gcf, fullfile(outDir, 'report_semana_E0_E5.png'));
            close(gcf);

            % barras por subsistema E0 vs E5
            order = {'HVAC','LAB','IT','ILUM','BOMB','AUX'};
            sql = sprintf("SELECT r.simulation_id, r.subsystem, r.energy_base_kwh, r.energy_ctrl_kwh FROM simulation_results r WHERE r.simulation_id IN (%d,%d) AND r.subsystem <> 'TOTAL'", simE0, simE5);
            subT = conn.fetch(sql);
            b0 = zeros(6,1); b5 = zeros(6,1);
            for i = 1:6
                r0 = subT(subT.simulation_id == simE0 & strcmp(subT.subsystem, order{i}), :);
                r5 = subT(subT.simulation_id == simE5 & strcmp(subT.subsystem, order{i}), :);
                b0(i) = r0.energy_base_kwh(1)/1000;
                b5(i) = r5.energy_ctrl_kwh(1)/1000;
            end
            figure('Visible','off','Position',[100 100 900 500]);
            bar([b0 b5]);
            grid on; ylabel('Energía [MWh/año]');
            title('Consumo por subsistema: E0 vs E5');
            legend('E0 base','E5 control'); xticklabels(order);
            exportgraphics(gcf, fullfile(outDir, 'report_subsistemas_E0_E5.png'));
            close(gcf);

            % flujo económico E5 desde data_json
            d5 = jsondecode(e5.data_json);
            if isfield(d5, 'flujo_usd')
                figure('Visible','off','Position',[100 100 900 500]);
                bar(0:(numel(d5.flujo_usd)-1), d5.flujo_usd);
                grid on; xlabel('Año'); ylabel('Flujo de caja [USD]');
                title('Flujo económico E5');
                exportgraphics(gcf, fullfile(outDir, 'report_flujo_E5.png'));
                close(gcf);
            end

            fprintf('Resumen de escenarios (TOTAL):\n');
            disp(sumT(:, {'scenario_code','name','savings_pct','peak_reduction','co2_avoided_ton','payback_years','van_usd','tir_pct'}));
            dt_db.close(conn);
        end

        function exportCSV(dbPath, outDir)
            %EXPORTCSV Exporta los resultados de la base a CSV.
            if ~exist(outDir, 'dir')
                mkdir(outDir);
            end
            conn = dt_db.open(dbPath);
            sumT = dt_plot.summaryTable(conn);
            writetable(sumT, fullfile(outDir, 'resultados_escenarios.csv'));

            sims = conn.fetch("SELECT s.scenario_code, sim.simulation_id FROM simulations sim JOIN scenarios s ON sim.scenario_id=s.scenario_id ORDER BY s.scenario_code");
            if height(sims) > 0
                meas = conn.fetch(sprintf("SELECT m.* FROM measurements m WHERE m.simulation_id=%d ORDER BY m.device_id, m.ts LIMIT 2000", sims.simulation_id(1)));
                writetable(meas, fullfile(outDir, 'mediciones_muestra.csv'));
                ev = conn.fetch(sprintf("SELECT e.* FROM events e WHERE e.simulation_id=%d ORDER BY e.event_id", sims.simulation_id(1)));
                writetable(ev, fullfile(outDir, 'eventos.csv'));
            end
            dt_db.close(conn);
            fprintf('CSV exportados a %s\n', outDir);
        end

    end

    methods (Static, Access = private)

        function T = summaryTable(conn)
            %SUMMARYTABLE Resumen de escenarios (subsistema TOTAL).
            sql = "SELECT sc.scenario_code, sc.name, " + ...
                "r.energy_base_kwh, r.energy_ctrl_kwh, r.savings_kwh, r.savings_pct, " + ...
                "r.peak_base_kw, r.peak_ctrl_kw, " + ...
                "100*(r.peak_base_kw - r.peak_ctrl_kw)/NULLIF(r.peak_base_kw,0) AS peak_reduction, " + ...
                "r.co2_avoided_ton, " + ...
                "COALESCE(r.rmse_kw,0) AS rmse_kw, COALESCE(r.mae_kw,0) AS mae_kw, " + ...
                "COALESCE(r.r2,0) AS r2, COALESCE(r.payback_years,0) AS payback_years, " + ...
                "COALESCE(r.van_usd,0) AS van_usd, COALESCE(r.tir_pct,0) AS tir_pct, " + ...
                "r.data_json, sim.simulation_id " + ...
                "FROM simulation_results r " + ...
                "JOIN simulations sim ON r.simulation_id = sim.simulation_id " + ...
                "JOIN scenarios sc ON sim.scenario_id = sc.scenario_id " + ...
                "WHERE r.subsystem = 'TOTAL' ORDER BY sc.scenario_code";
            T = conn.fetch(sql);
        end

    end

end
