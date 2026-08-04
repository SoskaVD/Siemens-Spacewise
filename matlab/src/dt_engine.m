classdef dt_engine
    %DT_ENGINE Motor del gemelo digital energético SPACEWISE AI.
    %   Implementa el modelo matemático parametrizado de las directrices
    %   (Secciones 10 y 15): clima sintético, ocupación, perfiles por
    %   subsistema, escenarios de control, gestión de demanda, predicción
    %   por regresión y evaluación económica.

    methods (Static)

        function v = version()
            %VERSION Versión del motor.
            v = '1.0.0';
        end

        function [res, env, base, ctrl] = run(P, sc)
            %RUN Ejecuta la simulación del gemelo para un escenario.
            %   [res, env, base, ctrl] = dt_engine.run(P, sc)
            %   P  : parámetros (spacewise_params).
            %   sc : escenario (dt_scenario.definition) con campos:
            %        sc.mode       'base'|'horario'|'sensores'|'ahorro'|'integral'
            %        sc.peak_mgmt  logical (desplazamiento de carga en punta)
            %        sc.prediction logical (métricas de predicción)
            %   res  : KPIs y resultados (estructura).
            %   env  : variables ambientales (estructura con vectores horarios).
            %   base : perfiles base por subsistema (estructura de vectores).
            %   ctrl : perfiles controlados por subsistema (estructura de vectores).

            rng(P.rng_seed);

            %% 1. Eje temporal
            N = P.dias_simulacion * 24;
            t = (1:N)';
            hour = mod(t-1, 24);
            day = floor((t-1)/24) + 1;
            weekday = mod(day-1, 7);  % 0 = domingo

            %% 2. Clima sintético
            Text = P.t_media ...
                + P.amp_anual*sin(2*pi*(day-30)/P.dias_simulacion) ...
                + P.amp_diaria*sin(2*pi*(hour-14)/24) ...
                + 1.2*randn(N,1);
            Hum = 60 + 10*sin(2*pi*(day+40)/P.dias_simulacion) + 5*randn(N,1);
            Hum = min(max(Hum, 30), 90);
            Solar = zeros(N,1);
            idxSol = hour >= 7 & hour <= 19;
            Solar(idxSol) = sin(pi*(hour(idxSol)-7)/12);
            Solar = max(Solar, 0);

            %% 3. Ocupación y actividad técnica
            ocup = zeros(N,1);
            for k = 1:N
                if weekday(k) < 5 && hour(k) >= 8 && hour(k) <= 18
                    ocup(k) = 0.70 + 0.25*rand();
                elseif weekday(k) < 5 && hour(k) > 18 && hour(k) <= 22
                    ocup(k) = 0.15 + 0.10*rand();
                else
                    ocup(k) = 0.05 + 0.05*rand();
                end
            end
            ocup = min(max(ocup, 0), 1);

            actividadLAB = 0.15*ones(N,1);
            for k = 1:N
                if weekday(k) < 5 && hour(k) >= 9 && hour(k) <= 18
                    actividadLAB(k) = 0.55 + 0.40*rand();
                elseif rand() < 0.02
                    actividadLAB(k) = 0.80 + 0.20*rand();
                end
            end
            actividadLAB = min(actividadLAB, 1);

            %% 4. Energía anual objetivo por subsistema
            subs = {'HVAC'; 'LAB'; 'IT'; 'ILUM'; 'BOMB'; 'AUX'};
            frac = [P.fracHVAC P.fracLAB P.fracIT P.fracILUM P.fracBOMB P.fracAUX];
            Eobj = P.area_m2 * P.eui_kwh_m2_anio * frac;

            %% 5. Perfiles base
            perfil.HVAC = 0.35 + 0.40*ocup + 0.20*abs(Text-P.t_confort)/10 + 0.05*Solar;
            perfil.LAB  = 0.25 + 0.75*actividadLAB;
            perfil.IT   = 0.92 + 0.08*ocup;
            perfil.ILUM = 0.20 + 0.75*ocup.*(1 - 0.55*Solar);
            perfil.BOMB = 0.30 + 0.55*ocup + 0.15*actividadLAB;
            perfil.AUX  = 0.55 + 0.25*ocup + 0.20*actividadLAB;

            base = struct();
            for i = 1:numel(subs)
                s = subs{i};
                base.(s) = perfil.(s) * (Eobj(i)/sum(perfil.(s)));
            end
            base.TOTAL = base.HVAC + base.LAB + base.IT + base.ILUM + base.BOMB + base.AUX;

            %% 6. Perfiles controlados según el modo del escenario
            ahorro = [P.ahorroHVAC P.ahorroLAB P.ahorroIT P.ahorroILUM P.ahorroBOMB P.ahorroAUX];
            ctrl = struct();
            for i = 1:numel(subs)
                s = subs{i};
                switch sc.mode
                    case 'base'
                        ctrl.(s) = base.(s);
                    case 'horario'
                        ctrl.(s) = base.(s) .* dt_engine.scheduleFactor(P, s, hour, weekday);
                    case 'sensores'
                        ctrl.(s) = base.(s) .* dt_engine.sensorFactor(P, s, ocup);
                    otherwise % 'ahorro' | 'integral'
                        ctrl.(s) = base.(s) * (1 - ahorro(i));
                end
            end
            ctrl.TOTAL = ctrl.HVAC + ctrl.LAB + ctrl.IT + ctrl.ILUM + ctrl.BOMB + ctrl.AUX;

            %% 7. Gestión de demanda (desplazamiento de cargas flexibles)
            ctrl.total_final = ctrl.TOTAL;
            if sc.peak_mgmt
                esPunta = hour >= 18 & hour <= 22;
                exceso = max(ctrl.TOTAL - P.peak_limite_kw, 0);
                desplazable = min(exceso, 0.08*ctrl.LAB + 0.10*ctrl.AUX);
                desplazable(~esPunta) = 0;
                ctrl.total_final = ctrl.TOTAL - desplazable;
                EDesplazada = sum(desplazable);
                idxValle = hour >= 1 & hour <= 5;
                ctrl.total_final(idxValle) = ctrl.total_final(idxValle) + EDesplazada/sum(idxValle);
            end

            %% 8. Resultados energéticos y por subsistema
            res.Ebase = sum(base.TOTAL)*P.dt_h;
            res.Ectrl = sum(ctrl.total_final)*P.dt_h;
            res.Esav = res.Ebase - res.Ectrl;
            res.savPct = 100*res.Esav/res.Ebase;
            res.peakBase = max(base.TOTAL);
            res.peakCtrl = max(ctrl.total_final);
            res.peakRedPct = 100*(res.peakBase - res.peakCtrl)/res.peakBase;
            res.ahorroBruto = res.Esav*P.tarifa_usd_kwh;
            res.ahorroNeto1 = res.ahorroBruto - P.opex_usd_anio;
            res.co2Base = res.Ebase*P.factor_co2_kg_kwh/1000;        % ton
            res.co2Ctrl = res.Ectrl*P.factor_co2_kg_kwh/1000;        % ton
            res.co2Evitado = res.Esav*P.factor_co2_kg_kwh/1000;      % ton

            for i = 1:numel(subs)
                s = subs{i};
                res.(['Ebase_' s]) = sum(base.(s))*P.dt_h;
                res.(['Ectrl_' s]) = sum(ctrl.(s))*P.dt_h;
                res.(['sav_' s]) = res.(['Ebase_' s]) - res.(['Ectrl_' s]);
                res.(['savPct_' s]) = 100*res.(['sav_' s])/res.(['Ebase_' s]);
            end

            %% 9. Evaluación económica (VAN, TIR, payback)
            H = P.horizonte_anios;
            flujo = zeros(H+1,1);
            flujo(1) = -P.capex_usd;
            factorAnual = (1+P.crecimiento_tarifa)*(1-P.degradacion_ahorro);
            for y = 1:H
                flujo(y+1) = res.ahorroBruto*factorAnual^(y-1) - P.opex_usd_anio;
            end
            res.flujo = flujo;
            res.VAN = sum(flujo./(1+P.tasa_descuento).^(0:H)');
            funVAN = @(tir) sum(flujo./(1+tir).^(0:H)');
            try
                res.TIR = fzero(funVAN, [0.001 2]);
            catch
                res.TIR = NaN;
            end
            acum = cumsum(flujo);
            idx = find(acum >= 0, 1);
            if isempty(idx)
                res.payback = NaN;
            elseif idx == 1
                res.payback = 0;
            else
                saldoAnterior = -acum(idx-1);
                res.payback = (idx-2) + saldoAnterior/flujo(idx);
            end

            %% 10. Predicción de demanda (regresión multivariable)
            res.RMSE = NaN; res.MAE = NaN; res.R2 = NaN;
            res.Ypred = []; res.Ytest = [];
            if sc.prediction
                X = [ones(N,1), Text, Hum, Solar, ocup, actividadLAB, ...
                    sin(2*pi*hour/24), cos(2*pi*hour/24)];
                Y = base.TOTAL;
                Ntrain = round(P.train_frac*N);
                Nval = round(P.val_frac*N);
                Xtrain = X(1:Ntrain, :); Ytrain = Y(1:Ntrain);
                Xtest = X(Ntrain+Nval+1:end, :); Ytest = Y(Ntrain+Nval+1:end);
                beta = Xtrain\Ytrain;
                Ypred = Xtest*beta;
                res.RMSE = sqrt(mean((Ytest-Ypred).^2));
                res.MAE = mean(abs(Ytest-Ypred));
                res.R2 = 1 - sum((Ytest-Ypred).^2)/sum((Ytest-mean(Ytest)).^2);
                res.Ypred = Ypred; res.Ytest = Ytest;
            end

            %% 11. Variables ambientales de salida
            env.ts = P.start_date + hours(t-1);
            env.hour = hour; env.day = day; env.weekday = weekday;
            env.Text = Text; env.Hum = Hum; env.Solar = Solar;
            env.ocup = ocup; env.actividadLAB = actividadLAB;
            env.co2 = min(max(420 + 500*ocup + 10*randn(N,1), 380), 1400);

            res.subsystems = subs;
            res.engine_version = dt_engine.version();
            res.mode = sc.mode;
        end

    end

    methods (Static, Access = private)

        function f = scheduleFactor(~, s, hour, weekday)
            %SCHEDULEFACTOR Factor de control horario (escenario E2).
            %   Carga 24/7 (IT) no se reduce; el resto sigue el horario
            %   laboral con niveles día/tarde/noche/fin de semana.
            f = ones(size(hour));
            if strcmp(s, 'IT')
                return;
            end
            work = weekday < 5;
            dayH = hour >= 8 & hour <= 18;
            eve  = hour > 18 & hour <= 22;
            f(work & dayH)  = 1.00;
            f(work & eve)   = 0.55;
            f(work & ~dayH & ~eve) = 0.30;
            f(~work) = 0.30;
            switch s
                case {'ILUM', 'AUX', 'BOMB'}
                    f = 0.7*f + 0.3;   % reducción más moderada
            end
        end

        function f = sensorFactor(~, s, ocup)
            %SENSORFACTOR Factor de regulación por sensores/ocupación (E3).
            switch s
                case 'ILUM'
                    f = 0.25 + 0.75*ocup;
                case 'HVAC'
                    f = 0.55 + 0.45*ocup;
                case {'BOMB', 'AUX'}
                    f = 0.65 + 0.35*ocup;
                case 'LAB'
                    f = 0.30 + 0.70*ocup;
                otherwise  % IT
                    f = ones(size(ocup));
            end
        end

    end

end
