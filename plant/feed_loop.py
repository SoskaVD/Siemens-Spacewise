"""Continuous feed runner (Camino B) — pushes the synthetic plant into the API.

Streams the plant simulator's hourly measurements into POST /api/ingest/hourly
of a running backend, simulating a meter feed (e.g. SENTRON) so the twin loop
can be exercised end to end without hardware. Pointing at REAL data later only
means replacing this producer: the ingestion, state estimation and calibration
side is identical for synthetic and real measurements.

Usage:
    python plant/feed_loop.py --base-url http://127.0.0.1:5000 \
        --hours 168 --interval 0.2 [--machines HVAC-001,BOMB-007] [--start 2026-01-05T00]

Stdlib only (urllib), matching the plant package's dependency policy.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plant import plant_sim  # noqa: E402

INGEST_ENDPOINT = '/api/ingest/hourly'
MAX_RECORDS_PER_POST = 500


def build_hour_records(machines: list[dict], hour_start: datetime) -> list[dict]:
    """One deterministic plant hour for every machine, ingest-ready records.

    plant_sim.generate_series seeds the RNG from (machine_code, start hour),
    so a single-hour call is byte-stable and re-streaming the same hour always
    replays the same values (safe for idempotent upsert). Note it is an
    independently seeded hour, NOT a slice of a multi-hour window series.
    """
    records: list[dict] = []
    for machine in machines:
        rows = plant_sim.generate_series(machine, hour_start, 1)
        for row in rows:
            records.append({
                'machine_code': row['machine_code'],
                'ts': row['ts'],
                'active_power_kw': row['active_power_kw'],
            })
    return records


def post_records(base_url: str, records: list[dict], *, opener=None) -> dict:
    """POST a batch to the ingest endpoint; returns the parsed JSON response."""
    url = base_url.rstrip('/') + INGEST_ENDPOINT
    payload = json.dumps({'records': records}).encode('utf-8')
    request = urllib.request.Request(
        url, data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    open_fn = opener or urllib.request.urlopen
    with open_fn(request, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def run_loop(base_url: str, machines: list[dict], start: datetime, hours: int,
             interval: float, *, sleep=time.sleep, poster=post_records) -> dict:
    """Stream `hours` plant hours to the API, batching <= MAX_RECORDS_PER_POST."""
    summary = {'batches': 0, 'records': 0, 'inserted': 0, 'updated': 0}
    base_hour = start.replace(minute=0, second=0, microsecond=0)
    for step in range(hours):
        hour_start = base_hour + timedelta(hours=step)
        records = build_hour_records(machines, hour_start)
        for offset in range(0, len(records), MAX_RECORDS_PER_POST):
            batch = records[offset:offset + MAX_RECORDS_PER_POST]
            result = poster(base_url, batch)
            summary['batches'] += 1
            summary['records'] += len(batch)
            summary['inserted'] += result.get('inserted', 0)
            summary['updated'] += result.get('updated', 0)
        if interval > 0 and step < hours - 1:
            sleep(interval)
    return summary


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base-url', default='http://127.0.0.1:5000')
    parser.add_argument('--start', default=None,
                        help='first plant hour, ISO-like YYYY-MM-DDTHH (default: now)')
    parser.add_argument('--hours', type=int, default=168)
    parser.add_argument('--interval', type=float, default=0.2,
                        help='seconds of simulated wall time between hours (0 = no wait)')
    parser.add_argument('--machines', default=None,
                        help='comma-separated machine codes (default: whole catalog)')
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.hours < 1:
        print('hours must be >= 1', file=sys.stderr)
        return 2
    if args.start:
        start = datetime.strptime(args.start, '%Y-%m-%dT%H')
    else:
        start = datetime.now().replace(minute=0, second=0, microsecond=0)
    codes = args.machines.split(',') if args.machines else None
    machines = list(plant_sim.load_machines().values())
    if codes:
        wanted = {c.strip() for c in codes}
        machines = [m for m in machines if m['machine_code'] in wanted]
        missing = wanted - {m['machine_code'] for m in machines}
        if missing:
            print(f'unknown machine codes: {sorted(missing)}', file=sys.stderr)
            return 2
    if not machines:
        print('no active machines found under machines/', file=sys.stderr)
        return 2

    print(f'Feeding {len(machines)} machines x {args.hours} hours '
          f'from {start:%Y-%m-%d %H:%M} into {args.base_url}')
    try:
        summary = run_loop(args.base_url, machines, start, args.hours, args.interval)
    except urllib.error.URLError as exc:
        print(f'ingestion failed: {exc}', file=sys.stderr)
        return 1
    print(f'Done: {summary["records"]} records in {summary["batches"]} batches '
          f'({summary["inserted"]} inserted, {summary["updated"]} updated)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
