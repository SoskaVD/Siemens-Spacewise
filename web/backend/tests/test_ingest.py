"""Tests for continuous ingestion — POST /api/ingest/hourly (Camino B, T2).

Covers:
- Ingest appends to a single rolling LIVE import ('LIVE-STREAM'), created once
- Idempotency: re-ingesting (machine_code, ts) UPDATEs instead of duplicating
- Strict per-record validation at the same level as /api/import/real:
  machine code format/existence, ts 'YYYY-MM-DD HH:MM:SS' strptime-checked,
  finite non-negative floats
- All-or-nothing: any invalid record -> 400 {error, error_count, errors[:20]}
  and nothing written (not even the live import header)
- Response shape {import_id, inserted, updated, total}
- Live-imported rows are comparable through the EXISTING
  GET /api/simulations/<id>/compare?machine=...&import_id=...
- refresh_live_import_bounds recomputes start/end/total from stored rows
"""

import sqlite3
from pathlib import Path

import pytest

from app import create_app

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'

# HVAC-001 sim profile 100/200/300/400 kW (same fixture shape as test_imports).
SIM_HOURS = [
    ('2026-01-01 00:00:00', 0, 100.0),
    ('2026-01-01 01:00:00', 1, 200.0),
    ('2026-01-01 02:00:00', 2, 300.0),
    ('2026-01-01 03:00:00', 3, 400.0),
]

LIVE_CODE = 'LIVE-STREAM'
LIVE_NAME = 'Live feed (hourly ingest)'


@pytest.fixture
def ingest_db(tmp_path):
    """Schema + catalog + one simulation whose HVAC-001 profile is 100/200/300/400 kW."""
    db = tmp_path / 'ingest.db'
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
def client(ingest_db):
    app = create_app(db_path=ingest_db)
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def record(machine='HVAC-001', ts='2026-01-01 00:00:00', power=80.0, **optional):
    rec = {'machine_code': machine, 'ts': ts, 'active_power_kw': power}
    rec.update(optional)
    return rec


def post_ingest(client, records):
    return client.post('/api/ingest/hourly', json={'records': records})


def row_counts(db_path):
    conn = sqlite3.connect(db_path)
    try:
        imports = conn.execute('SELECT COUNT(*) FROM import_data').fetchone()[0]
        measurements = conn.execute('SELECT COUNT(*) FROM import_measurements').fetchone()[0]
    finally:
        conn.close()
    return imports, measurements


class TestIngestLiveImport:
    def test_ingest_inserts_into_live_import(self, client):
        resp = post_ingest(client, [
            record(ts='2026-01-01 00:00:00', power=80.0),
            record(ts='2026-01-01 01:00:00', power=250.0),
            record(machine='COMP-015', ts='2026-01-01 00:00:00', power=70.0),
        ])
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data['import_id'], int) and data['import_id'] > 0
        assert data['inserted'] == 3
        assert data['updated'] == 0
        assert data['total'] == 3

        listing = client.get('/api/imports').get_json()
        assert listing['count'] == 1
        header = listing['imports'][0]
        assert header['import_code'] == LIVE_CODE
        assert header['name'] == LIVE_NAME
        assert header['total_records'] == 3
        assert header['start_date'] == '2026-01-01 00:00:00'
        assert header['end_date'] == '2026-01-01 01:00:00'

        detail = client.get(f"/api/imports/{data['import_id']}").get_json()
        counts = {m['machine_code']: m['rows'] for m in detail['machines']}
        assert counts == {'HVAC-001': 2, 'COMP-015': 1}

    def test_ingest_keeps_single_live_import_across_batches(self, client):
        first = post_ingest(client, [record(ts='2026-01-01 00:00:00')]).get_json()
        second = post_ingest(client, [record(ts='2026-01-01 01:00:00')]).get_json()
        assert first['import_id'] == second['import_id']
        listing = client.get('/api/imports').get_json()
        assert listing['count'] == 1
        assert listing['imports'][0]['import_code'] == LIVE_CODE
        assert listing['imports'][0]['total_records'] == 2
        assert listing['imports'][0]['end_date'] == '2026-01-01 01:00:00'

    def test_optional_values_stored(self, client, ingest_db):
        resp = post_ingest(client, [
            record(power=80.0, energy_kwh=99.5, current_a=120.4,
                   power_factor=0.86, voltage_v=479.2),
        ])
        assert resp.status_code == 200
        conn = sqlite3.connect(ingest_db)
        try:
            row = conn.execute(
                'SELECT energy_kwh, current_a, power_factor, voltage_v '
                'FROM import_measurements').fetchone()
        finally:
            conn.close()
        assert row == pytest.approx((99.5, 120.4, 0.86, 479.2))


