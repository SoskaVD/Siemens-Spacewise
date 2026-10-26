"""Unit tests for the energy assistant core (forecast + tools + chat loop).

No network and no database: forecast math is pure, the Toolbox runs against a
fake queries object, and the chat client is driven by a scripted transport that
replays what Ollama would return. This keeps the suite fast and free (no cloud
usage) while still exercising the full tool-calling loop.
"""

import json

import pytest

from assistant import forecast
from assistant.client import AssistantClient, OllamaError, OllamaUnavailable
from assistant.tools import Toolbox


# --------------------------------------------------------------------- forecast
def test_daily_energy_from_hours_scales_to_a_day():
    # 240 kWh over 48 h -> 5 kWh/h -> 120 kWh/day
    assert forecast.daily_energy_from_hours(240.0, 48) == pytest.approx(120.0)


def test_daily_energy_from_hours_zero_hours_is_safe():
    assert forecast.daily_energy_from_hours(100.0, 0) == 0.0


def test_bias_correction_reduces_an_overestimating_model():
    # Simulation reads 25% high -> real estimate = 100 / 1.25 = 80
    assert forecast.apply_bias_correction(100.0, 25.0) == pytest.approx(80.0)


def test_bias_correction_none_is_identity():
    assert forecast.apply_bias_correction(100.0, None) == 100.0


def test_bias_correction_floors_pathological_divisor():
    # bias of -200% would give a negative/zero divisor; it must stay finite.
    assert forecast.apply_bias_correction(100.0, -200.0) > 0


def test_project_energy_applies_bias_and_cost():
    out = forecast.project_energy(100.0, 30, price_kwh=0.2, mean_bias_pct=25.0)
    assert out["bias_corrected"] is True
    assert out["daily_energy_kwh"] == pytest.approx(80.0)
    assert out["projected_energy_kwh"] == pytest.approx(2400.0)
    assert out["projected_cost"] == pytest.approx(480.0)


def test_scenario_savings_fewer_hours_saves_energy():
    machine = {"machine_code": "COMP-001", "rated_power_kw": 10.0,
               "load_factor": 0.5, "hours_per_day": 16, "days_per_week": 5}
    out = forecast.scenario_savings(machine, new_hours_per_day=8, horizon_days=7,
                                    price_kwh=0.1)
    # baseline 10*0.5*16*5 = 400 kWh/wk; scenario 10*0.5*8*5 = 200 kWh/wk
    assert out["baseline"]["energy_kwh"] == pytest.approx(400.0)
    assert out["scenario"]["energy_kwh"] == pytest.approx(200.0)
    assert out["saved_energy_kwh"] == pytest.approx(200.0)
    assert out["saved_pct"] == pytest.approx(50.0)
    assert out["saved_cost"] == pytest.approx(20.0)


def test_scenario_savings_more_intensive_is_negative():
    machine = {"machine_code": "MOT-001", "rated_power_kw": 5.0,
               "load_factor": 0.4, "hours_per_day": 8, "days_per_week": 5}
    out = forecast.scenario_savings(machine, new_days_per_week=7, horizon_days=7)
    assert out["saved_energy_kwh"] < 0


def test_detect_anomalies_flags_and_ranks():
    series = [
        {"ts": "2026-01-01 00:00:00", "simulated_kw": 10.0, "real_kw": 10.0},   # 0%
        {"ts": "2026-01-01 01:00:00", "simulated_kw": 20.0, "real_kw": 10.0},   # +100%
        {"ts": "2026-01-01 02:00:00", "simulated_kw": 5.0, "real_kw": 10.0},    # -50%
        {"ts": "2026-01-01 03:00:00", "simulated_kw": 9.0, "real_kw": 0.0},     # skipped
    ]
    out = forecast.detect_anomalies(series, threshold_pct=30.0)
    assert out["hours_checked"] == 4
    assert out["anomalies_found"] == 2
    assert out["anomalies"][0]["deviation_pct"] == pytest.approx(100.0)  # worst first


