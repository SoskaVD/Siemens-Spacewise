classdef simulacion_params
    %SIMULACION_PARAMS Parámetros globales del simulador de maquinaria industrial.
    %   Clase con constantes de configuración para la simulación de 110 máquinas
    %   industriales durante 8760 horas (1 año completo).
    %
    %   Ejemplo:
    %       params = simulacion_params;
    %       fprintf('Horas por año: %d\n', params.HOURS_PER_YEAR);
    
    properties (Constant)
        % Temporales
        HOURS_PER_YEAR = 8760;
        HOURS_PER_DAY = 24;
        DAYS_PER_WEEK = 7;
        WEEKS_PER_YEAR = 52.14;
        
        % Reproducibilidad
        DEFAULT_SEED = 42;
        
        % Rutas
        DB_PATH = 'data/spacewise.db';
        CATALOG_PATH = 'docs/CATALOGO_EQUIPOS.md';  % Solo referencia histórica / migración
        SCHEMA_PATH = 'data/schema_simulator.sql';
        MACHINES_DIR = 'machines';  % Catálogo modular: machines/<CODE>/machine.json
        
        % Categorías de máquinas
        CATEGORIES = {'HVAC', 'Compresores', 'Motores', 'Bombas', ...
                      'Iluminacion', 'Laboratorios', 'Manufactura', ...
                      'TI', 'Auxiliares'};
        
        % Estados operativos
        OP_STATES = {'RUNNING', 'PARTIAL', 'STANDBY', 'STARTUP', 'OFF'};
        
        % Niveles de criticidad
        CRITICALITY_LEVELS = {'CRITICA', 'ESENCIAL', 'FLEXIBLE', 'NO_CRITICA'};
        
        % Parámetros de simulación
        NOISE_STD_DEV = 0.05;          % Desviación estándar del ruido (5%)
        STARTUP_HOURS = 0.05;          % Horas que dura un arranque (3 min)
        
        % Performance
        BATCH_SIZE = 10000;            % Tamaño de lote para inserciones SQL
        
        % Versionado
        ENGINE_VERSION = '1.0.0';
    end
    
    methods (Static)
        function validateSeed(seed)
            %VALIDATESEED Valida que el seed sea un entero positivo.
            if ~isscalar(seed) || ~isnumeric(seed) || seed < 0 || seed ~= floor(seed)
                error('SIM:InvalidSeed', 'Seed must be a non-negative integer');
            end
        end
        
        function validateDbPath(path)
            %VALIDATEDBPATH Valida que la ruta de DB sea segura.
            if isempty(path) || ~ischar(path)
                error('SIM:InvalidDbPath', 'Database path must be a non-empty string');
            end
            % Prevenir path traversal
            if contains(path, '..')
                error('SIM:UnsafePath', 'Database path cannot contain ".."');
            end
        end
    end
end