class TestIngestIdempotency:
    def test_reingest_same_ts_updates_not_duplicates(self, client, ingest_db):
        first = post_ingest(client, [
            record(ts='2026-01-01 00:00:00', power=80.0),
            record(ts='2026-01-01 01:00:00', power=250.0),
        ]).get_json()
        assert (first['inserted'], first['updated']) == (2, 0)

        second = post_ingest(client, [
            record(ts='2026-01-01 00:00:00', power=95.0),
            record(ts='2026-01-01 01:00:00', power=250.0),
        ]).get_json()
        assert second['import_id'] == first['import_id']
        assert second['inserted'] == 0
        assert second['updated'] == 1
        assert second['total'] == 2

        # No duplication, and the changed value is the one stored.
        conn = sqlite3.connect(ingest_db)
        try:
            total = conn.execute(
                'SELECT COUNT(*) FROM import_measurements').fetchone()[0]
            power = conn.execute(
                "SELECT active_power_kw FROM import_measurements "
                "WHERE ts = '2026-01-01 00:00:00'").fetchone()[0]
        finally:
            conn.close()
        assert total == 2
        assert power == pytest.approx(95.0)

        detail = client.get(f"/api/imports/{first['import_id']}").get_json()
        assert detail['total_records'] == 2

    def test_reingest_identical_values_changes_nothing(self, client, ingest_db):
        post_ingest(client, [record(ts='2026-01-01 00:00:00', power=80.0)])
        again = post_ingest(client, [record(ts='2026-01-01 00:00:00', power=80.0)]).get_json()
        assert (again['inserted'], again['updated'], again['total']) == (0, 0, 1)
        assert row_counts(ingest_db) == (1, 1)


class TestIngestValidation:
    def test_invalid_record_rejects_whole_batch(self, client, ingest_db):
        before = row_counts(ingest_db)
        resp = post_ingest(client, [
            record(ts='2026-01-01 00:00:00', power=80.0),
            record(ts='2026-01-01 01:00:00', power='abc'),
        ])
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data
        assert data['error_count'] == 1
        assert len(data['errors']) == 1
        assert data['errors'][0]['index'] == 1
        # All-or-nothing: not even the live import header is created.
        assert row_counts(ingest_db) == before

    def test_unknown_machine_code_rejected(self, client, ingest_db):
        resp = post_ingest(client, [record(machine='XXX-999')])
        assert resp.status_code == 400
        errors_text = ' '.join(e['error'] for e in resp.get_json()['errors'])
        assert 'XXX-999' in errors_text
        assert row_counts(ingest_db) == (0, 0)

    def test_inactive_machine_code_rejected(self, client, ingest_db):
        resp = post_ingest(client, [record(machine='PUMP-007')])
        assert resp.status_code == 400
        assert row_counts(ingest_db) == (0, 0)

    def test_lowercase_machine_code_normalized(self, client):
        resp = post_ingest(client, [record(machine='hvac-001')])
        assert resp.status_code == 200
        assert resp.get_json()['inserted'] == 1

    def test_bad_timestamp_rejected(self, client, ingest_db):
        for bad_ts in ('2026-13-45 99:99:99', '2026-01-01', 'not-a-date', None):
            resp = post_ingest(client, [record(ts=bad_ts)])
            assert resp.status_code == 400, bad_ts
        assert row_counts(ingest_db) == (0, 0)

    def test_negative_power_rejected(self, client, ingest_db):
        resp = post_ingest(client, [record(power=-5.0)])
        assert resp.status_code == 400
        assert row_counts(ingest_db) == (0, 0)

    def test_non_finite_power_rejected(self, client, ingest_db):
        for bad in (float('inf'), float('nan')):
            resp = client.post('/api/ingest/hourly',
                               json={'records': [record(power=bad)]})
            assert resp.status_code == 400, bad
        assert row_counts(ingest_db) == (0, 0)

    def test_missing_required_field_rejected(self, client, ingest_db):
        resp = client.post('/api/ingest/hourly',
                           json={'records': [{'machine_code': 'HVAC-001',
                                              'ts': '2026-01-01 00:00:00'}]})
        assert resp.status_code == 400
        assert row_counts(ingest_db) == (0, 0)

    def test_record_not_object_rejected(self, client):
        resp = post_ingest(client, ['HVAC-001'])
        assert resp.status_code == 400

    def test_empty_records_rejected(self, client, ingest_db):
        resp = post_ingest(client, [])
        assert resp.status_code == 400
        assert row_counts(ingest_db) == (0, 0)

    def test_missing_records_key_rejected(self, client):
        resp = client.post('/api/ingest/hourly', json={})
        assert resp.status_code == 400

    def test_records_not_list_rejected(self, client):
        resp = client.post('/api/ingest/hourly', json={'records': {'a': 1}})
        assert resp.status_code == 400

    def test_non_json_body_rejected(self, client):
        resp = client.post('/api/ingest/hourly', data=b'plain text',
                           content_type='text/plain')
        assert resp.status_code == 400

    def test_errors_capped_at_twenty(self, client, ingest_db):
        bad = [record(ts='2026-01-01 00:00:00', power=f'nan{j}')
               for j in range(25)]
        resp = post_ingest(client, bad)
        assert resp.status_code == 400
        data = resp.get_json()
        assert len(data['errors']) <= 20
        assert data['error_count'] == 25