# ------------------------------------------------------------------- fake data
class FakeQueries:
    """Minimal stand-in for web.backend.queries used by the Toolbox."""

    def __init__(self):
        self.sims = [{"simulation_id": 7, "simulation_code": "S07",
                      "status": "RUNNING", "total_hours": 8760,
                      "created_at": "2026-10-20"}]
        self.summary = {
            "status": "RUNNING", "total_energy_kwh": 2400.0, "avg_power_kw": 100.0,
            "peak_power_kw": 180.0, "peak_ts": "2026-01-15 14:00:00",
            "total_cost_usd": None, "hours_processed": 48,
            "energy_by_category_json": json.dumps({"hvac": 1000.0, "pumps": 400.0}),
            "top_machines_json": json.dumps([
                {"code": "HVAC-001", "energy": 500.0},
                {"code": "COMP-001", "energy": 300.0},
                {"code": "MOT-001", "energy": 200.0},
            ]),
        }
        self.machine = {"machine_code": "HVAC-001", "name": "Chiller",
                        "category": "HVAC", "rated_power_kw": 20.0,
                        "load_factor": 0.6, "hours_per_day": 12, "days_per_week": 6}
        self.imports = [{"import_id": 3, "name": "Octubre"}]

    def get_all_simulations(self, **kw):
        return self.sims

    def get_simulation_summary(self, sim_id, **kw):
        return dict(self.summary) if sim_id == 7 else None

    def get_machine_by_code(self, code, **kw):
        return dict(self.machine) if code == "HVAC-001" else None

    def list_imports(self, **kw):
        return self.imports

    def get_comparison(self, sim_id, code, imp_id, **kw):
        return {"simulation_id": sim_id, "machine_code": code, "import_id": imp_id,
                "mape_pct": 12.5, "mean_bias_pct": 25.0, "hours_compared": 40,
                "coverage_pct": 83.0,
                "series": [{"ts": "2026-01-01 00:00:00", "simulated_kw": 20.0,
                            "real_kw": 10.0}]}

    def get_machine_measurements(self, sim_id, code, **kw):
        return [{"energy_kwh": 5.0} for _ in range(48)] if code == "HVAC-001" else []

    def get_real_measurements(self, imp_id, machine_code=None, **kw):
        return []


@pytest.fixture
def toolbox():
    return Toolbox(FakeQueries(), machines_dir="machines", price_kwh=0.2)


# ---------------------------------------------------------------------- toolbox
def test_schemas_are_well_formed(toolbox):
    schemas = toolbox.schemas()
    assert len(schemas) == len(toolbox.names())
    for s in schemas:
        assert s["type"] == "function"
        assert s["function"]["name"]
        assert s["function"]["parameters"]["type"] == "object"


def test_resumen_uses_latest_sim_and_computes_cost(toolbox):
    out = toolbox.call("resumen_energetico", {})
    assert out["simulation_id"] == 7
    assert out["total_energy_kwh"] == pytest.approx(2400.0)
    assert out["estimated_cost"] == pytest.approx(480.0)  # 2400 * 0.2
    assert out["energy_by_category"]["hvac"] == 1000.0


def test_top_consumidores_limits(toolbox):
    out = toolbox.call("top_consumidores", {"n": 2})
    assert len(out["top"]) == 2
    assert out["top"][0]["code"] == "HVAC-001"


def test_detalle_maquina_normalizes_code(toolbox):
    out = toolbox.call("detalle_maquina", {"machine_code": " hvac-001 "})
    assert out["machine_code"] == "HVAC-001"


def test_detalle_maquina_bad_code(toolbox):
    assert "error" in toolbox.call("detalle_maquina", {"machine_code": "nope"})


def test_comparar_drops_series_keeps_metrics(toolbox):
    out = toolbox.call("comparar_real_vs_simulado", {"machine_code": "HVAC-001"})
    assert "series" not in out
    assert out["mape_pct"] == 12.5


def test_proyectar_machine_is_bias_corrected(toolbox):
    # 48 rows * 5 kWh = 240 kWh over 48h -> 120 kWh/day, bias 25% -> 96 kWh/day
    out = toolbox.call("proyectar_consumo", {"machine_code": "HVAC-001",
                                             "horizon_days": 10})
    assert out["scope"] == "machine"
    assert out["bias_corrected"] is True
    assert out["daily_energy_kwh"] == pytest.approx(96.0)
    assert out["projected_energy_kwh"] == pytest.approx(960.0)


