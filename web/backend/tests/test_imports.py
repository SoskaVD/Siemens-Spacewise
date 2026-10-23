"""Tests for real-measurement import and the simulated-vs-real comparison (T2).

Covers:
- POST /api/import/real (multipart file and raw text/csv body)
- Validation: unknown/inactive machine codes, bad timestamps, negative or
  non-numeric values, missing header, no data rows, error cap of 20 lines
- Atomicity: a rejected CSV must leave zero rows behind
- GET /api/imports, GET /api/imports/<id>, DELETE /api/imports/<id> (cascade)
- GET /api/simulations/<id>/compare: hourly alignment by exact ts string,
  MAPE over hours with real > 0 only, signed bias, hours compared,
  coverage, latest-import default, and no-overlap behaviour without a 500
"""

import io
import sqlite3
from pathlib import Path

import pytest

from app import create_app

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'

# Machine codes present in the seeded catalog (active) and one inactive.
SIM_HOURS = [
    ('2026-01-01 00:00:00', 0, 100.0),
    ('2026-01-01 01:00:00', 1, 200.0),
    ('2026-01-01 02:00:00', 2, 300.0),
    ('2026-01-01 03:00:00', 3, 400.0),
]


@pytest.fixture
def import_db(tmp_path):
    """Schema + catalog + one simulation whose HVAC-001 profile is 100/200/300/400 kW."""
    db = tmp_path / 'imports.db'
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    rows = ',\n'.join(
        f"(1, 1, '{ts}', {hour}, {kw}, {kw}, 0.8, 'RUNNING')"
        for ts, hour, kw in SIM_HOURS
    )
    conn.executescript(f"""
        INSERT INTO machines (machine_id, machine_code, name, category, rated_power_kw,
            voltage_v, current_a, power_factor, phases, thd_pct, hours_per_day,
            days_per_week, load_factor, criticality, active)
        VALUES (1, 'HVAC-001', 'Chiller A', 'HVAC', 150, 480, 200, 0.85, 3, 5, 18, 6, 0.75, 'ESENCIAL', 1),
               (2, 'COMP-015', 'Compressor B', 'Compresores', 75, 480, 100, 0.88, 3, 4, 12, 5, 0.6, 'CRITICA', 1),
               (3, 'PUMP-007', 'Inactive Pump', 'Bombas', 25, 480, 35, 0.8, 3, 2, 8, 5, 0.5, 'FLEXIBLE', 0);
        INSERT INTO simulations (simulation_id, simulation_code, name, status, total_machines, total_hours)
        VALUES (1, 'SIM-2026-001', 'Baseline', 'COMPLETED', 2, 4);
        INSERT INTO machine_measurements (simulation_id, machine_id, ts, hour_index,
            active_power_kw, energy_kwh, load_factor, operation_state)
        VALUES {rows};
    """)
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def client(import_db):
    app = create_app(db_path=import_db)
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def csv_text(rows, header='machine_code,ts,active_power_kw'):
    body = '\r\n'.join([header] + rows) + '\r\n'
    return body


def post_multipart(client, content, filename='medidas.csv', query=''):
    return client.post(f'/api/import/real{query}',
                       data={'file': (io.BytesIO(content.encode('utf-8')), filename)},
                       content_type='multipart/form-data')


def row_counts(db_path):
    conn = sqlite3.connect(db_path)
    try:
        imports = conn.execute('SELECT COUNT(*) FROM import_data').fetchone()[0]
        measurements = conn.execute('SELECT COUNT(*) FROM import_measurements').fetchone()[0]
    finally:
        conn.close()
    return imports, measurements


