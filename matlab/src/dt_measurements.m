classdef dt_measurements
    %DT_MEASUREMENTS Generación de mediciones horarias por dispositivo.
    %   Desagrega el perfil horario de cada subsistema al nivel de
    %   dispositivo según su potencia nominal (share) y estado operativo,
    %   y deriva las magnitudes eléctricas (V, I, P, Q, PF, energía, THD).

    methods (Static)

        function [measT, envT, eventsT] = generate(P, env, ctrl, devTable)
            %GENERATE Genera las tablas de mediciones, ambiente y eventos.
            %   [measT, envT, eventsT] = dt_measurements.generate(P, env, ctrl, devTable)
            %   P        : parámetros.
            %   env      : estructura de ambiente (salida de dt_engine.run).
            %   ctrl     : perfiles controlados por subsistema (dt_engine.run).
            %   devTable : tabla de dispositivos (con device_id) desde la BD.
            %   measT    : tabla de mediciones por dispositivo y hora.
            %   envT     : tabla ambiental horaria.
            %   eventsT  : tabla de alarmas/anomalías.

            N = numel(env.hour);
            nsamp = min(N, round(P.measurement_days*24));
            ts = string(env.ts(1:nsamp), 'yyyy-MM-dd HH:mm:ss');
            hour = env.hour(1:nsamp);
            weekday = env.weekday(1:nsamp);
            ocup = env.ocup(1:nsamp);
            actLAB = env.actividadLAB(1:nsamp);
            solar = env.Solar(1:nsamp);

            cap = dt_device.installedCapacity(devTable);
            nDev = height(devTable);

            %% Estado operativo por dispositivo
            facCell = cell(nDev, 1);
            statCell = cell(nDev, 1);
            for d = 1:nDev
                if devTable.rated_power_kw(d) > 0
                    [facCell{d}, statCell{d}] = ...
                        dt_measurements.deviceState(devTable.type_code(d), ocup, actLAB, hour, weekday);
                else
                    facCell{d} = ones(nsamp, 1);
                    statCell{d} = repmat("ON", nsamp, 1);
                end
            end

            %% Renormalización: sum(P_dev) == P_subsistema por hora
            Ssub = containers.Map('KeyType', 'char', 'ValueType', 'any');
            for d = 1:nDev
                if devTable.rated_power_kw(d) <= 0
                    continue;
                end
                s = char(devTable.subsystem(d));
                share = devTable.rated_power_kw(d)/cap(s);
                if ~Ssub.isKey(s)
                    Ssub(s) = zeros(nsamp, 1);
                end
                Ssub(s) = Ssub(s) + share.*facCell{d};
            end

            %% Matriz de mediciones
            maxRows = nDev*nsamp;
            devId = zeros(maxRows, 1); vV = zeros(maxRows, 1); iA = zeros(maxRows, 1);
            pKw = zeros(maxRows, 1); qKvar = zeros(maxRows, 1); pfCol = zeros(maxRows, 1);
            eKwh = zeros(maxRows, 1); thdCol = zeros(maxRows, 1);
            stCol = strings(maxRows, 1); tsCol = strings(maxRows, 1);
            PdevCell = cell(nDev, 1); pfCell = cell(nDev, 1);

            row = 0;
            for d = 1:nDev
                s = char(devTable.subsystem(d));
                if strcmp(s, 'GENERAL')
                    Psub = ctrl.total_final(1:nsamp);
                else
                    Psub = ctrl.(s)(1:nsamp);
                end
                if devTable.rated_power_kw(d) > 0
                    share = devTable.rated_power_kw(d)/cap(s);
                    Pdev = Psub .* share .* facCell{d} ./ Ssub(s);
                else
                    Pdev = Psub;
                end
                Pdev = max(Pdev .* (1 + 0.01*randn(nsamp, 1)), 0);

                V = devTable.voltage_v(d) * (1 + 0.02*randn(nsamp, 1));
                pfV = min(max(devTable.pf_nominal(d) + 0.02*randn(nsamp, 1), 0.70), 0.99);
                if devTable.phases(d) == 3
                    I = Pdev*1000 ./ (sqrt(3)*V .* pfV);
                else
                    I = Pdev*1000 ./ (V .* pfV);
                end
                Q = Pdev .* tan(acos(pfV));
                E = Pdev * P.dt_h;
                thdV = max(devTable.thd_nominal_pct(d) + 0.5*randn(nsamp, 1), 0.2);

                idx = (1:nsamp) + row;
                devId(idx) = devTable.device_id(d);
                vV(idx) = V; iA(idx) = I; pKw(idx) = Pdev; qKvar(idx) = Q;
                pfCol(idx) = pfV; eKwh(idx) = E; thdCol(idx) = thdV;
                stCol(idx) = statCell{d}; tsCol(idx) = ts;
                PdevCell{d} = Pdev; pfCell{d} = pfV;
                row = row + nsamp;
            end
            idx = (1:row)';
            measT = table(tsCol(idx), devId(idx), vV(idx), iA(idx), pKw(idx), qKvar(idx), ...
                pfCol(idx), eKwh(idx), thdCol(idx), stCol(idx), ...
                'VariableNames', {'ts','device_id','voltage_v','current_a','active_power_kw', ...
                'reactive_power_kvar','power_factor','energy_kwh','thd_pct','status'});
            measT = movevars(measT, 'device_id', 'Before', 'ts');

            %% Tabla ambiental
            envT = table(ts, env.Text(1:nsamp), env.Hum(1:nsamp), env.co2(1:nsamp), ...
                ocup, solar*800, weekday, hour, ...
                'VariableNames', {'ts','temp_c','humidity_pct','co2_ppm','occupancy', ...
                'solar_wm2','weekday','hour'});

            %% Eventos (alarmas/anomalías)
            evMax = 4000;
            evDev = zeros(evMax, 1); evTs = strings(evMax, 1);
            evType = strings(evMax, 1); evSev = strings(evMax, 1);
            evMsg = strings(evMax, 1); evVal = zeros(evMax, 1);
            evRow = 0;
            for d = 1:nDev
                if devTable.rated_power_kw(d) <= 0
                    continue;
                end
                Pdev = PdevCell{d}; pfV = pfCell{d};
                rated = devTable.rated_power_kw(d);
                over = Pdev > rated*0.97;
                qual = pfV < 0.80;
                anom = Pdev > (mean(Pdev) + 3*std(Pdev));
                ovIdx = find(over);
                for k = 1:min(numel(ovIdx), 200)
                    evRow = evRow + 1;
                    if evRow > evMax, break; end
                    h = ovIdx(k);
                    evDev(evRow) = devTable.device_id(d); evTs(evRow) = ts(h);
                    evType(evRow) = "OVERLOAD"; evSev(evRow) = "HIGH";
                    evMsg(evRow) = sprintf('%s supera el 97%% de su potencia nominal', devTable.device_code{d});
                    evVal(evRow) = Pdev(h);
                end
                qIdx = find(qual);
                for k = 1:min(numel(qIdx), 200)
                    evRow = evRow + 1;
                    if evRow > evMax, break; end
                    h = qIdx(k);
                    evDev(evRow) = devTable.device_id(d); evTs(evRow) = ts(h);
                    evType(evRow) = "QUALITY"; evSev(evRow) = "MEDIUM";
                    evMsg(evRow) = sprintf('%s con factor de potencia bajo', devTable.device_code{d});
                    evVal(evRow) = pfV(h);
                end
                aIdx = find(anom);
                for k = 1:min(numel(aIdx), 200)
                    evRow = evRow + 1;
                    if evRow > evMax, break; end
                    h = aIdx(k);
                    evDev(evRow) = devTable.device_id(d); evTs(evRow) = ts(h);
                    evType(evRow) = "ANOMALY"; evSev(evRow) = "LOW";
                    evMsg(evRow) = sprintf('%s con consumo anómalo (>3 sigma)', devTable.device_code{d});
                    evVal(evRow) = Pdev(h);
                end
            end
            if evRow > 0
                i = (1:evRow)';
                eventsT = table(evDev(i), evTs(i), evType(i), evSev(i), evMsg(i), evVal(i), ...
                    'VariableNames', {'device_id','ts','event_type','severity','message','value'});
            else
                eventsT = table(zeros(0,1), strings(0,1), strings(0,1), strings(0,1), strings(0,1), zeros(0,1), ...
                    'VariableNames', {'device_id','ts','event_type','severity','message','value'});
            end
        end

    end

    methods (Static, Access = private)

        function [fac, status] = deviceState(type_code, ocup, actLAB, hour, weekday)
            %DEVICESTATE Estado operativo (ON/STANDBY) por tipo de equipo.
            %   Carga 24/7 (it) permanece ON; el resto entra en STANDBY
            %   según ocupación, actividad y horario.
            nsamp = numel(hour);
            t = string(type_code);
            fac = ones(nsamp, 1);
            status = repmat("ON", nsamp, 1);
            if t == "it"
                return;
            end
            workday = weekday < 5;
            dayH = hour >= 8 & hour <= 18;
            on = false(nsamp, 1);
            standbyFac = 0.15;
            switch t
                case "hvac"
                    on = ocup > 0.05 | (dayH & workday);
                case "lighting"
                    on = (dayH & workday & ocup > 0.10) | (hour >= 19 & hour <= 23);
                    standbyFac = 0.10;
                case "lab"
                    on = (dayH & workday & actLAB > 0.10) | (actLAB > 0.60);
                    standbyFac = 0.10;
                case {"pump", "fan"}
                    on = dayH & workday;
                otherwise % aux
                    on = dayH & workday;
                    standbyFac = 0.25;
            end
            off = ~on;
            fac(off) = standbyFac;
            status(off) = "STANDBY";
        end

    end

end
