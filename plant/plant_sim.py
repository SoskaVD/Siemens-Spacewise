"""Synthetic plant generator for the digital-twin closed loop.

Produces realistic hourly power measurements for every machine in the
``machines/<CODE>/machine.json`` catalog, standing in for real meter
hardware (spec S1: no access to machinery). The output is indistinguishable
in shape from a CSV import accepted by ``POST /api/import/real`` and carries
a known ground truth (``state`` per row) so calibration (path A) can later
recover parameters from it.

The generator deliberately DEVIATES from the catalog prior (spec S2, log L2):

- work-cycle state shares drift by a seeded multiplicative factor,
- the day/night and weekday schedule differs from ``hours_per_day`` /
  ``days_per_week``,
- measured active power is ``rated_power_kw * load_factor * degradation``
  with a seeded degradation multiplier in ~[1.05, 1.25],
- STANDBY rows sit at ``rated_power_kw * standby_pct / 100``,
- Gaussian noise (sigma = 2% of the value, clamped at 0) is added,
- occasional seeded outages appear as contiguous OFF blocks,
- OFF -> active transitions get a short startup surge scaled by
  ``startup_time_s`` (hourly resolution, kept simple and deterministic).

Everything is seeded from ``machine_code + start_dt`` so the same inputs
always yield the same series. Only the Python standard library is used.
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
_CSV_COLUMNS = ("machine_code", "ts", "active_power_kw")
_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MACHINES_DIR = _REPO_ROOT / "machines"

# Power-model constants (documented in the module docstring).
_NOISE_SIGMA_FRACTION = 0.02
_DEGRADATION_RANGE = (1.05, 1.25)
_PARTIAL_FRACTION = 0.65
_SHARE_DRIFT = 0.35
_OUTAGE_LENGTH_RANGE = (2, 6)


def _stable_seed(text: str) -> int:
    """Return a deterministic 64-bit seed for a string (FNV-1a).

    Avoids process-dependent hash randomization so the same
    machine_code + start_dt always replays the same series.
    """
    value = 1469598103934665603
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * 1099511628211) % (2 ** 64)
    return value


def _classify_state(name: str) -> str:
    """Map a work-cycle state name to its power model class.

    Handles the inherited mangled names in the catalog (e.g. ``n_parcial``)
    by substring matching, never by renaming (spec S4e).
    """
    lowered = name.lower()
    if "standby" in lowered:
        return "standby"
    if lowered == "off":
        return "off"
    # Partial-load states (incl. mangled n_parcial) meter at a distinct band;
    # full/other active states (e.g. n_plena) share the RUNNING model.
    if "partial" in lowered or "parcial" in lowered:
        return "partial"
    return "running"


def _normalized_shares(work_cycles: dict) -> tuple[list, list]:
    """Return (states, weights) with weights summing to 1."""
    states = list(work_cycles)
    weights = []
    for state in states:
        try:
            weight = float(work_cycles[state])
        except (TypeError, ValueError):
            weight = 0.0
        weights.append(max(weight, 0.0))
    total = sum(weights)
    if total <= 0:
        weights = [1.0 / len(states)] * len(states)
    else:
        weights = [w / total for w in weights]
    return states, weights


def load_machines(machines_dir=None) -> dict:
    """Discover active machine modules as ``{machine_code: machine_dict}``.

    Mirrors the MATLAB discovery rules (``sim_catalog.m``): folders whose
    name starts with ``'_'`` or ``'.'`` are skipped (e.g. ``_TEMPLATE``),
    and only modules with ``"active": 1`` are kept (``active`` defaults to
    1 when absent). Folders without a readable machine.json are ignored so
    generation never breaks on catalog bookkeeping.
    """
    base = Path(machines_dir) if machines_dir is not None else DEFAULT_MACHINES_DIR
    machines = {}
    if not base.is_dir():
        raise FileNotFoundError(f"Machines directory not found: {base}")
    for entry in sorted(base.iterdir()):
        name = entry.name
        if not entry.is_dir() or name.startswith("_") or name.startswith("."):
            continue
        module_path = entry / "machine.json"
        if not module_path.is_file():
            continue
        try:
            machine = json.loads(module_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(machine, dict):
            continue
        if machine.get("active", 1) != 1:
            continue
        code = machine.get("machine_code") or name
        machine.setdefault("machine_code", code)
        machines[code] = machine
    return machines


def generate_series(machine: dict, start_dt: datetime, hours: int) -> list:
    """Generate ``hours`` hourly measurement rows for one machine.

    Each row is a dict with keys ``machine_code``, ``ts``
    (``'YYYY-MM-DD HH:MM:SS'`` on the hour), ``active_power_kw`` (float,
    >= 0) and ``state`` (the ground-truth state name: one of the machine's
    ``work_cycles`` keys, or ``'OFF'`` when the machine is not scheduled to
    run or is hit by an outage).

    Deterministic: the RNG is seeded from machine_code + start_dt (truncated
    to the hour), so the same inputs always yield the same series.
    """
    if not isinstance(machine, dict):
        raise TypeError("machine must be a dict loaded from machine.json")
    code = machine.get("machine_code")
    if not code:
        raise ValueError("machine dict is missing 'machine_code'")
    work_cycles = machine.get("work_cycles") or {}
    if not work_cycles:
        raise ValueError(f"machine {code} has no work_cycles")
    hours = int(hours)
    if hours < 1:
        raise ValueError("hours must be >= 1")

    start = start_dt.replace(minute=0, second=0, microsecond=0)
    rng = random.Random(_stable_seed(f"{code}|{start.strftime(_TS_FORMAT)}"))

    rated = float(machine.get("rated_power_kw", 0.0) or 0.0)
    load_factor = float(machine.get("load_factor", 1.0) or 0.0)
    standby_kw = rated * float(machine.get("standby_pct", 0.0) or 0.0) / 100.0
    startup_time_s = float(machine.get("startup_time_s", 0.0) or 0.0)
    startup_multiplier = float(machine.get("startup_multiplier", 1.0) or 1.0)

    states, prior_weights = _normalized_shares(work_cycles)
    classes = {state: _classify_state(state) for state in states}

    # --- deliberate deviation from the catalog prior --------------------
    # State shares: multiplicative seeded drift, then renormalize.
    drifted = [
        max(w * (1.0 + rng.uniform(-_SHARE_DRIFT, _SHARE_DRIFT)), 0.01)
        for w in prior_weights
    ]
    drift_total = sum(drifted)
    shares = [w / drift_total for w in drifted]

    # Degradation multiplier (seeded, stable across the series).
    degradation = rng.uniform(*_DEGRADATION_RANGE)

    # Schedule deviation: actual window and days differ from prior.
    hours_per_day = int(machine.get("hours_per_day", 24) or 24)
    days_per_week = int(machine.get("days_per_week", 7) or 7)
    actual_hours_per_day = min(24, max(4, hours_per_day + rng.randint(-3, 3)))
    actual_days = min(7, max(1, days_per_week + rng.randint(-1, 1)))
    work_start_hour = rng.randint(0, 23)
    day_shift = rng.randint(1, 3)  # weekend/weekday pattern shifts by 1..3 days

    # Occasional seeded outages as contiguous OFF blocks.
    outage_hours = set()
    n_outages = rng.choices([0, 1, 2, 3], weights=[4, 3, 2, 1], k=1)[0]
    for _ in range(n_outages):
        length = rng.randint(*_OUTAGE_LENGTH_RANGE)
        if hours <= length:
            outage_hours.update(range(hours))
        else:
            pos = rng.randint(0, hours - length)
            outage_hours.update(range(pos, pos + length))

    def _scheduled(dt: datetime) -> bool:
        if ((dt.weekday() - day_shift) % 7) >= actual_days:
            return False
        if actual_hours_per_day >= 24:
            return True
        return ((dt.hour - work_start_hour) % 24) < actual_hours_per_day

    rows = []
    was_off = True
    for index in range(hours):
        stamp = start + timedelta(hours=index)
        if index in outage_hours or not _scheduled(stamp):
            state = "OFF"
        else:
            state = rng.choices(states, weights=shares, k=1)[0]

        klass = classes.get(state, "running")
        if state == "OFF" or klass == "off":
            ideal = 0.0
            state = "OFF"
        elif klass == "standby":
            ideal = standby_kw
        else:
            # RUNNING = rated * load_factor * seeded degradation; PARTIAL is
            # metered at _PARTIAL_FRACTION of that level so power-band
            # classification can recover the PARTIAL share from measurements
            # alone (identical levels would collapse both states into one
            # band, leaving calibration blind to it).
            ideal = rated * load_factor * degradation
            if klass == "partial":
                ideal *= _PARTIAL_FRACTION

        # Startup surge on OFF -> active transitions (hourly resolution).
        is_off = state == "OFF"
        if was_off and not is_off and startup_time_s > 0 and ideal > 0:
            span = min(startup_time_s / 3600.0, 1.0)
            surge = 1.0 + max(startup_multiplier - 1.0, 0.0) * span
            ideal *= surge
        was_off = is_off

        # Gaussian noise (sigma = 2% of the value), clamped at >= 0.
        sigma = ideal * _NOISE_SIGMA_FRACTION
        measured = ideal + rng.gauss(0.0, sigma) if sigma > 0 else ideal
        measured = max(0.0, round(measured, 3))

        rows.append({
            "machine_code": code,
            "ts": stamp.strftime(_TS_FORMAT),
            "active_power_kw": measured,
            "state": state,
        })
    return rows


def generate_catalog(start_dt: datetime, hours: int, machine_codes=None) -> list:
    """Generate hourly rows for many machines (sorted by machine code).

    ``machine_codes`` optionally restricts generation to a subset; unknown
    codes are ignored. Rows are concatenated per machine in code order so
    the combined output is deterministic.
    """
    machines = load_machines()
    if machine_codes is not None:
        wanted = {str(code).strip().upper() for code in machine_codes}
        machines = {c: m for c, m in machines.items() if c in wanted}
    rows = []
    for code in sorted(machines):
        rows.extend(generate_series(machines[code], start_dt, hours))
    return rows


def write_csv(rows, path) -> Path:
    """Write measurement rows as a CSV accepted by POST /api/import/real.

    The header is exactly ``machine_code,ts,active_power_kw``; the
    ground-truth ``state`` column is deliberately NOT emitted because a real
    meter would not expose it. Returns the path written.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_CSV_COLUMNS)
        for row in rows:
            writer.writerow([
                row["machine_code"],
                row["ts"],
                f"{float(row['active_power_kw']):.3f}",
            ])
    return out_path