class TestImportRealEndpoint:
    def test_multipart_import_success(self, client):
        content = csv_text([
            'HVAC-001,2026-01-01 00:00:00,80',
            'HVAC-001,2026-01-01 01:00:00,250',
            'COMP-015,2026-01-01 00:00:00,70',
        ])
        resp = post_multipart(client, content)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['rows'] == 3
        assert isinstance(data['import_id'], int) and data['import_id'] > 0

        detail = client.get(f"/api/imports/{data['import_id']}")
        assert detail.status_code == 200
        detail_json = detail.get_json()
        assert detail_json['source_file'] == 'medidas.csv'
        assert detail_json['total_records'] == 3
        counts = {m['machine_code']: m['rows'] for m in detail_json['machines']}
        assert counts == {'HVAC-001': 2, 'COMP-015': 1}

    def test_raw_csv_body_import_with_name_and_notes(self, client, import_db):
        content = csv_text(
            ['HVAC-001,2026-01-01 00:00:00,80,99.5,120.4,0.86,479.2'],
            header='machine_code,ts,active_power_kw,energy_kwh,current_a,power_factor,voltage_v',
        )
        resp = client.post('/api/import/real?name=Q1%20Mediciones&notes=SentrAN%20site',
                           data=content.encode('utf-8'),
                           content_type='text/csv')
        assert resp.status_code == 201
        detail = client.get(f"/api/imports/{resp.get_json()['import_id']}").get_json()
        assert detail['name'] == 'Q1 Mediciones'
        assert detail['description'] == 'SentrAN site'
        # Optional columns must be stored, not dropped.
        conn = sqlite3.connect(import_db)
        try:
            row = conn.execute(
                'SELECT energy_kwh, current_a, power_factor, voltage_v '
                'FROM import_measurements').fetchone()
        finally:
            conn.close()
        assert row == pytest.approx((99.5, 120.4, 0.86, 479.2))

    def test_malformed_csv_rejected_without_partial_write(self, client, import_db):
        before = row_counts(import_db)
        content = csv_text([
            'HVAC-001,2026-01-01 00:00:00,80',
            'HVAC-001,2026-01-01 01:00:00,abc',
        ])
        resp = post_multipart(client, content)
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data
        assert len(data['errors']) >= 1
        assert data['errors'][0]['line'] == 3  # header is line 1
        # Atomicity: nothing may be written.
        assert row_counts(import_db) == before

    def test_unknown_machine_code_rejected(self, client, import_db):
        before = row_counts(import_db)
        content = csv_text([
            'HVAC-001,2026-01-01 00:00:00,80',
            'XXX-999,2026-01-01 01:00:00,90',
        ])
        resp = post_multipart(client, content)
        assert resp.status_code == 400
        errors_text = ' '.join(e['error'] for e in resp.get_json()['errors'])
        assert 'XXX-999' in errors_text
        assert row_counts(import_db) == before

    def test_inactive_machine_code_rejected(self, client, import_db):
        content = csv_text(['PUMP-007,2026-01-01 00:00:00,80'])
        resp = post_multipart(client, content)
        assert resp.status_code == 400
        assert row_counts(import_db) == (0, 0)

    def test_negative_power_rejected(self, client, import_db):
        content = csv_text(['HVAC-001,2026-01-01 00:00:00,-5'])
        resp = post_multipart(client, content)
        assert resp.status_code == 400
        assert row_counts(import_db) == (0, 0)

    def test_bad_timestamp_rejected(self, client):
        content = csv_text(['HVAC-001,2026-13-45 99:99:99,80'])
        resp = post_multipart(client, content)
        assert resp.status_code == 400

    def test_missing_header_rejected(self, client):
        content = 'HVAC-001,2026-01-01 00:00:00,80\r\n'  # no header row
        resp = post_multipart(client, content)
        assert resp.status_code == 400

    def test_no_data_rows_rejected(self, client):
        content = csv_text([])
        resp = post_multipart(client, content)
        assert resp.status_code == 400

    def test_empty_body_rejected(self, client):
        resp = client.post('/api/import/real', data=b'', content_type='text/csv')
        assert resp.status_code == 400

    def test_errors_capped_at_twenty(self, client):
        bad = [f'HVAC-001,2026-01-01 00:00:00,nan{j}' for j in range(25)]
        content = csv_text(bad)
        resp = post_multipart(client, content)
        assert resp.status_code == 400
        data = resp.get_json()
        assert len(data['errors']) <= 20
        assert data['error_count'] == 25

    def test_sql_injection_machine_code_rejected(self, client, import_db):
        content = csv_text(["HVAC-001'; DROP TABLE machines;--,2026-01-01 00:00:00,80"])
        resp = post_multipart(client, content)
        assert resp.status_code == 400
        conn = sqlite3.connect(import_db)
        try:
            machines = conn.execute('SELECT COUNT(*) FROM machines').fetchone()[0]
        finally:
            conn.close()
        assert machines == 3


class TestImportsListingAndDelete:
    def test_list_empty(self, client):
        data = client.get('/api/imports').get_json()
        assert data == {'imports': [], 'count': 0}

    def test_list_after_import(self, client):
        post_multipart(client, csv_text(['HVAC-001,2026-01-01 00:00:00,80']))
        data = client.get('/api/imports').get_json()
        assert data['count'] == 1
        assert data['imports'][0]['total_records'] == 1

    def test_detail_not_found(self, client):
        assert client.get('/api/imports/999').status_code == 404

    def test_delete_import_cascades(self, client, import_db):
        resp = post_multipart(client, csv_text([
            'HVAC-001,2026-01-01 00:00:00,80',
            'HVAC-001,2026-01-01 01:00:00,90',
        ]))
        import_id = resp.get_json()['import_id']
        assert row_counts(import_db) == (1, 2)

        dele = client.delete(f'/api/imports/{import_id}')
        assert dele.status_code == 200
        assert row_counts(import_db) == (0, 0)
        assert client.get(f'/api/imports/{import_id}').status_code == 404
        assert client.delete(f'/api/imports/{import_id}').status_code == 404


