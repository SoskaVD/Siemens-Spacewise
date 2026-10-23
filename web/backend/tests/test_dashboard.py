"""Tests del dashboard y del modo de simulación continua.

Cubren los problemas que impedían ver el dashboard:
- "/" respondía 404 (nadie servía index.html).
- Una simulación en ejecución no tiene simulation_results, por lo que /summary
  devolvía 404.
- El backend creaba un archivo SQLite vacío si la base aún no existía.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from app import create_app

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'


@pytest.fixture
def running_db(tmp_path):
    """Base como la deja la simulación continua: RUNNING, sin simulation_results."""
    db = tmp_path / 'running.db'
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    conn.executescript("""
        INSERT INTO machines (machine_id, machine_code, name, category, rated_power_kw,
            voltage_v, current_a, power_factor, phases, thd_pct, hours_per_day,
            days_per_week, load_factor, criticality, active)
        VALUES (1, 'HVAC-001', 'Chiller', 'HVAC', 150, 480, 200, 0.85, 3, 5, 18, 6, 0.75, 'ESENCIAL', 1),
               (2, 'COMP-001', 'Compresor', 'Compresores', 75, 480, 100, 0.88, 3, 4, 12, 5, 0.6, 'CRITICA', 1);
        INSERT INTO simulations (simulation_id, simulation_code, name, status, total_machines, total_hours)
        VALUES (1, 'SIM-CONTINUOUS-001', 'Continua', 'RUNNING', 2, 2);
        INSERT INTO hourly_totals (simulation_id, ts, hour_index, total_power_kw, total_energy_kwh,
            hvac_power_kw, compressors_power_kw)
        VALUES (1, '2026-01-01 00:00:00', 0, 200.0, 200.0, 150.0, 50.0),
               (1, '2026-01-01 01:00:00', 1, 300.0, 300.0, 200.0, 100.0);
        INSERT INTO machine_measurements (simulation_id, machine_id, ts, hour_index,
            active_power_kw, energy_kwh, load_factor)
        VALUES (1, 1, '2026-01-01 00:00:00', 0, 150, 150, 0.8),
               (1, 1, '2026-01-01 01:00:00', 1, 200, 200, 0.9),
               (1, 2, '2026-01-01 00:00:00', 0, 50, 50, 0.5),
               (1, 2, '2026-01-01 01:00:00', 1, 100, 100, 0.6);
    """)
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def client(running_db):
    app = create_app(db_path=running_db)
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestFrontendServed:
    def test_root_serves_dashboard(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'Simulador de Maquinaria Industrial' in resp.data
        resp.close()

    def test_static_assets_served(self, client):
        for path in ('/css/styles.css', '/js/api.js', '/js/charts.js'):
            resp = client.get(path)
            assert resp.status_code == 200, path
            resp.close()

    def test_unknown_asset_is_404(self, client):
        assert client.get('/js/no-existe.js').status_code == 404

    def test_root_contains_comparison_section(self, client):
        """T2: the dashboard exposes the "Simulado vs Real" area and its 4th chart."""
        body = client.get('/').data.decode('utf-8')
        assert 'Simulado vs Real' in body
        assert 'compare-chart' in body
        assert 'Cargar CSV real' in body

    def test_compare_assets_exposed(self, client):
        charts = client.get('/js/charts.js').data.decode('utf-8')
        assert 'renderCompareChart' in charts
        api = client.get('/js/api.js').data.decode('utf-8')
        for fn in ('uploadRealCsv', 'getImports', 'getCompare'):
            assert fn in api

    def test_health_alias(self, client):
        assert client.get('/health').status_code == 200


class TestRunningSimulation:
    def test_summary_available_while_running(self, client):
        resp = client.get('/api/simulations/1/summary')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_partial'] is True
        assert data['hours_processed'] == 2
        assert data['total_energy_kwh'] == pytest.approx(500.0)
        assert data['avg_power_kw'] == pytest.approx(250.0)
        assert data['peak_power_kw'] == pytest.approx(300.0)
        assert data['peak_ts'] == '2026-01-01 01:00:00'

    def test_partial_summary_has_chart_payloads(self, client):
        data = client.get('/api/simulations/1/summary').get_json()
        categories = json.loads(data['energy_by_category_json'])
        assert categories['hvac'] == pytest.approx(350.0)
        top = json.loads(data['top_machines_json'])
        assert top[0] == {'code': 'HVAC-001', 'name': 'Chiller',
                          'category': 'HVAC', 'energy': 350.0}

    def test_unknown_simulation_still_404(self, client):
        assert client.get('/api/simulations/999/summary').status_code == 404

    def test_simulation_listed_as_running(self, client):
        sims = client.get('/api/simulations').get_json()['simulations']
        assert sims[0]['status'] == 'RUNNING'


class TestMissingDatabase:
    def test_does_not_create_database_file(self, tmp_path):
        """Flask no debe crear un archivo vacío: MATLAB lo tomaría como base lista."""
        missing = tmp_path / 'aun-no-existe.db'
        app = create_app(db_path=str(missing))
        app.config['TESTING'] = True
        with app.test_client() as c:
            assert c.get('/api/simulations').get_json()['simulations'] == []
            assert c.get('/api/machines').get_json()['machines'] == []
            assert c.get('/api/simulations/1/summary').status_code == 404
            assert c.get('/api/health').get_json()['status'] == 'degraded'
        assert not missing.exists()