class TestIngestCompareIntegration:
    def test_compare_against_live_import_id(self, client):
        """Live-ingested rows go through the existing comparison path."""
        import_id = post_ingest(client, [
            record(ts='2026-01-01 00:00:00', power=80.0),
            record(ts='2026-01-01 01:00:00', power=250.0),
            record(ts='2026-01-01 02:00:00', power=300.0),
            record(ts='2026-01-01 04:00:00', power=500.0),
        ]).get_json()['import_id']
        resp = client.get(
            f'/api/simulations/1/compare?machine=HVAC-001&import_id={import_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Same hand-computed expectation as test_imports.TestCompareEndpoint.
        assert data['mape_pct'] == pytest.approx(15.0)
        assert data['mean_bias_pct'] == pytest.approx(5.0 / 3.0)
        assert data['hours_compared'] == 3
        assert data['coverage_pct'] == pytest.approx(75.0)
        assert data['series'] == [
            {'ts': '2026-01-01 00:00:00', 'simulated_kw': 100.0, 'real_kw': 80.0},
            {'ts': '2026-01-01 01:00:00', 'simulated_kw': 200.0, 'real_kw': 250.0},
            {'ts': '2026-01-01 02:00:00', 'simulated_kw': 300.0, 'real_kw': 300.0},
        ]

    def test_get_real_measurements_sees_live_rows(self, client, ingest_db):
        import_id = post_ingest(client, [
            record(ts='2026-01-01 00:00:00', power=80.0),
            record(ts='2026-01-01 01:00:00', power=95.0),
        ]).get_json()['import_id']
        import queries
        rows = queries.get_real_measurements(import_id, db_path=ingest_db)
        assert [r['active_power_kw'] for r in rows] == [80.0, 95.0]


class TestRefreshLiveImportBounds:
    def test_refresh_recomputes_bounds(self, client, ingest_db):
        import_id = post_ingest(client, [
            record(ts='2026-01-01 01:00:00', power=80.0),
        ]).get_json()['import_id']

        # Corrupt the header bounds behind the API's back.
        conn = sqlite3.connect(ingest_db)
        try:
            conn.execute(
                'UPDATE import_data SET start_date = NULL, end_date = NULL, '
                'total_records = 0 WHERE import_id = ?', (import_id,))
            conn.commit()
        finally:
            conn.close()

        import queries
        queries.refresh_live_import_bounds(import_id, db_path=ingest_db)

        header = client.get('/api/imports').get_json()['imports'][0]
        assert header['start_date'] == '2026-01-01 01:00:00'
        assert header['end_date'] == '2026-01-01 01:00:00'
        assert header['total_records'] == 1