class TestCompareEndpoint:
    """Hand-computed expectations against the 100/200/300/400 kW seeded profile.

    Real series h0=80, h1=250, h2=300 (+ h4=500 outside the sim grid):
      APE per aligned hour = |sim-real|/real*100
        h0: |100-80|/80   = 25 %
        h1: |200-250|/250 = 20 %
        h2: |300-300|/300 =  0 %
      MAPE = (25+20+0)/3 = 15 %
      Bias per hour = (sim-real)/real*100 -> (+25, -20, 0); mean = 5/3 %
      hours_compared = 3; coverage = 3 of 4 sim hours = 75 %
    """

    def _import_real(self, client, rows):
        resp = post_multipart(client, csv_text(rows))
        assert resp.status_code == 201
        return resp.get_json()['import_id']

    def test_compare_exact_mape(self, client):
        import_id = self._import_real(client, [
            'HVAC-001,2026-01-01 00:00:00,80',
            'HVAC-001,2026-01-01 01:00:00,250',
            'HVAC-001,2026-01-01 02:00:00,300',
            'HVAC-001,2026-01-01 04:00:00,500',
        ])
        resp = client.get(f'/api/simulations/1/compare?machine=HVAC-001&import_id={import_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['mape_pct'] == pytest.approx(15.0)
        assert data['mean_bias_pct'] == pytest.approx(5.0 / 3.0)
        assert data['hours_compared'] == 3
        assert data['coverage_pct'] == pytest.approx(75.0)
        assert data['series'] == [
            {'ts': '2026-01-01 00:00:00', 'simulated_kw': 100.0, 'real_kw': 80.0},
            {'ts': '2026-01-01 01:00:00', 'simulated_kw': 200.0, 'real_kw': 250.0},
            {'ts': '2026-01-01 02:00:00', 'simulated_kw': 300.0, 'real_kw': 300.0},
        ]

    def test_compare_ignores_zero_real_in_mape(self, client):
        # h0 real is 0 kW: it stays an aligned hour but is excluded from MAPE/bias.
        import_id = self._import_real(client, [
            'HVAC-001,2026-01-01 00:00:00,0',
            'HVAC-001,2026-01-01 01:00:00,250',
            'HVAC-001,2026-01-01 02:00:00,300',
            'HVAC-001,2026-01-01 03:00:00,400',
        ])
        resp = client.get(f'/api/simulations/1/compare?machine=HVAC-001&import_id={import_id}')
        data = resp.get_json()
        # MAPE over real>0 hours: (20+0+0)/3; bias: (-20+0+0)/3
        assert data['hours_compared'] == 4
        assert data['coverage_pct'] == pytest.approx(100.0)
        assert data['mape_pct'] == pytest.approx(20.0 / 3.0)
        assert data['mean_bias_pct'] == pytest.approx(-20.0 / 3.0)

    def test_compare_no_overlap_is_clean_zero_coverage(self, client):
        import_id = self._import_real(client, [
            'HVAC-001,2027-06-01 00:00:00,80',
        ])
        resp = client.get(f'/api/simulations/1/compare?machine=HVAC-001&import_id={import_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['series'] == []
        assert data['hours_compared'] == 0
        assert data['coverage_pct'] == pytest.approx(0.0)
        assert data['mape_pct'] is None
        assert data['mean_bias_pct'] is None

    def test_compare_defaults_to_latest_import(self, client):
        self._import_real(client, ['HVAC-001,2027-06-01 00:00:00,80'])  # stale
        latest = self._import_real(client, ['HVAC-001,2026-01-01 00:00:00,80'])
        resp = client.get('/api/simulations/1/compare?machine=HVAC-001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['import_id'] == latest
        assert data['hours_compared'] == 1
        assert data['mape_pct'] == pytest.approx(25.0)

    def test_compare_import_not_found(self, client):
        resp = client.get('/api/simulations/1/compare?machine=HVAC-001&import_id=999')
        assert resp.status_code == 404

    def test_compare_without_any_import(self, client):
        resp = client.get('/api/simulations/1/compare?machine=HVAC-001')
        assert resp.status_code == 404

    def test_compare_machine_required(self, client):
        resp = client.get('/api/simulations/1/compare')
        assert resp.status_code == 400

    def test_compare_invalid_machine_format(self, client):
        resp = client.get('/api/simulations/1/compare?machine=hvac')
        assert resp.status_code == 400

    def test_compare_sim_not_found(self, client):
        resp = client.get('/api/simulations/999/compare?machine=HVAC-001')
        assert resp.status_code == 404

    def test_compare_machine_not_in_catalog(self, client):
        resp = client.get('/api/simulations/1/compare?machine=XYZ-999')
        assert resp.status_code == 404
