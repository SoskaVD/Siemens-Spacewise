"""Tests for the feed runner and the closed-loop demo (T5, specs S1/S2/S5).

- build_hour_records: deterministic, ingest-shaped, one row per machine-hour.
- run_loop: streaming semantics through an injected poster (batching,
  counters, interval sleeps, hour stepping).
- run_demo: end-to-end plant -> ingest -> calibrate closes the loop:
  every demo machine's daily-energy MAPE strictly improves and no repo file
  is touched (scratch outside the worktree).
"""

import time
from datetime import datetime
from pathlib import Path

import pytest

from plant import feed_loop
REPO_ROOT = Path(__file__).resolve().parent.parent
START = datetime(2026, 3, 2, 0, 0, 0)

MACHINE = {
    "machine_code": "ZZT-100",
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


class TestBuildHourRecords:
    def test_one_row_per_machine_and_shape(self):
        records = feed_loop.build_hour_records([MACHINE, {**MACHINE, "machine_code": "ZZT-101"}], START)
        assert len(records) == 2
        codes = {r["machine_code"] for r in records}
        assert codes == {"ZZT-100", "ZZT-101"}
        for record in records:
            assert set(record) == {"machine_code", "ts", "active_power_kw"}
            assert record["ts"] == "2026-03-02 00:00:00"
            assert record["active_power_kw"] >= 0

    def test_same_hour_replays_identical_values(self):
        first = feed_loop.build_hour_records([MACHINE], START)
        second = feed_loop.build_hour_records([MACHINE], START)
        assert first == second

    def test_hour_boundaries_step(self):
        records = feed_loop.build_hour_records(
            [MACHINE], START.replace(hour=5)
        )
        assert records[0]["ts"] == "2026-03-02 05:00:00"


class TestRunLoop:
    def test_counts_and_batching_with_fake_poster(self):
        calls = []

        def fake_poster(base_url, records):
            calls.append((base_url, len(records)))
            return {"inserted": len(records), "updated": 0}

        machines = [{**MACHINE, "machine_code": f"ZZT-{100 + k}"} for k in range(3)]
        slept = []
        summary = feed_loop.run_loop(
            "http://x:5000", machines, START, hours=4, interval=0.0,
            sleep=slept.append, poster=fake_poster,
        )
        assert len(calls) == 4  # 3 records/hour < MAX_RECORDS_PER_POST -> one batch/hour
        assert summary == {"batches": 4, "records": 12, "inserted": 12, "updated": 0}
        assert slept == []  # interval 0 -> never sleeps

    def test_hour_timestamps_stream_in_order(self):
        seen = []

        def fake_poster(base_url, records):
            seen.extend(r["ts"] for r in records)
            return {"inserted": len(records), "updated": 0}

        feed_loop.run_loop(
            "http://x", [MACHINE], START, hours=3, interval=0.0,
            sleep=lambda s: None, poster=fake_poster,
        )
        assert seen == [
            "2026-03-02 00:00:00",
            "2026-03-02 01:00:00",
            "2026-03-02 02:00:00",
        ]

    def test_batching_splits_large_hours(self):
        calls = []

        def fake_poster(base_url, records):
            calls.append(len(records))
            return {"inserted": len(records), "updated": 0}

        machines = [{**MACHINE, "machine_code": f"ZZK-{k:03d}"} for k in range(600)]
        feed_loop.run_loop(
            "http://x", machines, START, hours=1, interval=0.0,
            sleep=lambda s: None, poster=fake_poster,
        )
        assert sum(calls) == 600
        assert all(count <= feed_loop.MAX_RECORDS_PER_POST for count in calls)


class TestClosedLoopDemo:
    def test_demo_improves_every_machine_without_touching_repo(self):
        from plant import demo_closed_loop

        before = time.time()
        summary = demo_closed_loop.run_demo(hours=168)
        assert summary["records_posted"] > 0
        assert summary["machines"], "demo needs at least one machine"
        for row in summary["machines"]:
            assert row["mape_before_pct"] is not None
            assert row["mape_after_pct"] is not None
            assert row["mape_after_pct"] < row["mape_before_pct"], (
                f"{row['machine_code']}: calibration did not improve daily MAPE"
            )
        # the demo never writes inside the worktree
        import subprocess
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT,
            capture_output=True, text=True,
        ).stdout
        repo_machines = [line for line in status.splitlines()
                         if 'machines/' in line and '.bak' in line]
        assert repo_machines == []
