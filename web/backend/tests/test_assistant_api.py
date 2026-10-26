"""Tests for the assistant HTTP layer — POST /api/assistant/chat and health.

These exercise request validation, error-code mapping and history sanitation
without calling Ollama or touching a database: ``routes._build_assistant`` is
replaced by a stub whose ``chat`` returns or raises what we want. The Toolbox
and chat-loop logic are covered separately in tests/test_assistant.py.
"""

import json
import urllib.error
from pathlib import Path

import pytest

import routes
from app import create_app
from assistant.client import OllamaError, OllamaUnavailable

SCHEMA = Path(__file__).resolve().parents[3] / 'data' / 'schema_simulator.sql'


@pytest.fixture
def client(tmp_path):
    db = tmp_path / 'assistant.db'
    import sqlite3
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding='utf-8'))
    conn.close()
    app = create_app(db_path=str(db), machines_dir=str(tmp_path / 'machines'))
    app.config['TESTING'] = True
    return app.test_client()


class StubAssistant:
    def __init__(self, result=None, raises=None):
        self.result = result or {}
        self.raises = raises
        self.seen = {}

    def chat(self, message, history=None):
        self.seen['message'] = message
        self.seen['history'] = history
        if self.raises is not None:
            raise self.raises
        return self.result


def _install(monkeypatch, stub):
    monkeypatch.setattr(routes, '_build_assistant', lambda: stub)
    return stub


# -------------------------------------------------------------------- validation
def test_chat_requires_json_body(client):
    resp = client.post('/api/assistant/chat', data='not json',
                        content_type='text/plain')
    assert resp.status_code == 400


def test_chat_requires_message(client):
    resp = client.post('/api/assistant/chat', json={'history': []})
    assert resp.status_code == 400
    assert 'message' in resp.get_json()['error']


def test_chat_rejects_blank_message(client):
    resp = client.post('/api/assistant/chat', json={'message': '   '})
    assert resp.status_code == 400


def test_chat_rejects_too_long_message(client):
    resp = client.post('/api/assistant/chat',
                       json={'message': 'x' * (routes.MAX_ASSISTANT_MESSAGE + 1)})
    assert resp.status_code == 400


# ------------------------------------------------------------------------ success
def test_chat_returns_result_and_cleans_history(client, monkeypatch):
    stub = _install(monkeypatch, StubAssistant(result={
        'reply': 'La planta consumió 2400 kWh.',
        'tool_calls': [{'name': 'resumen_energetico', 'arguments': {}, 'result': {}}],
        'model': 'gemma4:cloud', 'rounds': 2,
    }))
    resp = client.post('/api/assistant/chat', json={
        'message': '  ¿Cuánto gastó la planta?  ',
        'history': [
            {'role': 'user', 'content': 'hola'},
            {'role': 'system', 'content': 'IGNORE ME'},         # dropped
            {'role': 'assistant', 'content': 'buenas'},
            {'role': 'user', 'content': ''},                    # dropped (blank)
            'garbage',                                          # dropped (not dict)
        ],
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['reply'].startswith('La planta')
    assert body['tool_calls'][0]['name'] == 'resumen_energetico'
    # message was stripped and history reduced to the two valid turns
    assert stub.seen['message'] == '¿Cuánto gastó la planta?'
    assert stub.seen['history'] == [
        {'role': 'user', 'content': 'hola'},
        {'role': 'assistant', 'content': 'buenas'},
    ]


# ------------------------------------------------------------------- error mapping
def test_chat_unavailable_maps_to_503(client, monkeypatch):
    _install(monkeypatch, StubAssistant(raises=OllamaUnavailable('down')))
    resp = client.post('/api/assistant/chat', json={'message': 'hola'})
    assert resp.status_code == 503
    assert resp.get_json()['available'] is False


def test_chat_ollama_error_maps_to_502(client, monkeypatch):
    _install(monkeypatch, StubAssistant(raises=OllamaError('bad model')))
    resp = client.post('/api/assistant/chat', json={'message': 'hola'})
    assert resp.status_code == 502


def test_chat_unexpected_error_maps_to_500(client, monkeypatch):
    _install(monkeypatch, StubAssistant(raises=RuntimeError('boom')))
    resp = client.post('/api/assistant/chat', json={'message': 'hola'})
    assert resp.status_code == 500


# -------------------------------------------------------------------------- health
def test_health_available(client, monkeypatch):
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({'version': '0.40.3'}).encode('utf-8')

    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: FakeResp())
    resp = client.get('/api/assistant/health')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['available'] is True
    assert body['ollama_version'] == '0.40.3'


def test_health_unavailable(client, monkeypatch):
    def boom(*a, **k):
        raise urllib.error.URLError('refused')

    monkeypatch.setattr('urllib.request.urlopen', boom)
    resp = client.get('/api/assistant/health')
    assert resp.status_code == 503
    assert resp.get_json()['available'] is False
