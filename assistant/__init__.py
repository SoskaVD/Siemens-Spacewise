"""Natural-language energy assistant for SPACEWISE AI.

A thin reasoning layer on top of the existing simulation/twin data: a local
Ollama model (``gemma4:cloud`` by default) answers questions and builds
forecasts, but every number it reports comes from a read-only *tool* that runs
Python against the same SQLite data and catalog the dashboard uses. The model
decides WHICH tool to call and explains the result in Spanish; it never invents
figures. See ``assistant.client`` for the chat loop, ``assistant.tools`` for the
tool catalog, and ``assistant.forecast`` for the pure projection math.
"""

from assistant.client import AssistantClient, OllamaError, OllamaUnavailable
from assistant.tools import Toolbox

__all__ = [
    "AssistantClient",
    "OllamaError",
    "OllamaUnavailable",
    "Toolbox",
]
