"""Tests for the live twin state — GET /api/machines/<code>/state (T4, S2/S5).

Covers specs S2 ('estado actual por máquina en el dashboard') and S5:
- Current state is the power-band class of the NEWEST real measurement inside
  the last N hourly rows (window param, default 48, cap 168), classified with
  the shared plant.calibration band model.
- confidence = share of window rows classified in the newest row's band.
- state reports the module's work-cycle state NAME mapping to that band when
  possible (including inherited mangled names), else the raw band class.
- No measurements in the window -> 200 UNKNOWN (fresh system never errors).
- Guards: invalid machine code 400, missing module 404, malformed window 400.
- Default source is the LIVE-STREAM import; explicit import_id is honored.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import create_app

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'

CODE = 'HVAC-900'
BASE = datetime(2026, 3, 2, 0, 0, 0)

# Band levels implied by this prior (plant/calibration.expected_levels):
#   off=0.0  standby=2.0  running=40.0  partial=26.0  (rated 100, lf 0.40, sp 2)
PRIOR = {
    "machine_code": CODE,
    "name": "Chiller de prueba",
    "category": "HVAC",
    "manufacturer": "TestCo",
    "model": "T-1",
    "rated_power_kw": 100.0,
    "voltage_v": 400,
    "current_a": 180.0,
    "power_factor": 0.85,
    "phases": 3,
    "thd_pct": 5.0,
    "hours_per_day": 16,
    "days_per_week": 5,
    "load_factor": 0.40,
    "seasonal_variability": "Baja",
    "work_cycles": {"RUNNING": 0.6, "PARTIAL": 0.2, "STANDBY": 0.2},
    "startup_time_s": 5,
    "startup_multiplier": 5.0,
    "standby_pct": 2.0,
    "flexibility": 0,
    "application": "test",
    "criticality": "ESENCIAL",
    "dependencies": "",
    "environmental_notes": "",
    "active": 1,
}


def write_module(machines_dir, module):
    machine_dir = machines_dir / module['machine_code']
    machine_dir.mkdir(parents=True, exist_ok=True)
    path = machine_dir / 'machine.json'
    path.write_text(json.dumps(module, indent=2) + '\n', encoding='utf-8')
    return path


def make_db(tmp_path, name='state.db', codes=(CODE,)):
    db = tmp_path / name
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    for index, code in enumerate(codes, start=1):
        conn.execute(
            "INSERT INTO machines (machine_id, machine_code, name, category,"
            " rated_power_kw, voltage_v, current_a, power_factor, phases, thd_pct,"
            " hours_per_day, days_per_week, load_factor, criticality, active)"
            " VALUES (?, ?, ?, 'HVAC', 100, 400, 180, 0.85, 3, 5, 16, 5, 0.4,"
            " 'ESENCIAL', 1)",
            (index, code, f'{code} test machine'),
        )
    conn.commit()
    conn.close()
    return db


def put_rows(db, import_id, powers, code=CODE, start=BASE):
    """Store one hourly row per power (ts ascending); returns newest ts."""
    conn = sqlite3.connect(db)
    last = None
    for index, power in enumerate(powers):
        ts = (start + timedelta(hours=index)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "INSERT INTO import_measurements (import_id, machine_code, ts,"
            " active_power_kw) VALUES (?, ?, ?, ?)",
            (import_id, code, ts, power),
        )
        last = ts
    conn.execute(
        "UPDATE import_data SET total_records = (SELECT COUNT(*) FROM"
        " import_measurements WHERE import_id = ?), start_date = ?, end_date = ?"
        " WHERE import_id = ?",
        (import_id, (start).strftime('%Y-%m-%d %H:%M:%S'), last, import_id),
    )
    conn.commit()
    conn.close()
    return last


def seed_import(db, import_code, powers, code=CODE, start=BASE):
    conn = sqlite3.connect(db)
    cur = conn.execute(
        "INSERT INTO import_data (import_code, name) VALUES (?, 'state fixture')",
        (import_code,),
    )
    import_id = cur.lastrowid
    conn.close()
    put_rows(db, import_id, powers, code=code, start=start)
    return import_id


def live_import_id(db):
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT import_id FROM import_data WHERE import_code = 'LIVE-STREAM'"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


@pytest.fixture
def env(tmp_path):
    """App with PRIOR module in a tmp machines dir and an empty schema DB."""
    machines_dir = tmp_path / 'machines'
    module_path = write_module(machines_dir, PRIOR)
    db = make_db(tmp_path)
    app = create_app(db_path=str(db), machines_dir=str(machines_dir))
    app.config['TESTING'] = True
    return app, app.test_client(), module_path, db


class TestStateHappyPath:
    def test_off_newest_with_confidence(self, env):
        app, client, _, db = env
        import_id = seed_import(db, 'IMP-OFF', [40.0, 40.0, 0.0])
        resp = client.get(f'/api/machines/{CODE}/state?import_id={import_id}')
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body['machine_code'] == CODE
        assert body['state'] == 'OFF'          # work-cycle-free OFF band
        assert body['state_key'] == 'off'      # raw band class
        assert body['power_kw'] == pytest.approx(0.0)
        assert body['last_ts'] == (BASE + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        assert body['confidence'] == pytest.approx(1.0 / 3.0)
        assert body['window_hours'] == 48
        assert body['import_id'] == import_id

    def test_running_band_state_maps_state_name(self, env):
        app, client, _, db = env
        # classes: standby(2.0), partial(26.0), running(40.0), running(41.0)
        import_id = seed_import(db, 'IMP-ON', [2.0, 26.0, 40.0, 41.0])
        body = client.get(f'/api/machines/{CODE}/state?import_id={import_id}').get_json()
        assert body['state'] == 'RUNNING'      # first work_cycles key for 'running'
        assert body['state_key'] == 'running'
        assert body['power_kw'] == pytest.approx(41.0)
        assert body['confidence'] == pytest.approx(2.0 / 4.0)


class TestStateEmptyAndGuards:
    def test_unknown_when_no_measurements(self, env):
        app, client, _, db = env
        resp = client.get(f'/api/machines/{CODE}/state')
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body['state'] == 'UNKNOWN'
        assert body['confidence'] == 0
        assert body['power_kw'] is None
        assert body['last_ts'] is None
        assert body['window_hours'] == 48
        assert isinstance(body['import_id'], int)
        # The default source (LIVE-STREAM) was created, never errored.
        assert live_import_id(db) == body['import_id']

    def test_invalid_machine_code_400(self, env):
        app, client, _, _ = env
        resp = client.get('/api/machines/bad!code/state')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_missing_module_404(self, env):
        app, client, module_path, _ = env
        module_path.unlink()
        resp = client.get(f'/api/machines/{CODE}/state')
        assert resp.status_code == 404
        assert 'error' in resp.get_json()

    def test_malformed_window_400(self, env):
        app, client, _, _ = env
        for bad in ('abc', '0', '-3'):
            resp = client.get(f'/api/machines/{CODE}/state?window={bad}')
            assert resp.status_code == 400, bad
            assert 'error' in resp.get_json()

    def test_unknown_when_window_has_no_rows_for_that_import(self, tmp_path):
        # Valid module + valid catalog row, but the import only holds rows of
        # ANOTHER machine: the queried window is empty -> UNKNOWN, not 404.
        machines_dir = tmp_path / 'machines'
        write_module(machines_dir, PRIOR)
        write_module(machines_dir, {**PRIOR, 'machine_code': 'BOMB-900'})
        db = make_db(tmp_path, name='state2.db', codes=(CODE, 'BOMB-900'))
        app = create_app(db_path=str(db), machines_dir=str(machines_dir))
        app.config['TESTING'] = True
        import_id = seed_import(db, 'IMP-OTHER', [40.0], code='BOMB-900')
        resp = app.test_client().get(
            f'/api/machines/{CODE}/state?import_id={import_id}')
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['state'] == 'UNKNOWN'


class TestStateWindow:
    def test_default_window_48_uses_last_rows(self, env):
        app, client, _, db = env
        import_id = live_import_id_of(client, db)
        # 60 rows: first 12 OFF, last 48 RUNNING. Default window=48 must
        # exclude the OFF ones entirely -> confidence 1.0.
        powers = [0.0] * 12 + [40.0] * 48
        put_rows(db, import_id, powers)
        body = client.get(f'/api/machines/{CODE}/state?import_id={import_id}').get_json()
        assert body['window_hours'] == 48
        assert body['confidence'] == pytest.approx(1.0)
        assert body['state_key'] == 'running'

    def test_window_slices_older_rows_out(self, env):
        app, client, _, db = env
        powers = [0.0, 0.0, 0.0, 40.0, 40.0]
        import_id = seed_import(db, 'IMP-W', powers)
        full = client.get(
            f'/api/machines/{CODE}/state?import_id={import_id}&window=5').get_json()
        assert full['confidence'] == pytest.approx(2.0 / 5.0)
        sliced = client.get(
            f'/api/machines/{CODE}/state?import_id={import_id}&window=2').get_json()
        assert sliced['confidence'] == pytest.approx(1.0)
        assert sliced['window_hours'] == 2
        # The newest row still anchors state even outside the sliced window.
        assert sliced['state_key'] == 'running'

    def test_window_capped_at_168(self, env):
        app, client, _, db = env
        powers = [0.0] * 50 + [40.0] * 150   # 200 rows total
        import_id = seed_import(db, 'IMP-CAP', powers)
        body = client.get(
            f'/api/machines/{CODE}/state?import_id={import_id}&window=500').get_json()
        assert body['window_hours'] == 168
        # Last 168 rows: 18 off + 150 running (uncapped would be 150/200).
        assert body['confidence'] == pytest.approx(150.0 / 168.0)

    def test_off_band_row_below_threshold_still_off(self, env):
        app, client, _, db = env
        # 1.5 kW: below standby*0.5=1.0? no -> 1.5 > 1.0 so it classifies by
        # distance: nearest level is standby (2.0). Use 0.4 kW (< 1.0 and
        # < rated*0.005=0.5) to pin the exact off-rule.
        import_id = seed_import(db, 'IMP-LOW', [40.0, 0.4])
        body = client.get(f'/api/machines/{CODE}/state?import_id={import_id}').get_json()
        assert body['state_key'] == 'off'


class TestStateSource:
    def test_default_source_is_live_stream_after_ingest(self, env):
        app, client, _, db = env
        resp = client.post('/api/ingest/hourly', json={'records': [
            {'machine_code': CODE, 'ts': '2026-03-02 00:00:00',
             'active_power_kw': 40.0},
            {'machine_code': CODE, 'ts': '2026-03-02 01:00:00',
             'active_power_kw': 2.0},
        ]})
        assert resp.status_code == 200, resp.get_json()
        import_id = resp.get_json()['import_id']

        # A different import holds a NEWER off-row; the default source must
        # ignore it because state reads LIVE-STREAM.
        other = seed_import(db, 'IMP-NOISE', [0.0] * 4, start=datetime(2026, 3, 2, 12))
        assert other != import_id

        body = client.get(f'/api/machines/{CODE}/state').get_json()
        assert body['import_id'] == import_id
        assert body['state_key'] == 'standby'
        assert body['state'] == 'STANDBY'
        assert body['power_kw'] == pytest.approx(2.0)

    def test_explicit_import_id_used(self, env):
        app, client, _, db = env
        import_id = seed_import(db, 'IMP-EX', [2.0])
        body = client.get(
            f'/api/machines/{CODE}/state?import_id={import_id}').get_json()
        assert body['import_id'] == import_id
        assert body['state'] == 'STANDBY'

    def test_bad_import_id_400(self, env):
        app, client, _, _ = env
        resp = client.get(f'/api/machines/{CODE}/state?import_id=zero')
        assert resp.status_code == 400


def live_import_id_of(client, db):
    """Force LIVE-STREAM creation through the ingest path and return its id."""
    resp = client.post('/api/ingest/hourly', json={'records': [
        {'machine_code': CODE, 'ts': BASE.strftime('%Y-%m-%d %H:%M:%S'),
         'active_power_kw': 40.0},
    ]})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()['import_id']