def test_proyectar_plant_scope(toolbox):
    out = toolbox.call("proyectar_consumo", {"horizon_days": 30})
    assert out["scope"] == "plant"
    # 2400 kWh / 48 h * 24 = 1200 kWh/day * 30
    assert out["projected_energy_kwh"] == pytest.approx(36000.0)


def test_proyectar_rejects_bad_horizon(toolbox):
    assert "error" in toolbox.call("proyectar_consumo", {"horizon_days": 0})


def test_simular_escenario_savings(toolbox):
    out = toolbox.call("simular_escenario", {"machine_code": "HVAC-001",
                                             "new_hours_per_day": 6, "horizon_days": 7})
    assert out["saved_energy_kwh"] > 0
    assert out["saved_cost"] > 0


def test_detectar_anomalias(toolbox):
    out = toolbox.call("detectar_anomalias", {"machine_code": "HVAC-001",
                                              "threshold_pct": 30})
    assert out["anomalies_found"] == 1
    assert out["machine_code"] == "HVAC-001"


def test_estado_unknown_without_measurements(toolbox):
    out = toolbox.call("estado_actual_maquina", {"machine_code": "HVAC-001"})
    assert out["state"] == "UNKNOWN"


def test_unknown_tool_is_reported(toolbox):
    assert "error" in toolbox.call("no_existe", {})


# ----------------------------------------------------------------------- client
def _scripted_transport(script):
    """Return a transport callable that yields each queued response in turn."""
    calls = {"payloads": []}
    queue = list(script)

    def transport(payload):
        calls["payloads"].append(payload)
        return queue.pop(0)

    transport.calls = calls
    return transport


def test_chat_runs_a_tool_then_answers(toolbox):
    script = [
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "resumen_energetico", "arguments": {}}}]}},
        {"message": {"content": "La planta consumió 2400 kWh (480 USD)."}},
    ]
    transport = _scripted_transport(script)
    client = AssistantClient(toolbox, transport=transport)
    out = client.chat("¿Cuánto gastó la planta?")
    assert "2400" in out["reply"]
    assert out["tool_calls"][0]["name"] == "resumen_energetico"
    assert out["tool_calls"][0]["result"]["total_energy_kwh"] == 2400.0
    assert out["rounds"] == 2
    # second request must carry the tool result back to the model
    assert any(m.get("role") == "tool"
               for m in transport.calls["payloads"][1]["messages"])


def test_chat_handles_arguments_as_json_string(toolbox):
    script = [
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "top_consumidores",
                          "arguments": '{"n": 1}'}}]}},
        {"message": {"content": "El mayor consumidor es HVAC-001."}},
    ]
    client = AssistantClient(toolbox, transport=_scripted_transport(script))
    out = client.chat("¿Quién consume más?")
    assert out["tool_calls"][0]["arguments"] == {"n": 1}
    assert len(out["tool_calls"][0]["result"]["top"]) == 1


def test_chat_without_tools_answers_directly(toolbox):
    script = [{"message": {"content": "Hola, soy el asistente energético."}}]
    client = AssistantClient(toolbox, transport=_scripted_transport(script))
    out = client.chat("hola")
    assert out["tool_calls"] == []
    assert out["rounds"] == 1


def test_chat_empty_message_raises(toolbox):
    client = AssistantClient(toolbox, transport=_scripted_transport([]))
    with pytest.raises(OllamaError):
        client.chat("   ")


def test_chat_propagates_unavailable(toolbox):
    def boom(payload):
        raise OllamaUnavailable("down")

    client = AssistantClient(toolbox, transport=boom)
    with pytest.raises(OllamaUnavailable):
        client.chat("hola")


def test_chat_stops_at_round_cap(toolbox):
    # Model keeps asking for tools forever; loop must stop and summarize.
    loop_resp = {"message": {"content": "", "tool_calls": [
        {"function": {"name": "resumen_energetico", "arguments": {}}}]}}
    script = [loop_resp] * 3 + [{"message": {"content": "Resumen final."}}]
    client = AssistantClient(toolbox, transport=_scripted_transport(script),
                             max_tool_rounds=3)
    out = client.chat("bucle")
    assert out.get("truncated") is True
    assert out["reply"] == "Resumen final."
