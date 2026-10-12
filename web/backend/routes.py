"""Flask Blueprint with API routes.

All endpoints validate inputs, use parameterized queries, and return JSON.
No stack traces are exposed to clients.
"""

import csv
import io
import json
import re
from flask import Blueprint, jsonify, request

import queries

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Pattern for machine codes: letters-digits (e.g. HVAC-001)
MACHINE_CODE_RE = re.compile(r'^[A-Z]{2,10}-\d{1,5}$')

# Pattern for timestamps: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?$')


def _validate_machine_code(code: str) -> str | None:
    """Return normalized machine code or None if invalid."""
    if not code or not isinstance(code, str):
        return None
    code = code.strip().upper()
    if len(code) > 20:
        return None
    return code if MACHINE_CODE_RE.match(code) else None


def _validate_positive_int(value, name: str) -> tuple[int | None, str | None]:
    """Return (int_value, None) on success or (None, error_message) on failure."""
    try:
        v = int(value)
        if v <= 0:
            return None, f"{name} must be positive"
        return v, None
    except (TypeError, ValueError):
        return None, f"{name} must be an integer"


def _validate_timestamp(value: str | None) -> str | None:
    """Return normalized timestamp or None if invalid."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > 30:
        return None
    return value if TIMESTAMP_RE.match(value) else None


@api_bp.route('/machines', methods=['GET'])
def list_machines():
    """List all active machines with basic info."""
    try:
        machines = queries.get_all_machines()
        return jsonify({'machines': machines, 'count': len(machines)})
    except Exception:
        return jsonify({'error': 'Failed to retrieve machines'}), 500


@api_bp.route('/machines/<code>', methods=['GET'])
def get_machine(code: str):
    """Get detailed info for a specific machine."""
    normalized = _validate_machine_code(code)
    if normalized is None:
        return jsonify({'error': 'Invalid machine code format'}), 400

    try:
        machine = queries.get_machine_by_code(normalized)
        if machine is None:
            return jsonify({'error': f'Machine {normalized} not found'}), 404
        return jsonify(machine)
    except Exception:
        return jsonify({'error': 'Failed to retrieve machine'}), 500


@api_bp.route('/simulations', methods=['GET'])
def list_simulations():
    """List all simulations."""
    try:
        simulations = queries.get_all_simulations()
        return jsonify({'simulations': simulations, 'count': len(simulations)})
    except Exception:
        return jsonify({'error': 'Failed to retrieve simulations'}), 500


@api_bp.route('/simulations/<int:sim_id>/summary', methods=['GET'])
def get_simulation_summary(sim_id: int):
    """Get KPI summary for a simulation."""
    if sim_id <= 0:
        return jsonify({'error': 'Simulation ID must be positive'}), 400

    try:
        if not queries.validate_simulation_id(sim_id):
            return jsonify({'error': f'Simulation {sim_id} not found'}), 404

        summary = queries.get_simulation_summary(sim_id)
        if summary is None:
            return jsonify({'error': f'Summary not available for simulation {sim_id}'}), 404
        return jsonify(summary)
    except Exception:
        return jsonify({'error': 'Failed to retrieve simulation summary'}), 500


@api_bp.route('/simulations/<int:sim_id>/hourly', methods=['GET'])
def get_hourly_totals(sim_id: int):
    """Get hourly totals for a simulation (8760 data points)."""
    if sim_id <= 0:
        return jsonify({'error': 'Simulation ID must be positive'}), 400

    try:
        if not queries.validate_simulation_id(sim_id):
            return jsonify({'error': f'Simulation {sim_id} not found'}), 404

        data = queries.get_hourly_totals(sim_id)
        return jsonify({'simulation_id': sim_id, 'points': len(data), 'data': data})
    except Exception:
        return jsonify({'error': 'Failed to retrieve hourly data'}), 500


@api_bp.route('/simulations/<int:sim_id>/machines/<code>', methods=['GET'])
def get_machine_data(sim_id: int, code: str):
    """Get measurements for a specific machine in a simulation."""
    if sim_id <= 0:
        return jsonify({'error': 'Simulation ID must be positive'}), 400

    normalized = _validate_machine_code(code)
    if normalized is None:
        return jsonify({'error': 'Invalid machine code format'}), 400

    try:
        if not queries.validate_simulation_id(sim_id):
            return jsonify({'error': f'Simulation {sim_id} not found'}), 404
        if not queries.validate_machine_code(normalized):
            return jsonify({'error': f'Machine {normalized} not found'}), 404

        data = queries.get_machine_measurements(sim_id, normalized)
        return jsonify({
            'simulation_id': sim_id,
            'machine_code': normalized,
            'points': len(data),
            'data': data
        })
    except Exception:
        return jsonify({'error': 'Failed to retrieve machine data'}), 500


@api_bp.route('/simulations/<int:sim_id>/export', methods=['GET'])
def export_data(sim_id: int):
    """Export simulation data as CSV or JSON with optional date filtering.
    
    Query params:
        format: 'csv' (default) or 'json'
        start: start timestamp (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        end: end timestamp (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
    """
    if sim_id <= 0:
        return jsonify({'error': 'Simulation ID must be positive'}), 400

    export_format = request.args.get('format', 'csv').lower()
    if export_format not in ('csv', 'json'):
        return jsonify({'error': "Format must be 'csv' or 'json'"}), 400

    start_ts = _validate_timestamp(request.args.get('start'))
    end_ts = _validate_timestamp(request.args.get('end'))
    # Allow None (not provided) but reject invalid provided values
    raw_start = request.args.get('start')
    raw_end = request.args.get('end')
    if raw_start and start_ts is None:
        return jsonify({'error': 'Invalid start timestamp format'}), 400
    if raw_end and end_ts is None:
        return jsonify({'error': 'Invalid end timestamp format'}), 400

    try:
        if not queries.validate_simulation_id(sim_id):
            return jsonify({'error': f'Simulation {sim_id} not found'}), 404

        data = queries.get_export_data(sim_id, start_ts, end_ts)

        if export_format == 'json':
            return jsonify({
                'simulation_id': sim_id,
                'start': start_ts,
                'end': end_ts,
                'points': len(data),
                'data': data
            })

        # CSV output
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        else:
            output.write('')

        csv_content = output.getvalue()
        output.close()

        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=simulation_{sim_id}_export.csv'
            }
        )
    except Exception:
        return jsonify({'error': 'Failed to export data'}), 500
