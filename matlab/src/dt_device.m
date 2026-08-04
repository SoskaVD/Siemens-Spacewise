classdef dt_device
    %DT_DEVICE Catálogo de dispositivos eléctricos del gemelo digital SPACEWISE AI.
%   Funciones:
%     T = dt_device.types()          tabla de tipos de dispositivo
%     T = dt_device.catalog()        tabla de dispositivos (catálogo inicial)
%     m = dt_device.installedCapacity(T)  mapa subsistema -> capacidad instalada (kW)
%
%   Para añadir dispositivos: agregue una fila a catalog() (Sección 9.1 del plan).

methods (Static)

    function T = types()
        %TYPES Catálogo de tipos de dispositivo.
        type_code = {'meter'; 'hvac'; 'lighting'; 'pump'; 'fan'; 'lab'; 'it'; 'aux'};
        type_name = {'Analizador de redes / medidor'; 'Climatización'; 'Iluminación'; ...
            'Bomba'; 'Ventilación'; 'Cargas de laboratorio'; 'TI / UPS / Datos'; ...
            'Servicios auxiliares y exteriores'};
        description = {'Medición Siemens SENTRON (PAC)'; ...
            'Unidades manejadoras de aire, chillers y fan-coils'; ...
            'Circuitos de iluminación interior y exterior'; ...
            'Bombas con variador de velocidad'; ...
            'Ventiladores y extracción'; ...
            'Equipos de laboratorio y bancos de prueba'; ...
            'Centro de datos, servidores, UPS y comunicaciones'; ...
            'Ascensores, CCTV, enchufes y cargas exteriores'};
        T = table(type_code, type_name, description);
    end

    function T = catalog()
        %CATALOG Catálogo inicial de dispositivos del CEN.
        %   La potencia nominal (rated_power_kw) define el reparto del consumo
        %   dentro de cada subsistema: share = P_nom / sum(P_nom del subsistema).
        code = { 'MET-01'; 'MET-02'; 'MET-03'; 'MET-04'; 'MET-05';
            'HVAC-01'; 'HVAC-02'; 'HVAC-03'; 'HVAC-04'; 'HVAC-05';
            'LIGHT-01'; 'LIGHT-02';
            'LAB-01'; 'LAB-02'; 'LAB-03';
            'IT-01'; 'IT-02';
            'PUMP-01'; 'PUMP-02'; 'FAN-01';
            'AUX-01'; 'AUX-02' };
        name = { 'Analizador Tablero General BT'; 'Analizador Tablero HVAC';
            'Analizador Tablero Laboratorios'; 'Analizador Tablero Iluminación';
            'Analizador Tablero Auxiliares';
            'AHU Principal Zona Este'; 'AHU Secundaria Zona Oeste';
            'Climatización Precisión Sala Limpia'; 'Fan-coil Oficinas Sur';
            'Fan-coil Oficinas Norte';
            'Circuito Iluminación Interior LED'; 'Circuito Iluminación Exterior';
            'Laboratorio Electrónico 1'; 'Laboratorio Electrónico 2';
            'Banco de Pruebas Satelital';
            'UPS Centro de Datos'; 'Servidores y Comunicaciones';
            'Bomba Primaria'; 'Bomba Secundaria'; 'Ventilación Auxiliar';
            'Ascensor y equipos auxiliares'; 'Cargas exteriores y seguridad' };
        type_code = { 'meter'; 'meter'; 'meter'; 'meter'; 'meter';
            'hvac'; 'hvac'; 'hvac'; 'hvac'; 'hvac';
            'lighting'; 'lighting';
            'lab'; 'lab'; 'lab';
            'it'; 'it';
            'pump'; 'pump'; 'fan';
            'aux'; 'aux' };
        subsystem = { 'GENERAL'; 'HVAC'; 'LAB'; 'ILUM'; 'AUX';
            'HVAC'; 'HVAC'; 'HVAC'; 'HVAC'; 'HVAC';
            'ILUM'; 'ILUM';
            'LAB'; 'LAB'; 'LAB';
            'IT'; 'IT';
            'BOMB'; 'BOMB'; 'BOMB';
            'AUX'; 'AUX' };
        criticality = { 'CRITICA'; 'CRITICA'; 'CRITICA'; 'ESENCIAL'; 'ESENCIAL';
            'ESENCIAL'; 'FLEXIBLE'; 'CRITICA'; 'FLEXIBLE'; 'FLEXIBLE';
            'FLEXIBLE'; 'NO_CRITICA';
            'ESENCIAL'; 'ESENCIAL'; 'CRITICA';
            'CRITICA'; 'CRITICA';
            'ESENCIAL'; 'ESENCIAL'; 'FLEXIBLE';
            'ESENCIAL'; 'NO_CRITICA' };
        manufacturer = { 'Siemens'; 'Siemens'; 'Siemens'; 'Siemens'; 'Siemens';
            'Siemens'; 'Siemens'; 'Siemens'; 'Carrier'; 'Carrier';
            'Philips'; 'Philips';
            'Keithley'; 'Keithley'; 'National Instruments';
            'Schneider'; 'Dell';
            'Siemens'; 'Siemens'; 'Siemens';
            'Otis'; 'Axis' };
        model = { 'SENTRON PAC4200'; 'SENTRON PAC3200'; 'SENTRON PAC3200';
            'SENTRON PAC2200'; 'SENTRON PAC2200';
            'AHU + SINAMICS G120'; 'AHU'; 'Sala limpia'; 'FCU'; 'FCU';
            'LED'; 'LED';
            'Bancos de carga'; 'Bancos de carga'; 'Integración satelital';
            'UPS'; 'Racks';
            'SINAMICS G120'; 'SINAMICS G120'; 'SINAMICS G120';
            'Elevador'; 'CCTV / alumbrado' };
        rated_power_kw = [ 0; 0; 0; 0; 0;
            120; 80; 150; 45; 45;
            30; 20;
            60; 60; 90;
            100; 70;
            25; 25; 15;
            15; 20 ];
        pf_nominal = [ 0.95; 0.92; 0.88; 0.95; 0.90;
            0.90; 0.90; 0.92; 0.88; 0.88;
            0.98; 0.98;
            0.85; 0.85; 0.85;
            0.95; 0.95;
            0.86; 0.86; 0.85;
            0.85; 0.90 ];
        thd_nominal_pct = [ 2.0; 2.5; 3.0; 2.0; 2.5;
            4.0; 4.0; 3.0; 5.0; 5.0;
            1.5; 1.5;
            5.0; 5.0; 4.0;
            2.0; 3.0;
            4.0; 4.0; 5.0;
            3.0; 2.0 ];
        voltage_v = [ 400; 400; 400; 230; 400;
            400; 400; 400; 400; 400;
            230; 230;
            400; 400; 400;
            400; 400;
            400; 400; 400;
            400; 230 ];
        phases = [ 3; 3; 3; 1; 3;
            3; 3; 3; 3; 3;
            1; 1;
            3; 3; 3;
            3; 3;
            3; 3; 3;
            3; 1 ];
        location = { 'Tablero General BT'; 'Tablero HVAC'; 'Tablero Laboratorios';
            'Tablero Iluminación'; 'Tablero Auxiliares';
            'Sala Técnica Este'; 'Sala Técnica Oeste'; 'Sala Limpia'; 'Oficinas Sur';
            'Oficinas Norte';
            'Pisos 1-5'; 'Perímetro';
            'Lab Electrónico 1'; 'Lab Electrónico 2'; 'Sala de Integración';
            'Centro de Datos'; 'Centro de Datos';
            'Sala de Bombas'; 'Sala de Bombas'; 'Cubierta';
            'Hall / núcleos'; 'Exteriores' };
        install_date = repmat("2026-01-01", numel(code), 1);
        active = ones(numel(code), 1);
        metadata_json = repmat("", numel(code), 1);

        T = table(code, name, type_code, subsystem, criticality, manufacturer, model, ...
            rated_power_kw, pf_nominal, thd_nominal_pct, voltage_v, phases, location, ...
            install_date, active, metadata_json, ...
            'VariableNames', {'device_code','name','type_code','subsystem','criticality', ...
            'manufacturer','model','rated_power_kw','pf_nominal','thd_nominal_pct', ...
            'voltage_v','phases','location','install_date','active','metadata_json'});
    end

    function m = installedCapacity(T)
        %INSTALLEDCAPACITY Capacidad instalada por subsistema (solo consumo).
        %   m es un containers.Map subsistema -> kW.
        cons = T(T.rated_power_kw > 0, :);
        subs = unique(string(cons.subsystem));
        m = containers.Map('KeyType','char','ValueType','double');
        for k = 1:numel(subs)
            idx = strcmp(cons.subsystem, subs{k});
            m(subs{k}) = sum(cons.rated_power_kw(idx));
        end
    end

end

end
