"""Calibration loop (Camino A) — recover a machine's real parameters from measurements.

The twin is only a twin when data can update the model. This module takes the
real (or synthetic-plant) hourly measurements already stored in
import_measurements and re-estimates the operating model of a machine:

- work-cycle state SHARES, by classifying measured power into bands derived
  from the module's own prior model (zero / standby / partial / running).
  State NAMES are never renamed (S4e): calibrated shares are written back to
  the exact keys the module already has (including inherited mangled names
  such as ``n_plena``).
- ``load_factor`` from the RUNNING band's median power (metered degradation is
  absorbed into the model prior, which is the point of calibrating).
- ``standby_pct`` from the STANDBY band's median power.
- ``hours_per_day`` / ``days_per_week`` from the observed activity schedule.

The module update is traceable: a ``_calibration`` block (an OPTIONAL key the
MATLAB catalog tolerates by design — sim_catalog.m only enforces required
fields) stores before/after snapshots and the provenance of the import used,
and ``machine.json.bak`` keeps the bytes of the FIRST-ever calibration so a
bad loop never destroys the original catalog values.

Pure standard library; no DB and no Flask imports so it stays unit-testable
from both the web backend and the plant runners.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plant import plant_sim

MIN_HOURS_FOR_CALIBRATION = 24

# Power-band boundaries are derived from the module's prior model. A measured
# hour is classified by its distance to each expected level; _MARGIN_FRACTION
# defines how wide each band is around its level before the next one wins.
_MARGIN_FRACTION = 0.18

_EXPECTED_KEYS = (
    "work_cycles",
    "load_factor",
    "standby_pct",
    "hours_per_day",
    "days_per_week",
)


class CalibrationError(ValueError):
    """Raised when measurements or the module make calibration impossible."""


def expected_levels(machine: dict) -> dict[str, float]:
    """Expected metered power per band, derived from the module's prior model.

    Mirrors the plant's own power model so classification is consistent on
    both sides of the loop: standby = rated * standby_pct / 100, running =
    rated * load_factor, partial = running * _PARTIAL_FRACTION.
    """
    rated = float(machine.get("rated_power_kw") or 0.0)
    if rated <= 0:
        raise CalibrationError("machine module has no positive rated_power_kw")
    load = float(machine.get("load_factor") or 0.0)
    standby_kw = rated * float(machine.get("standby_pct") or 0.0) / 100.0
    running_kw = rated * load
    partial_kw = running_kw * plant_sim._PARTIAL_FRACTION
    return {
        "off": 0.0,
        "standby": standby_kw,
        "partial": partial_kw,
        "running": running_kw,
    }


def classify_rows(machine: dict, rows: list[dict]) -> list[str]:
    """Assign each measurement row a power-band class name."""
    levels = expected_levels(machine)
    rated = float(machine["rated_power_kw"])
    classes: list[str] = []
    for row in rows:
        power = row.get("active_power_kw")
        if power is None:
            raise CalibrationError("every measurement row needs active_power_kw")
        power = float(power)
        if power <= levels["standby"] * 0.5 and power < rated * 0.005:
            classes.append("off")
            continue
        best = min(
            ("standby", "partial", "running"),
            key=lambda band: abs(power - levels[band]),
        )
        classes.append(best)
    return classes


def _calibratable_states(work_cycles: dict) -> tuple[list[str], dict[str, str]]:
    """Split module states into the keys calibration may update.

    Only keys that map to a measurable band (running/partial/standby via the
    shared plant classifier) participate in band estimation. Unknown keys
    keep their prior share and their share is taken out of the active-time
    budget proportionally, so the total still renormalizes to 1.0.
    """
    mapping: dict[str, str] = {}
    unknown: list[str] = []
    for key in work_cycles:
        klass = plant_sim._classify_state(key)
        if klass in ("running", "partial", "standby", "off"):
            mapping[key] = klass
        else:  # pragma: no cover - defensive
            unknown.append(key)
    return unknown, mapping


def calibrate(machine: dict, rows: list[dict]) -> dict:
    """Return the calibrated machine dict (with ``_calibration`` trace).

    ``rows`` are measurement dicts with at least ``ts`` and
    ``active_power_kw`` (as returned by queries.get_real_measurements).
    """
    work_cycles = machine.get("work_cycles")
    if not isinstance(work_cycles, dict) or not work_cycles:
        raise CalibrationError("machine module has no work_cycles")

    if len(rows) < MIN_HOURS_FOR_CALIBRATION:
        raise CalibrationError(
            f"need at least {MIN_HOURS_FOR_CALIBRATION} hours of measurements,"
            f" got {len(rows)}"
        )

    classes = classify_rows(machine, rows)
    counts = Counter(classes)
    total = len(rows)

    # Band -> measured share of all observed hours (off included).
    measured = {
        band: counts[band] / total for band in ("off", "standby", "partial", "running")
    }

    unknown_keys, state_class = _calibratable_states(work_cycles)
    prior = {key: float(work_cycles[key]) for key in work_cycles}
    unknown_prior_sum = sum(prior[key] for key in unknown_keys)

    # Distribute the (1 - unknown_prior_sum) budget across measured bands,
    # per class, proportionally to prior within the same class.
    calibratable_budget = 1.0 - unknown_prior_sum
    active_share = measured["standby"] + measured["partial"] + measured["running"]
    if active_share <= 0:
        raise CalibrationError("measurements never show the machine consuming power")

    new_cycles: dict[str, float] = {}
    for key in unknown_keys:
        new_cycles[key] = round(prior[key], 6)
    for key, klass in state_class.items():
        if klass == "off":
            new_cycles[key] = round(prior[key], 6)
            continue
        class_members = [k for k, c in state_class.items() if c == klass and c != "off"]
        class_prior = sum(prior[k] for k in class_members)
        share_of_class = (prior[key] / class_prior) if class_prior > 0 else 1.0 / len(class_members)
        band_share = measured[klass] / active_share  # renormalize over active states
        new_cycles[key] = round(band_share * share_of_class * calibratable_budget, 6)

    # Fix float drift so the contract "shares sum to 1" holds exactly.
    drift = 1.0 - sum(new_cycles.values())
    if abs(drift) > 1e-9:
        biggest = max(new_cycles, key=lambda k: new_cycles[k])
        new_cycles[biggest] = round(new_cycles[biggest] + drift, 6)

    medians = _band_medians(machine, rows, classes)
    rated = float(machine["rated_power_kw"])
    new_load = max(medians["running"] / rated, 0.05)
    new_standby_pct = max(medians["standby"] / rated * 100.0, 0.0)

    schedule = _schedule_estimates(machine, rows, classes)

    calibrated = dict(machine)
    calibrated["work_cycles"] = new_cycles
    calibrated["load_factor"] = round(new_load, 4)
    calibrated["standby_pct"] = round(new_standby_pct, 2)
    calibrated["hours_per_day"] = schedule["hours_per_day"]
    calibrated["days_per_week"] = schedule["days_per_week"]
    calibrated["_calibration"] = {
        "calibrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "before": {key: _snapshot(machine.get(key)) for key in _EXPECTED_KEYS},
        "after": {key: _snapshot(calibrated.get(key)) for key in _EXPECTED_KEYS},
        "calibrated_from": {
            "source": "import",
            "hours_analyzed": total,
            "start_ts": min(row["ts"] for row in rows),
            "end_ts": max(row["ts"] for row in rows),
        },
    }
    return calibrated


def _snapshot(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: round(float(v), 6) if isinstance(v, (int, float)) else v
                for k, v in value.items()}
    if isinstance(value, float):
        return round(value, 6)
    return value


def _band_medians(machine: dict, rows: list[dict], classes: list[str]) -> dict[str, float]:
    groups: dict[str, list[float]] = {"standby": [], "partial": [], "running": []}
    for row, klass in zip(rows, classes):
        if klass in groups:
            groups[klass].append(float(row["active_power_kw"]))
    medians: dict[str, float] = {}
    for band, values in groups.items():
        if values:
            ordered = sorted(values)
            medians[band] = ordered[len(ordered) // 2]
        else:
            # No samples for a band: keep the prior level implied by the module
            # so a sparse import cannot collapse the model to zero.
            medians[band] = expected_levels(machine)[band]
    return medians


def _schedule_estimates(machine: dict, rows: list[dict], classes: list[str]) -> dict[str, int]:
    per_day_active: dict[str, int] = {}
    for row, klass in zip(rows, classes):
        if klass in ("standby", "partial", "running"):
            day = row["ts"][:10]
            per_day_active[day] = per_day_active.get(day, 0) + 1

    observed_days = set()
    for row in rows:
        observed_days.add(row["ts"][:10])
    if not observed_days:
        return {
            "hours_per_day": int(machine.get("hours_per_day") or 8),
            "days_per_week": int(machine.get("days_per_week") or 5),
        }

    active_hours = sum(per_day_active.values())
    hours_per_day = round(active_hours / len(observed_days))
    days_with_activity = len([d for d in per_day_active if per_day_active[d] > 0])
    days_per_week = round(days_with_activity / len(observed_days) * 7)
    return {
        "hours_per_day": min(24, max(1, hours_per_day)),
        "days_per_week": min(7, max(1, days_per_week)),
    }


def module_path(machines_dir: str | Path, machine_code: str) -> Path:
    return Path(machines_dir) / machine_code / "machine.json"


def read_module(path: Path) -> str:
    """Return the raw JSON text of a module, raising CalibrationError on garbage."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CalibrationError(f"machine module not found: {path}") from exc
    import json as _json
    try:
        _json.loads(text)
    except ValueError as exc:
        raise CalibrationError(f"machine module is not valid JSON: {exc}") from exc
    return text
