"""Pure forecasting / scenario math for the energy assistant.

No database, no Flask, no Ollama imports: every function takes plain numbers or
already-fetched rows and returns plain dicts, so it is unit-testable in
isolation (same contract discipline as ``plant.calibration``). The assistant's
tools (``assistant.tools``) fetch data from SQLite and delegate the arithmetic
here, which keeps the "the model never invents numbers" guarantee honest: the
numbers are produced by code a human can read and check.

All energy is in kWh, power in kW, money in the currency of ``price_kwh``.
"""

from __future__ import annotations

from typing import Any

HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7
HOURS_PER_WEEK = HOURS_PER_DAY * DAYS_PER_WEEK


def daily_energy_from_hours(total_energy_kwh: float, hours_processed: int) -> float:
    """Average energy per day implied by a partial simulation.

    ``hours_processed`` is how many hourly rows exist so far (the continuous
    simulator appends them over time). Returns 0.0 when nothing is processed
    yet so callers degrade gracefully instead of dividing by zero.
    """
    hours = max(int(hours_processed or 0), 0)
    if hours <= 0:
        return 0.0
    return float(total_energy_kwh or 0.0) / hours * HOURS_PER_DAY


def apply_bias_correction(simulated_kwh: float, mean_bias_pct: float | None) -> float:
    """Correct a simulated figure toward reality using measured bias.

    ``mean_bias_pct`` is the simulator's mean bias vs real data as produced by
    ``queries.get_comparison`` (``(sim - real) / real * 100``). A positive bias
    means the model over-estimates, so the real-world estimate is
    ``sim / (1 + bias/100)``. ``None`` (no overlap measured) leaves the value
    untouched. The divisor is floored so a pathological bias can never flip the
    sign or blow up.
    """
    if mean_bias_pct is None:
        return float(simulated_kwh or 0.0)
    divisor = 1.0 + float(mean_bias_pct) / 100.0
    if divisor <= 0.01:
        divisor = 0.01
    return float(simulated_kwh or 0.0) / divisor


def project_energy(
    daily_energy_kwh: float,
    horizon_days: int,
    price_kwh: float = 0.0,
    mean_bias_pct: float | None = None,
) -> dict[str, Any]:
    """Project energy and cost over a horizon from an average daily figure.

    When ``mean_bias_pct`` is given the daily figure is bias-corrected first, so
    the projection reflects what the meters actually show rather than the raw
    simulation. Returns both the raw and corrected daily rates for transparency.
    """
    horizon_days = max(int(horizon_days or 0), 0)
    raw_daily = float(daily_energy_kwh or 0.0)
    corrected_daily = apply_bias_correction(raw_daily, mean_bias_pct)
    projected = corrected_daily * horizon_days
    return {
        "horizon_days": horizon_days,
        "daily_energy_kwh": round(corrected_daily, 3),
        "raw_daily_energy_kwh": round(raw_daily, 3),
        "bias_corrected": mean_bias_pct is not None,
        "mean_bias_pct": (round(float(mean_bias_pct), 2)
                          if mean_bias_pct is not None else None),
        "projected_energy_kwh": round(projected, 2),
        "projected_cost": round(projected * float(price_kwh or 0.0), 2),
        "price_kwh": float(price_kwh or 0.0),
    }


def weekly_energy_kwh(
    rated_power_kw: float,
    load_factor: float,
    hours_per_day: float,
    days_per_week: float,
) -> float:
    """Energy a machine uses in a typical week for a given operating schedule.

    A transparent first-order model matching ``sim_machine``: while scheduled,
    the machine draws ``rated_power_kw * load_factor`` on average; outside the
    schedule it is OFF (≈0). Partial/standby cycles are folded into
    ``load_factor``, which is what calibration already estimates from meters.
    """
    running_kw = float(rated_power_kw or 0.0) * float(load_factor or 0.0)
    on_hours = _clamp(hours_per_day, 0, 24) * _clamp(days_per_week, 0, 7)
    return running_kw * on_hours


