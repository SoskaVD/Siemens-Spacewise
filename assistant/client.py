"""Chat client that drives a local Ollama model with the assistant's tools.

Talks to Ollama's REST API (``POST {host}/api/chat``) using only the Python
standard library, so the project gains no new pip dependency and works with the
same ``localhost:11434`` server the user already runs (``ollama signin`` enables
the free cloud model ``gemma4:cloud``). The default model is the only one in
Ollama's free plan; set ``OLLAMA_MODEL`` to switch once credits are added.

The loop implements tool calling: send the conversation + tool schemas, and
while the model answers with ``tool_calls`` run them through the ``Toolbox`` and
feed the results back, until it produces a normal reply or the round cap is hit.
Transport is injectable (``transport=`` / ``_post``) so tests exercise the loop
with a scripted fake and never touch the network.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

from assistant.tools import Toolbox

DEFAULT_HOST = "http://127.0.0.1:11434"
# gemma4:cloud is the only cloud model in Ollama's Free plan (verified against
# the live API) and it supports tool calling; override with OLLAMA_MODEL.
DEFAULT_MODEL = "gemma4:cloud"
DEFAULT_TIMEOUT = 120
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = (
    "Eres el asistente energético de SPACEWISE AI, un gemelo digital de 110 "
    "máquinas industriales. Respondes SIEMPRE en español, de forma clara y "
    "breve.\n"
    "REGLA DE ORO: nunca inventes cifras. Cualquier número (consumo, costo, "
    "MAPE, estado, proyección, ahorro) DEBE provenir de una herramienta. Si "
    "una pregunta requiere datos, llama a la herramienta adecuada y usa su "
    "resultado. Si una herramienta devuelve un campo 'error', explícalo con "
    "naturalidad y sugiere qué falta (p. ej. importar mediciones).\n"
    "Las predicciones y escenarios los calculan las herramientas: tú solo "
    "interpretas y explicas el resultado. No ejecutas ni modificas nada del "
    "sistema; solo consultas. Cuando des cifras, incluye la unidad (kWh, kW) "
    "y, si hay costo, la moneda."
)


class OllamaError(RuntimeError):
    """The model answered, but something in the exchange went wrong."""


class OllamaUnavailable(OllamaError):
    """Ollama could not be reached (not running, not signed in, timeout).

    Surfaced so the web layer can answer 503 and the dashboard can degrade with
    a helpful message instead of a stack trace.
    """


class AssistantClient:
    """Stateful-per-call chat client (history is passed in, not stored)."""

    def __init__(
        self,
        toolbox: Toolbox,
        host: str = DEFAULT_HOST,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
        system_prompt: str = SYSTEM_PROMPT,
        transport: Callable[[dict], dict] | None = None,
    ) -> None:
        self._toolbox = toolbox
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = float(timeout)
        self._max_rounds = int(max_tool_rounds)
        self._system_prompt = system_prompt
        self._transport = transport  # test seam; None -> real HTTP

    @property
    def model(self) -> str:
        return self._model

    def chat(self, message: str, history: list[dict] | None = None) -> dict:
        """Answer one user message, running tools as needed.

        ``history`` is an optional list of prior ``{role, content}`` turns
        (no system/tool bookkeeping — just user/assistant text). Returns
        ``{reply, tool_calls, rounds, model}`` where ``tool_calls`` is the list
        of ``{name, arguments, result}`` actually executed (for the UI to show
        what the answer is grounded on).
        """
        if not message or not str(message).strip():
            raise OllamaError("el mensaje no puede estar vacío")

        messages: list[dict] = [{"role": "system", "content": self._system_prompt}]
        for turn in history or []:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": str(message)})

        tool_schemas = self._toolbox.schemas()
        executed: list[dict] = []

        for round_idx in range(self._max_rounds):
            response = self._post({
                "model": self._model,
                "messages": messages,
                "tools": tool_schemas,
                "stream": False,
            })
            msg = response.get("message") or {}
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                return {
                    "reply": (msg.get("content") or "").strip(),
                    "tool_calls": executed,
                    "rounds": round_idx + 1,
                    "model": self._model,
                }

            # Record the assistant's tool-call turn, then answer every call.
            messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })
            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name") or ""
                arguments = _coerce_arguments(fn.get("arguments"))
                result = self._toolbox.call(name, arguments)
                executed.append({"name": name, "arguments": arguments, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # Ran out of rounds: ask once more without tools for a closing answer.
        final = self._post({
            "model": self._model,
            "messages": messages + [{
                "role": "user",
                "content": "Resume con los datos que ya obtuviste de las herramientas.",
            }],
            "stream": False,
        })
        return {
            "reply": ((final.get("message") or {}).get("content") or "").strip(),
            "tool_calls": executed,
            "rounds": self._max_rounds,
            "model": self._model,
            "truncated": True,
        }

    # ------------------------------------------------------------------ transport
    def _post(self, payload: dict) -> dict:
        if self._transport is not None:
            return self._transport(payload)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._host}/api/chat", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = _read_http_error(exc)
            # Ollama returns the "sign in / add credits" message as an error body.
            raise OllamaError(f"Ollama respondió {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OllamaUnavailable(
                f"no se pudo contactar a Ollama en {self._host}: {exc.reason}. "
                "¿Está Ollama en ejecución y con sesión iniciada (ollama signin)?"
            ) from exc
        except (TimeoutError, OSError) as exc:
            raise OllamaUnavailable(
                f"Ollama no respondió a tiempo ({self._timeout}s): {exc}"
            ) from exc
        if isinstance(body, dict) and body.get("error"):
            raise OllamaError(str(body["error"]))
        return body


def _coerce_arguments(arguments: Any) -> dict:
    """Tool-call arguments come back as a dict, or a JSON string from some models."""
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def _read_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        return str(payload.get("error") or payload)
    except Exception:
        return exc.reason or "error desconocido"
