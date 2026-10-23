"""Tests for the synthetic plant generator (plant/plant_sim.py).

Covers task T1 of odd/tasks/gemelo-lazo-cerrado.md (specs S1, S2, S4c):
determinism, timestamp/power contracts, CSV compatibility with
POST /api/import/real, ground-truth deviation from the catalog prior,
machine discovery rules, and non-negative noise clamping.
"""

import csv
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from plant import plant_sim

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINE_CODE_RE = re.compile(r"^[A-Z]{2,10}-\d{1,5}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
CSV_HEADER = ["machine_code", "ts", "active_power_kw"]

START = datetime(2026, 3, 2, 0, 0, 0)  # a Monday
HOURS = 24 * 14


def _make_machine(code="ZZX-900", **overrides):
    """Return a minimal machine dict compatible with the catalog schema."""
    machine = {
        "machine_code": code,
        "rated_power_kw": 10.0,
        "hours_per_day": 16,
        "days_per_week": 5,
        "load_factor": 0.6,
        "work_cycles": {"RUNNING": 0.6, "PARTIAL": 0.2, "STANDBY": 0.2},
        "startup_time_s": 5,
        "startup_multiplier": 5.0,
        "standby_pct": 2,
        "active": 1,
    }
    machine.update(overrides)
    return machine


class TestDiscovery:
    """Machine loading mirrors the MATLAB discovery rules (sim_catalog.m)."""

    def test_skips_underscore_and_dot_and_inactive(self):
        scratch = Path(tempfile.mkdtemp(prefix="plant_sim_test_"))
        try:
            # active == 1 module: must be discovered
            good = scratch / "ZZA-001"
            good.mkdir()
            (good / "machine.json").write_text(
                json.dumps(_make_machine("ZZA-001")), encoding="utf-8"
            )
            # active == 0 module: must be excluded
            off = scratch / "ZZB-002"
            off.mkdir()
            (off / "machine.json").write_text(
                json.dumps(_make_machine("ZZB-002", active=0)), encoding="utf-8"
            )
            # underscore-prefixed folder: must be excluded
            under = scratch / "_ZZC-003"
            under.mkdir()
            (under / "machine.json").write_text(
                json.dumps(_make_machine("ZZC-003")), encoding="utf-8"
            )
            # dot-prefixed folder: must be excluded
            dot = scratch / ".ZZD-004"
            dot.mkdir()
            (dot / "machine.json").write_text(
                json.dumps(_make_machine("ZZD-004")), encoding="utf-8"
            )
            # folder without machine.json: silently ignored
            (scratch / "ZZE-005").mkdir()

            machines = plant_sim.load_machines(scratch)
            assert set(machines) == {"ZZA-001"}
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_real_catalog_only_active_codes(self):
        machines = plant_sim.load_machines()
        assert len(machines) >= 100
        for code, machine in machines.items():
            assert MACHINE_CODE_RE.match(code)
            assert machine.get("active", 1) == 1
            assert not code.startswith("_")
        # The template module must never appear in the catalog view.
        assert "NEW-001" not in machines


class TestSeriesContract:
    """Row shape and value contracts of generate_series."""

    def test_row_keys_and_state_membership(self):
        machine = _make_machine()
        rows = plant_sim.generate_series(machine, START, HOURS)
        assert len(rows) == HOURS
        states = set(machine["work_cycles"]) | {"OFF"}
        for row in rows:
            assert set(row) == {"machine_code", "ts", "active_power_kw", "state"}
            assert row["machine_code"] == machine["machine_code"]
            assert row["state"] in states

    def test_timestamp_format_hourly_and_monotonic(self):
        machine = _make_machine()
        rows = plant_sim.generate_series(machine, START, HOURS)
        prev = None
        for row in rows:
            assert TS_RE.match(row["ts"])
            dt = datetime.strptime(row["ts"], "%Y-%m-%d %H:%M:%S")
            assert dt.minute == 0 and dt.second == 0
            if prev is not None:
                assert (dt - prev).total_seconds() == 3600
            prev = dt
        assert rows[0]["ts"] == START.strftime("%Y-%m-%d %H:%M:%S")

    def test_off_rows_are_exactly_zero(self):
        machine = _make_machine()
        rows = plant_sim.generate_series(machine, START, HOURS)
        for row in rows:
            if row["state"] == "OFF":
                assert row["active_power_kw"] == 0.0

    def test_power_is_non_negative_float(self):
        machine = _make_machine()
        rows = plant_sim.generate_series(machine, START, 48)
        for row in rows:
            assert isinstance(row["active_power_kw"], float)
            assert row["active_power_kw"] >= 0.0


class TestDeterminism:
    """Seed derived from machine_code + start_dt pins the whole series."""

    def test_same_inputs_identical_series(self):
        machine = _make_machine()
        a = plant_sim.generate_series(machine, START, 72)
        b = plant_sim.generate_series(machine, START, 72)
        assert a == b

    def test_different_start_dt_diverges(self):
        machine = _make_machine()
        from datetime import timedelta

        a = plant_sim.generate_series(machine, START, 72)
        b = plant_sim.generate_series(machine, START + timedelta(hours=1), 72)
        assert [r["state"] for r in a] != [r["state"] for r in b]


class TestGroundTruthDeviation:
    """The generator must deliberately deviate from the catalog prior."""

    def test_running_fraction_deviates_from_prior(self):
        machines = plant_sim.load_machines()
        running = [
            (code, m)
            for code, m in machines.items()
            if "RUNNING" in m.get("work_cycles", {})
        ]
        assert running
        deviating = 0
        for code, machine in running[:12]:
            prior = machine["work_cycles"]["RUNNING"]
            rows = plant_sim.generate_series(machine, START, HOURS)
            observed = sum(1 for r in rows if r["state"] == "RUNNING") / len(rows)
            if abs(observed - prior) > 0.05:
                deviating += 1
        assert deviating >= 1, (
            "no seeded machine deviates from its RUNNING prior by > 0.05"
        )

    def test_measured_running_power_above_prior_estimate(self):
        """RUNNING power = rated * load_factor * degradation(1.05..1.25)."""
        machine = _make_machine(rated_power_kw=100.0, load_factor=0.5)
        rows = plant_sim.generate_series(machine, START, HOURS)
        active = [r for r in rows if r["state"] == "RUNNING"]
        assert active
        for row in active:
            # noise sigma is 2% of the value, so stay inside a tolerant band
            assert 100.0 * 0.5 * 1.0 <= row["active_power_kw"] <= 100.0 * 0.5 * 1.25 * 1.10

    def test_partial_load_measured_below_running(self):
        """PARTIAL is metered at partial_fraction (~0.65) of the RUNNING level.

        Power-band separation lets calibration recover the PARTIAL share from
        measurements alone; identical levels would collapse both states into
        one estimated band.
        """
        machine = _make_machine(rated_power_kw=100.0, load_factor=0.5)
        rows = plant_sim.generate_series(machine, START, HOURS)
        running = [r["active_power_kw"] for r in rows if r["state"] == "RUNNING"]
        partial = [r["active_power_kw"] for r in rows if r["state"] == "PARTIAL"]
        assert running and partial, "series must contain both states"
        med_run = sorted(running)[len(running) // 2]
        med_par = sorted(partial)[len(partial) // 2]
        assert 0.5 * med_run <= med_par <= 0.8 * med_run, (
            f"PARTIAL median {med_par} not inside 0.5-0.8 of RUNNING median {med_run}"
        )


class TestCatalogAndCsv:
    """generate_catalog and write_csv surface contracts."""

    def test_generate_catalog_subset(self):
        rows = plant_sim.generate_catalog(
            START, 24, machine_codes=["AUX-001", "BOMB-002"]
        )
        codes = {r["machine_code"] for r in rows}
        assert codes == {"AUX-001", "BOMB-002"}
        assert len(rows) == 2 * 24

    def test_generate_catalog_all_machines(self):
        machines = plant_sim.load_machines()
        rows = plant_sim.generate_catalog(START, 3)
        assert {r["machine_code"] for r in rows} == set(machines)

    def test_write_csv_matches_import_contract(self):
        """Output must parse exactly like POST /api/import/real expects."""
        rows = plant_sim.generate_catalog(
            START, 24, machine_codes=["AUX-001", "HVAC-001"]
        )
        scratch = Path(tempfile.mkdtemp(prefix="plant_sim_csv_"))
        try:
            path = scratch / "measurements.csv"
            plant_sim.write_csv(rows, path)
            with path.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                assert reader.fieldnames == CSV_HEADER
                parsed = list(reader)
            assert len(parsed) == len(rows)
            for record in parsed:
                assert MACHINE_CODE_RE.match(record["machine_code"])
                assert TS_RE.match(record["ts"])
                datetime.strptime(record["ts"], "%Y-%m-%d %H:%M:%S")
                value = float(record["active_power_kw"])
                assert value >= 0.0
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


class TestNoiseClamp:
    """Gaussian noise must never push power below zero."""

    def test_all_values_non_negative_across_catalog(self):
        rows = plant_sim.generate_catalog(START, 48)
        assert rows
        worst = min(r["active_power_kw"] for r in rows)
        assert worst >= 0.0

    def test_zero_standby_machine_stays_non_negative(self):
        machine = _make_machine(
            rated_power_kw=0.05, standby_pct=0, load_factor=0.0
        )
        rows = plant_sim.generate_series(machine, START, 48)
        for row in rows:
            assert row["active_power_kw"] >= 0.0
