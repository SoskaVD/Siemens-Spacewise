"""Closed-loop demo: plant -> ingest -> calibrate -> expected-MAPE improvement.

Proves the twin loop end to end WITHOUT MATLAB and WITHOUT real hardware:

1. Boot the Flask app on a throwaway SQLite DB (schema only) seeded with a few
   real catalog modules registered as machines.
2. Stream plant hours through the REAL ingestion endpoint (POST
   /api/ingest/hourly) exactly as feed_loop.py would against a live server.
3. Calibrate every streamed machine through the REAL endpoint (POST
   /api/machines/<code>/calibrate, LIVE-STREAM default).
4. Compare, hour by hour, the model's expected profile (deterministic
   share-weighted power — the same information the MATLAB simulator encodes)
   against the streamed "measurements", before and after calibration.

The MAPE drop is the measurable signature of the closed loop: after
calibration the twin describes its (synthetic) physical individual better.
With MATLAB available the identical pattern holds end-to-end: calibrate the
modules, re-run the simulation, and GET /api/simulations/<id>/compare shows a
lower mape_pct.

Usage:
    .venv/bin/python plant/demo_closed_loop.py [--hours 168]
Stdlib only. All scratch lives under tempfile.mkdtemp(), never in the repo.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'web' / 'backend'))

SCHEMA = REPO_ROOT / 'data' / 'schema_simulator.sql'

MACHINE_INSERT = (
    "INSERT INTO machines (machine_id, machine_code, name, category,"
    " rated_power_kw, voltage_v, current_a, power_factor, phases, thd_pct,"
    " hours_per_day, days_per_week, load_factor, criticality, active)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)"
)


def _expected_daily_kwh(module: dict, start: datetime, hours: int) -> dict[str, float]:
    """Deterministic model expectation per calendar day, in kWh.

    The twin's "what the meter SHOULD accumulate" given its prior model:
    scheduled days (weekday < days_per_week, for the first hours_per_day
    hours) accumulate the share-weighted average of the state power levels
    (running/partial/standby via the same power model used for band
    classification); unscheduled days accumulate 0. Deterministic on
    purpose: the demo isolates PARAMETER error (wrong shares/levels/
    schedule), not sampling noise. Daily energy is the honest metric for a
    statistical profile: hourly MAPE would be dominated by standby hours
    where any relative error explodes.
    """
    from plant import calibration, plant_sim

    levels = calibration.expected_levels(module)
    work_cycles = module.get('work_cycles') or {}
    weighted = sum(
        share * max(levels.get(plant_sim._classify_state(name), 0.0), 0.0)
        for name, share in work_cycles.items()
    )
    total_share = sum(float(v) for v in work_cycles.values()) or 1.0
    active_kw = weighted / total_share if total_share else 0.0

    hours_per_day = int(module.get('hours_per_day') or 24)
    days_per_week = int(module.get('days_per_week') or 7)

    daily: dict[str, float] = {}
    for step in range(hours):
        stamp = start + timedelta(hours=step)
        day = stamp.strftime('%Y-%m-%d')
        expected_day = daily.setdefault(day, 0.0)
        if stamp.weekday() < days_per_week and stamp.hour < hours_per_day:
            daily[day] = expected_day + active_kw
    return daily


def _measurements_daily_kwh(conn: sqlite3.Connection, code: str) -> dict[str, float]:
    """Sum metered hourly kW into daily kWh for one machine (kW*1h = kWh)."""
    rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS day, SUM(active_power_kw) AS kwh"
        " FROM import_measurements WHERE machine_code = ?"
        " GROUP BY day",
        (code,),
    ).fetchall()
    return {day: kwh for day, kwh in rows}


def _mape_daily(expected: dict[str, float], real: dict[str, float]) -> float | None:
    """Daily-energy MAPE over days where the machine really consumed (>0)."""
    errors = [
        abs(expected[day] - real[day]) / real[day] * 100.0
        for day in real
        if real[day] > 0 and day in expected
    ]
    return (sum(errors) / len(errors)) if errors else None


def seed_db(db_path: Path, modules: list[dict]) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    for index, module in enumerate(modules, start=1):
        conn.execute(
            MACHINE_INSERT,
            (index, module['machine_code'], module.get('name', ''),
             module.get('category', ''), module['rated_power_kw'],
             module.get('voltage_v', 400), module.get('current_a', 0),
             module.get('power_factor', 0.85), module.get('phases', 3),
             module.get('thd_pct', 0), module.get('hours_per_day', 24),
             module.get('days_per_week', 7), module.get('load_factor', 0.5),
             module.get('criticality', 'ESENCIAL')),
        )
    conn.commit()
    conn.close()


def run_demo(hours: int = 168, machine_codes: list[str] | None = None) -> dict:
    """Execute the closed loop on a scratch copy of the catalog; return summary.

    Calibration writes happen on a temp COPY of machines/ (never the repo
    modules), so the demo is side-effect free.
    """
    from plant import plant_sim

    start = datetime(2026, 1, 5, 0, 0, 0)  # a Monday
    scratch = Path(tempfile.mkdtemp(prefix='gemelo_demo_'))
    try:
        machines_dir = scratch / 'machines'
        machines_dir.mkdir()
        modules = sorted(plant_sim.load_machines().values(),
                         key=lambda m: m['machine_code'])
        if machine_codes:
            modules = [m for m in modules if m['machine_code'] in machine_codes]
        modules = modules[:3]
        if not modules:
            raise SystemExit('no active machines to demo')
        for module in modules:
            target = machines_dir / module['machine_code']
            target.mkdir()
            (target / 'machine.json').write_text(
                json.dumps(module, indent=2, ensure_ascii=False) + '\n',
                encoding='utf-8',
            )

        db_path = scratch / 'demo.db'
        seed_db(db_path, modules)

        from app import create_app
        app = create_app(db_path=str(db_path), machines_dir=str(machines_dir))
        app.config['TESTING'] = True
        client = app.test_client()

        # 1) stream plant hours through the real ingestion endpoint
        from plant import feed_loop
        posted = 0
        for step in range(hours):
            records = feed_loop.build_hour_records(modules, start + timedelta(hours=step))
            result = client.post('/api/ingest/hourly', json={'records': records})
            assert result.status_code == 200, result.get_json()
            posted += result.get_json()['inserted']

        # 2) daily-energy MAPE before calibration, from the stored rows
        conn = sqlite3.connect(db_path)
        before = {}
        reals = {}
        for module in modules:
            code = module['machine_code']
            reals[code] = _measurements_daily_kwh(conn, code)
            before[code] = _mape_daily(
                _expected_daily_kwh(module, start, hours), reals[code])
        conn.close()

        # 3) calibrate through the real endpoint (LIVE-STREAM default)
        summaries = {}
        for module in modules:
            code = module['machine_code']
            result = client.post(f'/api/machines/{code}/calibrate')
            assert result.status_code == 200, (code, result.get_json())
            summaries[code] = result.get_json()

        # 4) daily-energy MAPE after calibration, reading the modules back
        after = {}
        for module in modules:
            code = module['machine_code']
            calibrated = json.loads(
                (machines_dir / code / 'machine.json').read_text(encoding='utf-8'))
            after[code] = _mape_daily(
                _expected_daily_kwh(calibrated, start, hours), reals[code])

        return {
            'hours': hours,
            'records_posted': posted,
            'machines': [
                {
                    'machine_code': m['machine_code'],
                    'mape_before_pct': None if before[m['machine_code']] is None
                    else round(before[m['machine_code']], 2),
                    'mape_after_pct': None if after[m['machine_code']] is None
                    else round(after[m['machine_code']], 2),
                    'load_factor': [summaries[m['machine_code']]['before']['load_factor'],
                                    summaries[m['machine_code']]['after']['load_factor']],
                }
                for m in modules
            ],
        }
    finally:
        print(f'[demo scratch: {scratch} — parent may remove]', file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--hours', type=int, default=168)
    args = parser.parse_args(argv)

    summary = run_demo(hours=args.hours)
    print(f"Lazo cerrado: {summary['records_posted']} horas ingestado, "
          f"{len(summary['machines'])} máquinas calibradas")
    for row in summary['machines']:
        improved = (row['mape_before_pct'] is not None
                    and row['mape_after_pct'] is not None
                    and row['mape_after_pct'] < row['mape_before_pct'])
        print(f"  {row['machine_code']}: MAPE {row['mape_before_pct']}% -> "
              f"{row['mape_after_pct']}% load_factor "
              f"{row['load_factor'][0]} -> {row['load_factor'][1]}"
              f" {'[MEJORÓ]' if improved else ''}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
