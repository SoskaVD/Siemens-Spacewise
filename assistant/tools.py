"""Read-only tool catalog the energy assistant can call.

Each tool fetches data through an injected ``queries`` object (the same module
the Flask app uses, or a fake in tests) and delegates any arithmetic to
``assistant.forecast``. Tools are READ-ONLY by design: calibration and ingest
rewrite files/rows, so they are deliberately NOT exposed to the model — the
assistant can read and reason about the twin, never mutate it.

Every tool returns a JSON-serializable dict and reports problems as
``{"error": "..."}`` instead of raising, so a bad argument becomes something
the model can read and recover from rather than a 500.

``Toolbox`` holds the wiring (queries access, machines dir, price per kWh) and
exposes two things the chat loop needs:

* ``schemas()`` — the Ollama ``tools`` array (JSON-Schema per function).
* ``call(name, arguments)`` — dispatch by name, always returning a dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from assistant import forecast


class Toolbox:
    """Bundle of read-only tools bound to one data source + config."""

    def __init__(
        self,
        queries: Any,
        machines_dir: str | Path,
        price_kwh: float = 0.0,
        currency: str = "USD",
    ) -> None:
        self._q = queries
        self._machines_dir = Path(machines_dir)
        self._price = float(price_kwh or 0.0)
        self._currency = currency
        # name -> (callable, json-schema). Order is the order shown to the model.
        self._tools: dict[str, tuple[Callable[..., dict], dict]] = {}
        self._register_all()

    # ------------------------------------------------------------------ public
    def schemas(self) -> list[dict]:
        """Ollama ``tools`` payload: one function schema per registered tool."""
        return [schema for _, schema in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    def call(self, name: str, arguments: dict | None = None) -> dict:
        """Run a tool by name with keyword ``arguments`` (defensive)."""
        entry = self._tools.get(name)
        if entry is None:
            return {"error": f"unknown tool: {name}"}
        fn, _ = entry
        args = arguments or {}
        if not isinstance(args, dict):
            return {"error": f"arguments for {name} must be an object"}
        try:
            return fn(**args)
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}
        except Exception as exc:  # pragma: no cover - last-resort guard
            return {"error": f"tool {name} failed: {exc}"}

    # ---------------------------------------------------------------- registry
    def _register_all(self) -> None:
        self._add(
            self.listar_simulaciones,
            "listar_simulaciones",
            "Lista las simulaciones disponibles (id, estado, horas procesadas, "
            "fecha). Úsala para saber qué datos existen antes de otras consultas.",
            {},
        )
        self._add(
            self.resumen_energetico,
            "resumen_energetico",
            "Resumen energético (KPIs) de una simulación: energía total kWh, "
            "potencia media y pico, costo y desglose por categoría. Sin "
            "simulation_id usa la simulación más reciente.",
            {"simulation_id": _int_param("ID de la simulación (opcional)")},
        )
        self._add(
            self.top_consumidores,
            "top_consumidores",
            "Las máquinas que más energía consumen en una simulación.",
            {
                "n": _int_param("Cuántas máquinas devolver (por defecto 5)"),
                "simulation_id": _int_param("ID de la simulación (opcional)"),
            },
        )
        self._add(
            self.detalle_maquina,
            "detalle_maquina",
            "Ficha de catálogo de una máquina: potencia nominal, categoría, "
            "horas/día, días/semana, factor de carga, criticidad.",
            {"machine_code": _str_param("Código, ej HVAC-001")},
            required=["machine_code"],
        )
        self._add(
            self.comparar_real_vs_simulado,
            "comparar_real_vs_simulado",
            "Compara el perfil simulado de una máquina contra las mediciones "
            "reales: MAPE %, sesgo medio %, horas comparadas y cobertura %.",
            {
                "machine_code": _str_param("Código, ej HVAC-001"),
                "simulation_id": _int_param("ID de la simulación (opcional)"),
                "import_id": _int_param("ID de la importación de datos (opcional)"),
            },
            required=["machine_code"],
        )
        self._add(
            self.proyectar_consumo,
            "proyectar_consumo",
            "Proyecta energía y costo para los próximos N días. Si se da "
            "machine_code proyecta esa máquina; si no, toda la planta. Si hay "
            "mediciones reales, corrige la proyección con el sesgo medido.",
            {
                "horizon_days": _int_param("Días a proyectar, ej 30"),
                "machine_code": _str_param("Código de máquina (opcional)"),
                "simulation_id": _int_param("ID de la simulación (opcional)"),
                "import_id": _int_param("ID de la importación (opcional)"),
            },
            required=["horizon_days"],
        )
        self._add(
            self.simular_escenario,
            "simular_escenario",
            "Escenario '¿y si…?': recalcula energía y costo de una máquina si "
            "cambia su horario (horas/día, días/semana) o su carga, y reporta "
            "el ahorro frente a la configuración actual.",
            {
                "machine_code": _str_param("Código, ej COMP-001"),
                "new_hours_per_day": _num_param("Nuevas horas por día (opcional)"),
                "new_days_per_week": _num_param("Nuevos días por semana (opcional)"),
                "load_scale": _num_param(
                    "Multiplicador de carga, ej 0.9 = 10% menos (opcional, 1.0)"),
                "horizon_days": _int_param("Días del escenario (por defecto 30)"),
            },
            required=["machine_code"],
        )
        self._add(
            self.detectar_anomalias,
            "detectar_anomalias",
            "Horas en que el consumo real se aleja más del simulado para una "
            "máquina (posible fallo, mal uso o modelo desajustado).",
            {
                "machine_code": _str_param("Código, ej MOT-001"),
                "threshold_pct": _num_param("Umbral de desviación % (por defecto 30)"),
                "simulation_id": _int_param("ID de la simulación (opcional)"),
                "import_id": _int_param("ID de la importación (opcional)"),
            },
            required=["machine_code"],
        )
        self._add(
            self.estado_actual_maquina,
            "estado_actual_maquina",
            "Estado actual estimado de una máquina (OFF/STANDBY/PARTIAL/RUNNING) "
            "según sus últimas mediciones reales, con potencia y confianza.",
            {
                "machine_code": _str_param("Código, ej HVAC-003"),
                "window": _int_param("Horas recientes a clasificar (por defecto 48)"),
                "import_id": _int_param("ID de la importación (opcional)"),
            },
            required=["machine_code"],
        )

    def _add(self, fn, name, description, properties, required=None):
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": list(required or []),
                },
            },
        }
        self._tools[name] = (fn, schema)

    # -------------------------------------------------------------- tool bodies
    def listar_simulaciones(self) -> dict:
        sims = self._q.get_all_simulations() or []
        return {
            "count": len(sims),
            "simulations": [
                {
                    "simulation_id": s.get("simulation_id"),
                    "code": s.get("simulation_code"),
                    "status": s.get("status"),
                    "total_hours": s.get("total_hours"),
                    "created_at": s.get("created_at"),
                }
                for s in sims
            ],
        }

    def resumen_energetico(self, simulation_id: int | None = None) -> dict:
        sim_id = self._resolve_sim(simulation_id)
        if sim_id is None:
            return {"error": "no hay simulaciones disponibles todavía"}
        summary = self._q.get_simulation_summary(sim_id)
        if not summary:
            return {"error": f"no hay resumen para la simulación {sim_id}"}

        total_energy = float(summary.get("total_energy_kwh") or 0.0)
        cost = summary.get("total_cost_usd")
        if cost is None:
            cost = total_energy * self._price
        return {
            "simulation_id": sim_id,
            "status": summary.get("status"),
            "hours_processed": summary.get("hours_processed") or summary.get("total_hours"),
            "total_energy_kwh": round(total_energy, 2),
            "avg_power_kw": round(float(summary.get("avg_power_kw") or 0.0), 2),
            "peak_power_kw": round(float(summary.get("peak_power_kw") or 0.0), 2),
            "peak_ts": summary.get("peak_ts"),
            "estimated_cost": round(float(cost or 0.0), 2),
            "currency": self._currency,
            "price_kwh": self._price,
            "energy_by_category": _load_json(summary.get("energy_by_category_json")),
        }

    def top_consumidores(self, n: int = 5, simulation_id: int | None = None) -> dict:
        sim_id = self._resolve_sim(simulation_id)
        if sim_id is None:
            return {"error": "no hay simulaciones disponibles todavía"}
        summary = self._q.get_simulation_summary(sim_id)
        if not summary:
            return {"error": f"no hay resumen para la simulación {sim_id}"}
        top = _load_json(summary.get("top_machines_json")) or []
        n = max(int(n or 5), 1)
        return {"simulation_id": sim_id, "top": top[:n]}

    def detalle_maquina(self, machine_code: str) -> dict:
        code = _norm_code(machine_code)
        if code is None:
            return {"error": "código de máquina inválido (formato ^[A-Z]{2,10}-\\d{1,5}$)"}
        machine = self._q.get_machine_by_code(code)
        if not machine:
            return {"error": f"máquina {code} no encontrada"}
        return machine

    def comparar_real_vs_simulado(
        self, machine_code: str, simulation_id: int | None = None,
        import_id: int | None = None,
    ) -> dict:
        code = _norm_code(machine_code)
        if code is None:
            return {"error": "código de máquina inválido"}
        sim_id = self._resolve_sim(simulation_id)
        if sim_id is None:
            return {"error": "no hay simulaciones disponibles"}
        imp_id = self._resolve_import(import_id)
        if imp_id is None:
            return {"error": "no hay mediciones reales importadas para comparar"}
        result = self._q.get_comparison(sim_id, code, imp_id)
        # Trim the full aligned series; the model only needs the metrics.
        result.pop("series", None)
        return result

    def proyectar_consumo(
        self, horizon_days: int, machine_code: str | None = None,
        simulation_id: int | None = None, import_id: int | None = None,
    ) -> dict:
        try:
            horizon = int(horizon_days)
        except (TypeError, ValueError):
            return {"error": "horizon_days debe ser un entero"}
        if horizon <= 0:
            return {"error": "horizon_days debe ser positivo"}
        sim_id = self._resolve_sim(simulation_id)
        if sim_id is None:
            return {"error": "no hay simulaciones disponibles"}

        if machine_code:
            return self._project_machine(code_or_error(machine_code), sim_id,
                                         import_id, horizon)
        return self._project_plant(sim_id, horizon)

    def simular_escenario(
        self, machine_code: str, new_hours_per_day: float | None = None,
        new_days_per_week: float | None = None, load_scale: float = 1.0,
        horizon_days: int = 30,
    ) -> dict:
        code = _norm_code(machine_code)
        if code is None:
            return {"error": "código de máquina inválido"}
        machine = self._q.get_machine_by_code(code)
        if not machine:
            return {"error": f"máquina {code} no encontrada"}
        return forecast.scenario_savings(
            machine,
            new_hours_per_day=new_hours_per_day,
            new_days_per_week=new_days_per_week,
            load_scale=1.0 if load_scale is None else float(load_scale),
            horizon_days=int(horizon_days or 30),
            price_kwh=self._price,
        )

    def detectar_anomalias(
        self, machine_code: str, threshold_pct: float = 30.0,
        simulation_id: int | None = None, import_id: int | None = None,
    ) -> dict:
        code = _norm_code(machine_code)
        if code is None:
            return {"error": "código de máquina inválido"}
        sim_id = self._resolve_sim(simulation_id)
        if sim_id is None:
            return {"error": "no hay simulaciones disponibles"}
        imp_id = self._resolve_import(import_id)
        if imp_id is None:
            return {"error": "no hay mediciones reales importadas"}
        comparison = self._q.get_comparison(sim_id, code, imp_id)
        result = forecast.detect_anomalies(
            comparison.get("series") or [], threshold_pct=float(threshold_pct or 30.0))
        result["machine_code"] = code
        result["simulation_id"] = sim_id
        result["import_id"] = imp_id
        return result

    def estado_actual_maquina(
        self, machine_code: str, window: int = 48, import_id: int | None = None,
    ) -> dict:
        code = _norm_code(machine_code)
        if code is None:
            return {"error": "código de máquina inválido"}
        imp_id = self._resolve_import(import_id)
        if imp_id is None:
            return {"machine_code": code, "state": "UNKNOWN",
                    "detail": "no hay mediciones reales importadas"}
        rows = self._q.get_real_measurements(imp_id, machine_code=code)
        if not rows:
            return {"machine_code": code, "state": "UNKNOWN",
                    "detail": "sin mediciones para esta máquina"}
        # Lazy import: these live in the plant package and read the module file.
        from plant import calibration, plant_sim
        path = calibration.module_path(self._machines_dir, code)
        if not path.is_file():
            return {"error": f"módulo de máquina no encontrado para {code}"}
        module = json.loads(path.read_text(encoding="utf-8"))
        window = max(int(window or 48), 1)
        window_rows = rows[-window:]
        classes = calibration.classify_rows(module, window_rows)
        newest = classes[-1]
        confidence = classes.count(newest) / len(classes)
        state_name = next(
            (k for k in (module.get("work_cycles") or {})
             if plant_sim._classify_state(k) == newest),
            None,
        )
        return {
            "machine_code": code,
            "state": state_name or newest.upper(),
            "state_key": newest,
            "power_kw": window_rows[-1].get("active_power_kw"),
            "last_ts": window_rows[-1].get("ts"),
            "confidence": round(confidence, 3),
            "window_hours": len(window_rows),
            "import_id": imp_id,
        }

    # ------------------------------------------------------------- projections
    def _project_machine(self, code, sim_id, import_id, horizon) -> dict:
        if isinstance(code, dict):  # code_or_error returned an error dict
            return code
        rows = self._q.get_machine_measurements(sim_id, code)
        if not rows:
            return {"error": f"la máquina {code} no está en la simulación {sim_id}"}
        sim_daily = forecast.daily_energy_from_hours(
            sum(float(r.get("energy_kwh") or 0.0) for r in rows), len(rows))
        bias = None
        imp_id = self._resolve_import(import_id)
        if imp_id is not None:
            bias = self._q.get_comparison(sim_id, code, imp_id).get("mean_bias_pct")
        out = forecast.project_energy(sim_daily, horizon, self._price, bias)
        out.update({"scope": "machine", "machine_code": code,
                    "simulation_id": sim_id, "currency": self._currency})
        return out

    def _project_plant(self, sim_id, horizon) -> dict:
        summary = self._q.get_simulation_summary(sim_id)
        if not summary:
            return {"error": f"no hay resumen para la simulación {sim_id}"}
        hours = summary.get("hours_processed") or summary.get("total_hours") or 0
        daily = forecast.daily_energy_from_hours(
            float(summary.get("total_energy_kwh") or 0.0), hours)
        out = forecast.project_energy(daily, horizon, self._price, None)
        out.update({"scope": "plant", "simulation_id": sim_id,
                    "currency": self._currency})
        return out

    # ---------------------------------------------------------------- resolvers
    def _resolve_sim(self, simulation_id: int | None) -> int | None:
        if simulation_id is not None:
            try:
                return int(simulation_id)
            except (TypeError, ValueError):
                return None
        sims = self._q.get_all_simulations() or []
        return sims[0].get("simulation_id") if sims else None

    def _resolve_import(self, import_id: int | None) -> int | None:
        if import_id is not None:
            try:
                return int(import_id)
            except (TypeError, ValueError):
                return None
        imports = self._q.list_imports() or []
        return imports[0].get("import_id") if imports else None


# ----------------------------------------------------------------- param specs
def _str_param(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _int_param(desc: str) -> dict:
    return {"type": "integer", "description": desc}


def _num_param(desc: str) -> dict:
    return {"type": "number", "description": desc}


# ---------------------------------------------------------------------- helpers
import re as _re

_CODE_RE = _re.compile(r"^[A-Z]{2,10}-\d{1,5}$")


def _norm_code(code: str) -> str | None:
    if not code or not isinstance(code, str):
        return None
    code = code.strip().upper()
    return code if _CODE_RE.match(code) else None


def code_or_error(code: str):
    """Return a normalized code, or an ``{"error": ...}`` dict for a bad one."""
    norm = _norm_code(code)
    return norm if norm is not None else {"error": "código de máquina inválido"}


def _load_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None
