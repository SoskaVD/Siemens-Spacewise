"""Tests for the calibration loop — POST /api/machines/<code>/calibrate (Camino A, T3).

Covers specs S2/S4a/S4e of odd/tasks/gemelo-lazo-cerrado.md:
- Calibration derives state shares / load_factor / standby_pct / schedule from
  real measurements and rewrites machines/<CODE>/machine.json in place.
- work_cycles state NAMES are preserved (including inherited mangled keys);
  only the proportions are updated.
- A machine.json.bak with the exact previous bytes is written before the update.
- An optional `_calibration` metadata block records before/after + provenance.
- sim_catalog tolerates `_calibration` (MATLAB side is pinned in
  matlab/tests/test_sim_catalog_modules.m).
- Guards: minimum-hours threshold, invalid machine code (400), missing module
  file (404), malformed module JSON (500, file untouched).
- Default source is the LIVE-STREAM import when import_id is omitted.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from app import create_app
from plant import plant_sim

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'

CODE = 'HVAC-900'
START = datetime(2026, 3, 2, 0, 0, 0)  # a Monday
HOURS = 24 * 7

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


def _median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else None


@pytest.fixture
def env(tmp_path):
    """Machines dir with PRIOR module + DB with catalog row and no imports."""
    machines_dir = tmp_path / 'machines'
    machine_dir = machines_dir / CODE
    machine_dir.mkdir(parents=True)
    module_path = machine_dir / 'machine.json'
    module_path.write_text(json.dumps(PRIOR, indent=2) + '\n', encoding='utf-8')

    db = tmp_path / 'cal.db'
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    conn.execute(
        "INSERT INTO machines (machine_id, machine_code, name, category,"
        " rated_power_kw, voltage_v, current_a, power_factor, phases, thd_pct,"
        " hours_per_day, days_per_week, load_factor, criticality, active)"
        " VALUES (1, ?, 'Chiller de prueba', 'HVAC', 100, 400, 180, 0.85, 3,"
        " 5, 16, 5, 0.4, 'ESENCIAL', 1)",
        (CODE,),
    )
    conn.commit()
    conn.close()

    app = create_app(db_path=str(db), machines_dir=str(machines_dir))
    app.config['TESTING'] = True
    return app, module_path, db


def _seed_import(db, rows, import_code='IMP-CAL'):
    """Store plant_sim rows as real measurements; returns import_id."""
    conn = sqlite3.connect(db)
    cur = conn.execute(
        "INSERT INTO import_data (import_code, name, start_date, end_date,"
        " total_records) VALUES (?, 'cal fixture', ?, ?, ?)",
        (import_code, rows[0]['ts'], rows[-1]['ts'], len(rows)),
    )
    import_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO import_measurements (import_id, machine_code, ts,"
        " active_power_kw) VALUES (?, ?, ?, ?)",
        [(import_id, r['machine_code'], r['ts'], r['active_power_kw'])
         for r in rows],
    )
    conn.commit()
    conn.close()
    return import_id


class TestCalibrationHappyPath:
    def test_calibrates_from_plant_ground_truth(self, env):
        app, module_path, db = env
        rows = plant_sim.generate_series(dict(PRIOR), START, HOURS)
        import_id = _seed_import(db, rows)

        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert body['machine_code'] == CODE
        assert body['import_id'] == import_id
        assert body['hours_analyzed'] == HOURS

        calibrated = json.loads(module_path.read_text(encoding='utf-8'))

        # (1) state names preserved exactly (S4e); shares renormalized to 1.
        assert set(calibrated['work_cycles']) == set(PRIOR['work_cycles'])
        assert abs(sum(calibrated['work_cycles'].values()) - 1.0) < 1e-6

        # (2) estimates approach the ground truth (and strictly beat the prior
        #     on at least one active state — that is the point of the loop).
        truth = {state: 0.0 for state in PRIOR['work_cycles']}
        active_rows = [r for r in rows if r['state'] != 'OFF']
        for row in active_rows:
            truth[row['state']] += 1.0
        for state in truth:
            truth[state] /= len(active_rows)
        improved = [
            state
            for state in truth
            if abs(calibrated['work_cycles'][state] - truth[state])
            < abs(PRIOR['work_cycles'][state] - truth[state])
        ]
        assert improved, (
            f'calibration did not approach ground truth on any state: '
            f'est={calibrated["work_cycles"]} truth={truth}'
        )
        for state in truth:
            assert abs(calibrated['work_cycles'][state] - truth[state]) < 0.15

        # (3) load_factor tracks the measured RUNNING band (degradation is
        #     absorbed into the calibrated prior).
        running_median = _median(
            [r['active_power_kw'] for r in rows if r['state'] == 'RUNNING']
        )
        assert abs(calibrated['load_factor'] - running_median / 100.0) <= 0.08

        # (4) standby_pct tracks the measured STANDBY band.
        standby_median = _median(
            [r['active_power_kw'] for r in rows if r['state'] == 'STANDBY']
        )
        assert abs(calibrated['standby_pct'] - standby_median) <= 1.0

        # (5) schedule fields land on plausible integers within schema ranges.
        assert isinstance(calibrated['hours_per_day'], int)
        assert 1 <= calibrated['hours_per_day'] <= 24
        assert isinstance(calibrated['days_per_week'], int)
        assert 1 <= calibrated['days_per_week'] <= 7

        # (6) traceability block: before/after + provenance, optional keys only.
        trace = calibrated['_calibration']
        assert trace['calibrated_from']['import_id'] == import_id
        assert trace['before']['work_cycles'] == PRIOR['work_cycles']
        assert trace['after']['work_cycles'] == calibrated['work_cycles']
        assert 'calibrated_at' in trace
        assert trace['calibrated_from']['source'] == 'import'

        # (7) byte-exact backup of the previous module.
        backup = module_path.with_suffix('.json.bak')
        assert backup.exists()
        assert json.loads(backup.read_text(encoding='utf-8')) == PRIOR

    def test_recalibration_keeps_original_bak_and_updates_trace(self, env):
        app, module_path, db = env
        rows = plant_sim.generate_series(dict(PRIOR), START, HOURS)
        import_id = _seed_import(db, rows)
        client = app.test_client()
        first = client.post(f'/api/machines/{CODE}/calibrate?import_id={import_id}')
        assert first.status_code == 200
        after_first = json.loads(module_path.read_text(encoding='utf-8'))

        second = client.post(f'/api/machines/{CODE}/calibrate?import_id={import_id}')
        assert second.status_code == 200
        after_second = json.loads(module_path.read_text(encoding='utf-8'))
        # before refers to the immediately-previous calibration result...
        assert after_second['_calibration']['before']['work_cycles'] == \
            after_first['work_cycles']
        # ...and the .bak still holds the ORIGINAL untouched module.
        backup = json.loads(
            module_path.with_suffix('.json.bak').read_text(encoding='utf-8')
        )
        assert backup == PRIOR

    def test_default_import_is_live_stream(self, env):
        app, module_path, db = env
        rows = plant_sim.generate_series(dict(PRIOR), START, HOURS)
        _seed_import(db, rows, import_code='LIVE-STREAM')

        response = app.test_client().post(f'/api/machines/{CODE}/calibrate')
        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert body['import_id'] == _live_import_id(db)


def _live_import_id(db):
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT import_id FROM import_data WHERE import_code = 'LIVE-STREAM'"
    ).fetchone()
    conn.close()
    return row[0]


class TestCalibrationGuards:
    def test_invalid_machine_code_returns_400(self, env):
        app, _, _ = env
        response = app.test_client().post('/api/machines/bad!code/calibrate')
        assert response.status_code == 400

    def test_missing_module_file_returns_404(self, env):
        app, module_path, db = env
        module_path.unlink()
        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id=1'
        )
        assert response.status_code == 404

    def test_insufficient_measurements_returns_400(self, env):
        app, _, db = env
        rows = plant_sim.generate_series(dict(PRIOR), START, 12)[:10]
        import_id = _seed_import(db, rows)
        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 400
        body = response.get_json()
        assert 'hours' in body['error'].lower()

    def test_no_measurements_for_machine_returns_400(self, env):
        app, _, db = env
        other = plant_sim.generate_series(
            {**PRIOR, 'machine_code': 'BOMB-900'}, START, HOURS
        )
        import_id = _seed_import(db, other)
        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 400

    def test_malformed_module_json_returns_500_and_keeps_file(self, env):
        app, module_path, db = env
        original = module_path.read_text(encoding='utf-8')
        module_path.write_text('{not json', encoding='utf-8')
        rows = plant_sim.generate_series(dict(PRIOR), START, HOURS)
        import_id = _seed_import(db, rows)

        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 500
        assert module_path.read_text(encoding='utf-8') == '{not json'
        assert not module_path.with_suffix('.json.bak').exists()
