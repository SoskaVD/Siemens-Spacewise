function P = spacewise_params()
%SPACEWISE_PARAMS Parámetros editables del gemelo digital SPACEWISE AI.
%   P = spacewise_params() devuelve la estructura de parámetros única de
%   entrada del modelo. Modifique este archivo para cambiar la simulación.
%
%   Referencia: docs/Grupo 3 Directrices ... SPACE WISE AI.pdf, Secciones 8 y 15.

%% Geometría y línea base
P.area_m2            = 12000;          % Área total climatizada (m2)
P.num_pisos          = 5;              % Número de pisos
P.num_subterraneos   = 2;              % Subterráneos
P.eui_kwh_m2_anio    = 240;            % Índice energético inicial (kWh/m2-año)
P.ocupacion_max      = 350;            % Ocupación máxima (personas)
P.dias_simulacion    = 365;            % Días simulados
P.dt_h               = 1;              % Resolución temporal (h/intervalo)

%% Participación energética por subsistema
P.fracHVAC = 0.38;
P.fracLAB  = 0.20;
P.fracIT   = 0.18;
P.fracILUM = 0.10;
P.fracBOMB = 0.06;
P.fracAUX  = 0.08;

%% Ahorro técnico por subsistema (escenario de control)
P.ahorroHVAC = 0.25;
P.ahorroLAB  = 0.18;
P.ahorroIT   = 0.10;
P.ahorroILUM = 0.40;
P.ahorroBOMB = 0.20;
P.ahorroAUX  = 0.12;

%% Economía
P.tarifa_usd_kwh      = 0.15;          % Tarifa promedio (USD/kWh)
P.factor_co2_kg_kwh   = 0.40;          % Factor de emisión (kgCO2/kWh)
P.capex_usd           = 310000;        % CAPEX preliminar (USD)
P.opex_usd_anio       = 12000;         % OPEX anual (USD/año)
P.tasa_descuento      = 0.10;          % Tasa de descuento
P.crecimiento_tarifa  = 0.025;         % Crecimiento anual de tarifa
P.degradacion_ahorro  = 0.005;         % Degradación anual del ahorro
P.horizonte_anios     = 10;            % Horizonte económico (años)

%% Límites operacionales y confort
P.t_confort     = 22;                  % Setpoint de confort (°C)
P.t_min         = 20;                  % Límite inferior (°C)
P.t_max         = 25;                  % Límite superior (°C)
P.peak_limite_kw = 500;                % Umbral de demanda máxima (kW)

%% Clima sintético
P.t_media    = 16;                  % Temperatura media anual (°C)
P.amp_anual  = 8;                   % Amplitud estacional (°C)
P.amp_diaria = 5;                   % Amplitud diaria (°C)
P.start_date = datetime(2026,1,1);  % Fecha de inicio de la simulación

%% Predicción (división de datos)
P.train_frac = 0.70;
P.val_frac   = 0.15;

%% Mediciones por dispositivo
P.measurement_days = 365;              % Ventana de mediciones (días). Use 28 para campaña de 4 semanas.

%% Reproducibilidad
P.rng_seed = 42;
end
