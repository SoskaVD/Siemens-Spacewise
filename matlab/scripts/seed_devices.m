% 02_seed_devices.m - Siembra el catálogo de tipos y dispositivos en la BD.
% Uso: ejecutar después de 01_init_db.m.

projectRoot = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot, 'src'), fullfile(projectRoot, 'config'));

repoRoot = fileparts(projectRoot);
dbPath = fullfile(repoRoot, 'bd', 'spacewise.db');

conn = dt_db.open(dbPath);

conn.execute('DELETE FROM devices');
conn.execute('DELETE FROM device_types');
dt_db.insertDeviceTypes(conn, dt_device.types());
dt_db.insertDevices(conn, dt_device.catalog());

devices = conn.fetch('SELECT device_id, device_code, name, type_code, subsystem, criticality, rated_power_kw FROM devices ORDER BY device_id');
fprintf('Dispositivos registrados: %d\n', height(devices));
disp(devices);

cap = dt_device.installedCapacity(devices);
keys = cap.keys;
fprintf('\nCapacidad instalada por subsistema (kW):\n');
for k = 1:numel(keys)
    fprintf('  %-6s %8.1f\n', keys{k}, cap(keys{k}));
end

dt_db.close(conn);
