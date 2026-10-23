"""Edge regression tests for the calibration write path (independent verifier batch).

Pins verifier findings on commit fc001cc:
- B1: all-zero measurement imports answer 400 (never 500) and write nothing.
- A1: explicit OFF keys in work_cycles keep their prior share instead of being
  silently zeroed by drift correction.
- A3: the first .bak keeps the module's ORIGINAL bytes, newline style included.
- S4e: unknown-but-bandless state names keep the total renormalized to exactly 1.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import create_app
from plant import plant_sim

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'
CODE = 'HVAC-901'
START = datetime(2026, 3, 2, 0, 0, 0)

BASE = {
    "machine_code": CODE,
    "name": "Chiller de bordes",
    "category": "HVAC",
    "manufacturer": "TestCo",
    "model": "T-2",
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


@pytest.fixture
def env(tmp_path):
    machines_dir = tmp_path / 'machines'
    machine_dir = machines_dir / CODE
    machine_dir.mkdir(parents=True)
    module_path = machine_dir / 'machine.json'

    db = tmp_path / 'edge.db'
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    conn.execute(
        "INSERT INTO machines (machine_id, machine_code, name, category,"
        " rated_power_kw, voltage_v, current_a, power_factor, phases, thd_pct,"
        " hours_per_day, days_per_week, load_factor, criticality, active)"
        " VALUES (1, ?, 'Chiller de bordes', 'HVAC', 100, 400, 180, 0.85, 3,"
        " 5, 16, 5, 0.4, 'ESENCIAL', 1)",
        (CODE,),
    )
    conn.commit()
    conn.close()

    app = create_app(db_path=str(db), machines_dir=str(machines_dir))
    app.config['TESTING'] = True

    def write_module(module: dict, *, newline: str = '\n') -> bytes:
        raw = json.dumps(module, indent=2).replace('\n', newline) + newline
        module_path.write_bytes(raw.encode('utf-8'))
        return raw.encode('utf-8')

    def seed_import(rows) -> int:
        conn = sqlite3.connect(db)
        cur = conn.execute(
            "INSERT INTO import_data (import_code, name, start_date, end_date,"
            " total_records) VALUES ('IMP-EDGE', 'edge fixture', ?, ?, ?)",
            (rows[0]['ts'], rows[-1]['ts'], len(rows)),
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

    return app, module_path, write_module, seed_import


class TestVerifierRegressions:
    def test_zero_active_import_is_400(self, env):
        """B1: a machine that never consumes power cannot drive calibration."""
        app, module_path, write_module, seed_import = env
        original = write_module(dict(BASE))
        rows = [
            {"machine_code": CODE,
             "ts": (START + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S"),
             "active_power_kw": 0.0}
            for h in range(48)
        ]
        import_id = seed_import(rows)

        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 400, response.get_json()
        assert 'power' in response.get_json()['error'].lower()
        # nothing was written: no .bak and the module keeps its original bytes
        assert not module_path.with_suffix('.json.bak').exists()
        assert module_path.read_bytes() == original

    def test_off_state_prior_preserved(self, env):
        """A1: explicit OFF keys keep their prior share; bands share the rest."""
        app, module_path, write_module, seed_import = env
        module = dict(BASE)
        module['work_cycles'] = {
            "OFF": 0.8, "RUNNING": 0.1, "PARTIAL": 0.05, "STANDBY": 0.05,
        }
        write_module(module)
        rows = plant_sim.generate_series(dict(module), START, 24 * 7)
        import_id = seed_import(rows)

        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 200, response.get_json()
        calibrated = json.loads(module_path.read_text(encoding='utf-8'))
        assert calibrated['work_cycles']['OFF'] == pytest.approx(0.8, abs=1e-6)
        assert sum(calibrated['work_cycles'].values()) == 1.0
        assert set(calibrated['work_cycles']) == set(module['work_cycles'])

    def test_unknown_key_sum_exactly_one(self, env):
        """S4e: any state-name set keeps keys and renormalizes to exactly 1."""
        app, module_path, write_module, seed_import = env
        module = dict(BASE)
        module['work_cycles'] = {
            "RUNNING": 0.5, "PARTIAL": 0.2, "STANDBY": 0.2, "MODO-X": 0.1,
        }
        write_module(module)
        rows = plant_sim.generate_series(dict(module), START, 24 * 7)
        import_id = seed_import(rows)

        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 200, response.get_json()
        calibrated = json.loads(module_path.read_text(encoding='utf-8'))
        assert set(calibrated['work_cycles']) == set(module['work_cycles'])
        assert sum(calibrated['work_cycles'].values()) == 1.0

    def test_crlf_backup_keeps_original_bytes(self, env):
        """A3: the first .bak is a byte-exact snapshot, CRLF included."""
        app, module_path, write_module, seed_import = env
        original = write_module(dict(BASE), newline='\r\n')
        rows = plant_sim.generate_series(dict(BASE), START, 24 * 7)
        import_id = seed_import(rows)

        response = app.test_client().post(
            f'/api/machines/{CODE}/calibrate?import_id={import_id}'
        )
        assert response.status_code == 200, response.get_json()
        backup = module_path.with_suffix('.json.bak')
        assert backup.read_bytes() == original