def scenario_savings(
    machine: dict,
    *,
    new_hours_per_day: float | None = None,
    new_days_per_week: float | None = None,
    load_scale: float = 1.0,
    horizon_days: int = 30,
    price_kwh: float = 0.0,
) -> dict[str, Any]:
    """"What if" savings from changing a machine's schedule or load.

    ``machine`` is a catalog dict (rated_power_kw, load_factor, hours_per_day,
    days_per_week). Any ``new_*`` left as ``None`` keeps the current value;
    ``load_scale`` multiplies the load factor (e.g. 0.9 = run 10% lighter).
    Returns baseline vs scenario energy/cost over the horizon and the saving
    (positive = less energy used). Negative savings (a more intensive schedule)
    are reported honestly rather than clamped.
    """
    rated = float(machine.get("rated_power_kw") or 0.0)
    base_load = float(machine.get("load_factor") or 0.0)
    base_hpd = float(machine.get("hours_per_day") or 0.0)
    base_dpw = float(machine.get("days_per_week") or 0.0)

    new_hpd = base_hpd if new_hours_per_day is None else float(new_hours_per_day)
    new_dpw = base_dpw if new_days_per_week is None else float(new_days_per_week)
    new_load = base_load * float(load_scale if load_scale is not None else 1.0)

    base_weekly = weekly_energy_kwh(rated, base_load, base_hpd, base_dpw)
    new_weekly = weekly_energy_kwh(rated, new_load, new_hpd, new_dpw)

    horizon_days = max(int(horizon_days or 0), 0)
    weeks = horizon_days / DAYS_PER_WEEK
    base_energy = base_weekly * weeks
    new_energy = new_weekly * weeks
    saved_energy = base_energy - new_energy
    price = float(price_kwh or 0.0)

    base_energy_r = round(base_energy, 2)
    saved_pct = (round(saved_energy / base_energy * 100.0, 2)
                 if base_energy > 0 else None)
    return {
        "machine_code": machine.get("machine_code"),
        "horizon_days": horizon_days,
        "baseline": {
            "hours_per_day": base_hpd,
            "days_per_week": base_dpw,
            "load_factor": round(base_load, 4),
            "energy_kwh": base_energy_r,
            "cost": round(base_energy * price, 2),
        },
        "scenario": {
            "hours_per_day": new_hpd,
            "days_per_week": new_dpw,
            "load_factor": round(new_load, 4),
            "energy_kwh": round(new_energy, 2),
            "cost": round(new_energy * price, 2),
        },
        "saved_energy_kwh": round(saved_energy, 2),
        "saved_cost": round(saved_energy * price, 2),
        "saved_pct": saved_pct,
        "price_kwh": price,
    }


def detect_anomalies(
    series: list[dict],
    *,
    threshold_pct: float = 30.0,
    limit: int = 10,
) -> dict[str, Any]:
    """Hours where real power deviates most from the simulated profile.

    ``series`` is the aligned list from ``queries.get_comparison`` (each row has
    ``ts``, ``simulated_kw``, ``real_kw``). An hour is flagged when the absolute
    percentage error vs the real reading exceeds ``threshold_pct``; hours with a
    real reading of ~0 are skipped (the same division-by-zero guard the MAPE
    uses). The ``limit`` worst offenders are returned, largest deviation first.
    """
    flagged: list[dict[str, Any]] = []
    for row in series:
        real = float(row.get("real_kw") or 0.0)
        sim = float(row.get("simulated_kw") or 0.0)
        if real <= 0:
            continue
        dev_pct = (sim - real) / real * 100.0
        if abs(dev_pct) >= float(threshold_pct):
            flagged.append({
                "ts": row.get("ts"),
                "simulated_kw": round(sim, 3),
                "real_kw": round(real, 3),
                "deviation_pct": round(dev_pct, 2),
            })
    flagged.sort(key=lambda r: abs(r["deviation_pct"]), reverse=True)
    return {
        "threshold_pct": float(threshold_pct),
        "hours_checked": len(series),
        "anomalies_found": len(flagged),
        "anomalies": flagged[: max(int(limit or 0), 0)],
    }


def _clamp(value: Any, low: float, high: float) -> float:
    try:
        v = float(value or 0.0)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, v))
