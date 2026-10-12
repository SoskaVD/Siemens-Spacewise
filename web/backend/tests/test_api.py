"""Pytest tests for the Simulator API.

Tests cover:
- All API endpoints (happy path)
- Error cases (invalid IDs, missing data, bad formats)
- SQL injection attempts (must be blocked)
- Input validation
- CORS headers
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

import app as app_module
from app import create_app


@pytest.fixture
def temp_db():
    """Create a temporary database with test data."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    db_path = tmp.name

    # Load schema first
    schema_path = Path(__file__).parent.parent.parent.parent / 'data' / 'schema_simulator.sql'
    if schema_path.exists():
        schema_sql = schema_path.read_text()
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_sql)
        conn.close()

    # Insert test data
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        -- Machines
        INSERT INTO machines (
            machine_id, machine_code, name, category, rated_power_kw,
            voltage_v, current_a, power_factor, phases, thd_pct,
            hours_per_day, days_per_week, load_factor, criticality, active
        ) VALUES
        (1, 'HVAC-001', 'Chiller Unit A', 'HVAC', 150.0, 480.0, 200.0, 0.85, 3, 5.0,
         18.0, 6.0, 0.75, 'ESENCIAL', 1),
        (2, 'COMP-015', 'Compressor B', 'Compresores', 75.0, 480.0, 100.0, 0.88, 3, 4.5,
         12.0, 5.0, 0.60, 'CRITICA', 1),
        (3, 'MOT-042', 'Motor C', 'Motores', 50.0, 480.0, 70.0, 0.90, 3, 3.0,
         24.0, 7.0, 0.85, 'NO_CRITICA', 1),
        (4, 'PUMP-007', 'Inactive Pump', 'Bombas', 25.0, 480.0, 35.0, 0.80, 3, 2.0,
         8.0, 5.0, 0.50, 'FLEXIBLE', 0);

        -- Simulations
        INSERT INTO simulations (
            simulation_id, simulation_code, name, description, status,
            total_machines, total_hours
        ) VALUES
        (1, 'SIM-2026-001', 'Baseline Simulation', 'First run', 'COMPLETED', 3, 8760),
        (2, 'SIM-2026-002', 'Alternative Scenario', 'Second run', 'COMPLETED', 3, 8760);

        -- Hourly totals (just a few rows for test efficiency)
        INSERT INTO hourly_totals (
            simulation_id, ts, hour_index, total_power_kw, total_energy_kwh,
            hvac_power_kw, compressors_power_kw, motors_power_kw
        ) VALUES
        (1, '2026-01-01 00:00:00', 0, 275.0, 275.0, 150.0, 75.0, 50.0),
        (1, '2026-01-01 01:00:00', 1, 260.0, 260.0, 140.0, 70.0, 50.0),
        (1, '2026-01-01 02:00:00', 2, 250.0, 250.0, 130.0, 70.0, 50.0),
        (2, '2026-01-01 00:00:00', 0, 280.0, 280.0, 155.0, 75.0, 50.0);

        -- Simulation results
        INSERT INTO simulation_results (
            simulation_id, total_energy_kwh, avg_power_kw, peak_power_kw, peak_ts,
            energy_by_category_json, top_machines_json
        ) VALUES
        (1, 2400000.0, 273.97, 450.0, '2026-07-15 14:00:00',
         '{"HVAC": 1200000, "Compresores": 800000, "Motores": 400000}',
         '[{"code": "HVAC-001", "energy": 1200000}, {"code": "COMP-015", "energy": 800000}]'),
        (2, 2500000.0, 285.0, 460.0, '2026-07-15 14:00:00',
         '{"HVAC": 1250000, "Compresores": 830000, "Motores": 420000}',
         '[{"code": "HVAC-001", "energy": 1250000}]');

        -- Machine measurements (small sample)
        INSERT INTO machine_measurements (
            simulation_id, machine_id, ts, hour_index, active_power_kw,
            energy_kwh, load_factor, operation_state
        ) VALUES
        (1, 1, '2026-01-01 00:00:00', 0, 150.0, 150.0, 0.85, 'RUNNING'),
        (1, 1, '2026-01-01 01:00:00', 1, 140.0, 140.0, 0.80, 'RUNNING'),
        (1, 2, '2026-01-01 00:00:00', 0, 75.0, 75.0, 0.60, 'RUNNING'),
        (1, 2, '2026-01-01 01:00:00', 1, 70.0, 70.0, 0.55, 'PARTIAL');
    """)
    conn.commit()
    conn.close()

    yield db_path

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def client(temp_db):
    """Create a test client with the temporary database."""
    app = create_app(db_path=temp_db)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'
        assert data['database'] == 'connected'


class TestMachinesEndpoint:
    def test_list_machines_returns_active_only(self, client):
        resp = client.get('/api/machines')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 3  # Inactive machine excluded
        codes = [m['machine_code'] for m in data['machines']]
        assert 'PUMP-007' not in codes

    def test_get_machine_by_code(self, client):
        resp = client.get('/api/machines/HVAC-001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['machine_code'] == 'HVAC-001'
        assert data['name'] == 'Chiller Unit A'
        assert data['category'] == 'HVAC'

    def test_get_machine_not_found(self, client):
        resp = client.get('/api/machines/XYZ-999')
        assert resp.status_code == 404

    def test_get_machine_invalid_code_format(self, client):
        # SQL injection attempt via machine code
        resp = client.get("/api/machines/HVAC-001' OR '1'='1")
        assert resp.status_code == 400

    def test_get_machine_sql_injection_attempt(self, client):
        # Various SQL injection patterns must all be rejected
        injection_attempts = [
            "HVAC-001; DROP TABLE machines",
            "HVAC-001' UNION SELECT * FROM machines--",
            "HVAC-001'; DELETE FROM machines;--",
            "'; DROP TABLE machines;--",
        ]
        for attempt in injection_attempts:
            resp = client.get(f'/api/machines/{attempt}')
            assert resp.status_code == 400, f"Injection not blocked: {attempt}"


class TestSimulationsEndpoint:
    def test_list_simulations(self, client):
        resp = client.get('/api/simulations')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 2
        # Newest first
        assert data['simulations'][0]['simulation_id'] == 2

    def test_get_simulation_summary(self, client):
        resp = client.get('/api/simulations/1/summary')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total_energy_kwh'] == 2400000.0
        assert data['peak_power_kw'] == 450.0

    def test_get_simulation_summary_not_found(self, client):
        resp = client.get('/api/simulations/999/summary')
        assert resp.status_code == 404

    def test_get_simulation_summary_invalid_id(self, client):
        resp = client.get('/api/simulations/0/summary')
        assert resp.status_code == 400

    def test_get_simulation_summary_negative_id(self, client):
        resp = client.get('/api/simulations/-1/summary')
        # Flask will return 404 for negative int in URL pattern
        assert resp.status_code in (400, 404)


class TestHourlyEndpoint:
    def test_get_hourly_totals(self, client):
        resp = client.get('/api/simulations/1/hourly')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['points'] == 3
        assert data['data'][0]['total_power_kw'] == 275.0

    def test_get_hourly_not_found(self, client):
        resp = client.get('/api/simulations/999/hourly')
        assert resp.status_code == 404

    def test_get_hourly_invalid_id(self, client):
        resp = client.get('/api/simulations/0/hourly')
        assert resp.status_code == 400


class TestMachineMeasurementsEndpoint:
    def test_get_machine_measurements(self, client):
        resp = client.get('/api/simulations/1/machines/HVAC-001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['points'] == 2
        assert data['machine_code'] == 'HVAC-001'

    def test_get_machine_measurements_invalid_sim(self, client):
        resp = client.get('/api/simulations/999/machines/HVAC-001')
        assert resp.status_code == 404

    def test_get_machine_measurements_invalid_machine(self, client):
        resp = client.get('/api/simulations/1/machines/XYZ-999')
        assert resp.status_code == 404

    def test_get_machine_measurements_invalid_code_format(self, client):
        resp = client.get("/api/simulations/1/machines/' OR 1=1--")
        assert resp.status_code == 400


class TestExportEndpoint:
    def test_export_csv_default(self, client):
        resp = client.get('/api/simulations/1/export')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/csv'
        content = resp.data.decode('utf-8')
        assert 'ts' in content
        assert 'total_power_kw' in content

    def test_export_json(self, client):
        resp = client.get('/api/simulations/1/export?format=json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['points'] == 3
        assert data['simulation_id'] == 1

    def test_export_with_date_range(self, client):
        resp = client.get('/api/simulations/1/export?format=json&start=2026-01-01 01:00:00')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['points'] == 2  # Only hours 1 and 2

    def test_export_invalid_format(self, client):
        resp = client.get('/api/simulations/1/export?format=xml')
        assert resp.status_code == 400

    def test_export_invalid_date(self, client):
        resp = client.get("/api/simulations/1/export?start=' OR 1=1--")
        assert resp.status_code == 400

    def test_export_sim_not_found(self, client):
        resp = client.get('/api/simulations/999/export')
        assert resp.status_code == 404


class TestCORS:
    def test_cors_headers_present(self, client):
        resp = client.get('/api/health', headers={'Origin': 'http://localhost:8000'})
        # CORS should allow the configured origin
        assert 'Access-Control-Allow-Origin' in resp.headers

    def test_cors_blocks_unauthorized_origin(self, client):
        resp = client.get('/api/health', headers={'Origin': 'http://evil.com'})
        # Origin header should NOT be echoed back for unauthorized origins
        assert resp.headers.get('Access-Control-Allow-Origin') != 'http://evil.com'


class TestErrorHandlers:
    def test_404_handler(self, client):
        resp = client.get('/api/nonexistent')
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'error' in data
        # Must not contain stack trace details
        assert 'Traceback' not in json.dumps(data)

    def test_405_handler(self, client):
        resp = client.post('/api/machines')
        assert resp.status_code == 405
        data = resp.get_json()
        assert 'error' in data
