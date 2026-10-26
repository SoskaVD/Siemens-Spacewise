/**
 * Energy assistant panel wiring.
 *
 * Self-contained (its own IIFE, no globals beyond reading window.API) so it
 * does not interfere with the dashboard's inline bootstrap script. Sends the
 * user's question to POST /api/assistant/chat, renders the reply and the list
 * of read-only tools the model used to ground it, and keeps a short rolling
 * history for follow-up questions. Degrades gracefully when Ollama is offline.
 */
(function () {
    'use strict';

    const chatEl = document.getElementById('assistant-chat');
    const formEl = document.getElementById('assistant-form');
    const inputEl = document.getElementById('assistant-input');
    const sendEl = document.getElementById('assistant-send');
    const healthEl = document.getElementById('assistant-health');
    const suggestionsEl = document.getElementById('assistant-suggestions');

    if (!chatEl || !formEl || !inputEl) {
        return; // panel not present (defensive)
    }

    // Rolling conversation history (user/assistant text only), capped so the
    // request stays small and cheap.
    const history = [];
    const MAX_HISTORY = 12;
    let busy = false;

    // Human-readable labels for the tool names the backend reports.
    const TOOL_LABELS = {
        listar_simulaciones: 'Listar simulaciones',
        resumen_energetico: 'Resumen energético',
        top_consumidores: 'Top consumidores',
        detalle_maquina: 'Ficha de máquina',
        comparar_real_vs_simulado: 'Comparar real vs simulado',
        proyectar_consumo: 'Proyección de consumo',
        simular_escenario: 'Escenario "¿y si…?"',
        detectar_anomalias: 'Detección de anomalías',
        estado_actual_maquina: 'Estado actual',
    };

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    function addMessage(role, text) {
        const wrap = document.createElement('div');
        wrap.className = `assistant-msg assistant-msg-${role}`;
        const body = document.createElement('div');
        body.className = 'assistant-bubble';
        body.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
        wrap.appendChild(body);
        chatEl.appendChild(wrap);
        chatEl.scrollTop = chatEl.scrollHeight;
        return wrap;
    }

    function addToolChips(wrap, toolCalls) {
        if (!toolCalls || !toolCalls.length) return;
        const row = document.createElement('div');
        row.className = 'assistant-tools';
        row.appendChild(document.createTextNode('Basado en: '));
        toolCalls.forEach(function (call) {
            const chip = document.createElement('span');
            chip.className = 'assistant-tool-chip';
            chip.textContent = TOOL_LABELS[call.name] || call.name;
            row.appendChild(chip);
        });
        wrap.appendChild(row);
    }

    function setBusy(state) {
        busy = state;
        inputEl.disabled = state;
        sendEl.disabled = state;
        sendEl.textContent = state ? 'Pensando…' : 'Preguntar';
    }

    async function refreshHealth() {
        if (!healthEl || !window.API) return;
        const health = await window.API.assistantHealth();
        if (health.available) {
            healthEl.textContent = `IA lista (${health.model || 'modelo'})`;
            healthEl.className = 'assistant-health ok';
        } else {
            healthEl.textContent = 'IA no disponible — inicia Ollama (ollama signin)';
            healthEl.className = 'assistant-health down';
        }
    }

    async function ask(question) {
        if (busy || !question.trim() || !window.API) return;
        addMessage('user', question);
        history.push({ role: 'user', content: question });
        setBusy(true);
        const pending = addMessage('assistant', '…');

        try {
            const res = await window.API.askAssistant(question, history.slice(0, -1));
            pending.querySelector('.assistant-bubble').innerHTML =
                escapeHtml(res.reply || '(sin respuesta)').replace(/\n/g, '<br>');
            addToolChips(pending, res.tool_calls);
            history.push({ role: 'assistant', content: res.reply || '' });
            while (history.length > MAX_HISTORY) history.shift();
        } catch (error) {
            pending.classList.add('assistant-msg-error');
            pending.querySelector('.assistant-bubble').textContent =
                error.message || 'No se pudo obtener respuesta del asistente.';
        } finally {
            setBusy(false);
            inputEl.focus();
        }
    }

    formEl.addEventListener('submit', function (event) {
        event.preventDefault();
        const question = inputEl.value.trim();
        if (!question) return;
        inputEl.value = '';
        ask(question);
    });

    if (suggestionsEl) {
        suggestionsEl.addEventListener('click', function (event) {
            const btn = event.target.closest('button[data-q]');
            if (btn && !busy) ask(btn.getAttribute('data-q'));
        });
    }

    refreshHealth();
})();
