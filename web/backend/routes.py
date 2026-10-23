"""Flask Blueprint with API routes.

All endpoints validate inputs, use parameterized queries, and return JSON.
No stack traces are exposed to clients.
"""

import csv
import io
import json
import math
import re
from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request

import queries

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Pattern for machine codes: letters-digits (e.g. HVAC-001)
MACHINE_CODE_RE = re.compile(r'^[A-Z]{2,10}-\d{1,5}$')

# Pattern for timestamps: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?$')

# At most this many line-level errors are returned per rejected CSV
MAX_IMPORT_ERRORS = 20


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


def _validate_timestamp(value: str | None, full: bool = False) -> str | None:
    """Return normalized timestamp or None if invalid.

    Args:
        value: Raw timestamp string.
        full: When True the time part is mandatory and the calendar date must
            actually exist (YYYY-MM-DD HH:MM:SS). The regex alone would accept
            impossible dates like 2026-13-45 99:99:99, and imported rows must
            be aligned by exact ts string against the simulation grid.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > 30:
        return None
    if not TIMESTAMP_RE.match(value):
        return None
    if not full:
        return value
    try:
        datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None
    return value


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


# ---------------------------------------------------------------------------
# Real-measurement import and simulated-vs-real comparison (digital shadow).
# ---------------------------------------------------------------------------

_IMPORT_CSV_REQUIRED_COLUMNS = ('machine_code', 'ts', 'active_power_kw')
_IMPORT_CSV_OPTIONAL_COLUMNS = ('energy_kwh', 'current_a', 'power_factor', 'voltage_v')


def _read_csv_payload() -> tuple[str | None, str | None]:
    """Return (csv_text, source_label) from a multipart file or a raw body.

    Accepts the formats the dashboard and field tools produce: a multipart
    upload with a 'file' part, or a text/csv (or plain) request body.
    """
    if request.files:
        file_storage = request.files.get('file') or next(iter(request.files.values()))
        raw = file_storage.read()
        filename = (file_storage.filename or '').strip() or None
        if not raw:
            return None, filename
        return raw.decode('utf-8-sig', errors='replace'), filename

    text = request.get_data(as_text=True)
    if not text or not text.strip():
        return None, None
    return text, None


def _parse_import_float(value, column: str) -> tuple[float | None, str | None]:
    """Parse one CSV numeric cell: finite, non-negative. Returns (value, error)."""
    if value is None:
        return None, f'{column} is required'
    text = str(value).strip()
    if not text:
        return None, f'{column} is required' if column in _IMPORT_CSV_REQUIRED_COLUMNS else (None, None)
    try:
        number = float(text)
    except ValueError:
        return None, f'{column} must be a number'
    if not math.isfinite(number):
        return None, f'{column} must be a finite number'
    if number < 0:
        return None, f'{column} must be zero or greater'
    return number, None


@api_bp.route('/import/real', methods=['POST'])
def import_real():
    """Import real measurements from a CSV (SENTREN-style meter export).

    Format: header `machine_code,ts,active_power_kw` with the optional
    columns `energy_kwh,current_a,power_factor,voltage_v`. Extra columns are
    ignored. Query params `name` and `notes` label the import.

    The whole file is validated before touching the database: either every
    row is stored or none is (201 with {import_id, rows}), and on validation
    failure a 400 is returned with at most 20 line-level errors.
    """
    text, source_file = _read_csv_payload()
    if text is None:
        return jsonify({'error': 'No CSV data provided'}), 400

    name = (request.args.get('name') or '').strip() or (source_file or 'CSV import')
    notes = (request.args.get('notes') or '').strip() or None
    if len(name) > 200 or (notes and len(notes) > 500):
        return jsonify({'error': 'Import name or notes too long'}), 400

    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return jsonify({'error': 'CSV header must include machine_code,ts,active_power_kw'}), 400
    columns = [c.strip().lower() for c in header]
    missing = [c for c in _IMPORT_CSV_REQUIRED_COLUMNS if c not in columns]
    if missing:
        return jsonify({
            'error': 'CSV header must include machine_code,ts,active_power_kw',
            'missing_columns': missing,
        }), 400

    try:
        known_codes = {m['machine_code'] for m in queries.get_all_machines()}
    except Exception:
        return jsonify({'error': 'Failed to load machine catalog'}), 500

    errors: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []
    seen_data_rows = False

    for row in reader:
        line = reader.line_num
        if not any((cell or '').strip() for cell in row):
            continue  # tolerate blank lines
        seen_data_rows = True
        values = dict(zip(columns, row))
        record: dict[str, Any] = {}

        code = _validate_machine_code(values.get('machine_code', ''))
        if code is None:
            errors.append({'line': line, 'error': 'invalid machine code format'})
        elif code not in known_codes:
            errors.append({'line': line, 'error': f"unknown machine code '{code}'"})
        else:
            record['machine_code'] = code

        ts = _validate_timestamp(values.get('ts'), full=True)
        if ts is None:
            errors.append({'line': line, 'error': 'invalid timestamp, expected YYYY-MM-DD HH:MM:SS'})
        else:
            record['ts'] = ts

        for column in _IMPORT_CSV_REQUIRED_COLUMNS[2:] + _IMPORT_CSV_OPTIONAL_COLUMNS:
            cell = values.get(column)
            cell = cell.strip() if isinstance(cell, str) else cell
            if column in _IMPORT_CSV_REQUIRED_COLUMNS:
                number, error = _parse_import_float(cell or None, column)
            elif cell in (None, ''):
                number, error = None, None
            else:
                number, error = _parse_import_float(cell, column)
            if error:
                errors.append({'line': line, 'error': error})
            elif number is not None or column in _IMPORT_CSV_REQUIRED_COLUMNS:
                record[column] = number

        if not any(k in record for k in ('machine_code', 'ts', 'active_power_kw')):
            continue
        # Rows that failed any field check are never stored, even partially.
        if not all(k in record for k in _IMPORT_CSV_REQUIRED_COLUMNS):
            continue
        valid_rows.append(record)

    if not seen_data_rows:
        return jsonify({'error': 'CSV contains no data rows'}), 400
    if errors:
        return jsonify({
            'error': 'CSV validation failed: nothing was imported',
            'error_count': len(errors),
            'errors': errors[:MAX_IMPORT_ERRORS],
        }), 400

    try:
        import_id = queries.insert_import(name, source_file, notes)
        rows_stored = queries.bulk_insert_real_measurements(import_id, valid_rows)
    except Exception:
        return jsonify({'error': 'Failed to store measurements'}), 500

    return jsonify({'import_id': import_id, 'rows': rows_stored}), 201


@api_bp.route('/ingest/hourly', methods=['POST'])
def ingest_hourly():
    """Append hourly measurements to the rolling live import (Camino B).

    Body: {"records": [{"machine_code", "ts", "active_power_kw",
    optional energy_kwh/current_a/power_factor/voltage_v}, ...]}.

    Same strictness as /api/import/real, validated record by record before
    touching the database: any invalid record returns 400 with at most 20
    errors and nothing is written. On success the rows go to the single
    LIVE-STREAM import, where an existing (machine_code, ts) pair is updated
    instead of duplicated, and the answer is
    {import_id, inserted, updated, total} with status 200.
    """
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400

    records = body.get('records')
    if not isinstance(records, list):
        return jsonify({'error': "'records' must be a list"}), 400
    if not records:
        return jsonify({'error': 'records list is empty'}), 400

    try:
        known_codes = {m['machine_code'] for m in queries.get_all_machines()}
    except Exception:
        return jsonify({'error': 'Failed to load machine catalog'}), 500

    errors: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        if not isinstance(raw, dict):
            errors.append({'index': index, 'error': 'record must be a JSON object'})
            continue
        record: dict[str, Any] = {}

        code = _validate_machine_code(raw.get('machine_code', ''))
        if code is None:
            errors.append({'index': index, 'error': 'invalid machine code format'})
        elif code not in known_codes:
            errors.append({'index': index,
                           'error': f"unknown machine code '{code}'"})
        else:
            record['machine_code'] = code

        ts = _validate_timestamp(raw.get('ts'), full=True)
        if ts is None:
            errors.append({'index': index,
                           'error': 'invalid timestamp, expected YYYY-MM-DD HH:MM:SS'})
        else:
            record['ts'] = ts

        for column in _IMPORT_CSV_REQUIRED_COLUMNS[2:] + _IMPORT_CSV_OPTIONAL_COLUMNS:
            value = raw.get(column)
            if column in _IMPORT_CSV_REQUIRED_COLUMNS:
                number, error = _parse_import_float(value, column)
            elif value is None or (isinstance(value, str) and not value.strip()):
                number, error = None, None
            else:
                number, error = _parse_import_float(value, column)
            if error:
                errors.append({'index': index, 'error': error})
            elif number is not None or column in _IMPORT_CSV_REQUIRED_COLUMNS:
                record[column] = number

        # Records that failed any field check are never stored, even partially.
        if not all(k in record for k in _IMPORT_CSV_REQUIRED_COLUMNS):
            continue
        valid_rows.append(record)

    if errors:
        return jsonify({
            'error': 'Ingest validation failed: nothing was stored',
            'error_count': len(errors),
            'errors': errors[:MAX_IMPORT_ERRORS],
        }), 400

    try:
        import_id = queries.get_or_create_live_import()
        result = queries.upsert_real_measurements(import_id, valid_rows)
    except Exception:
        return jsonify({'error': 'Failed to store measurements'}), 500

    return jsonify({
        'import_id': import_id,
        'inserted': result['inserted'],
        'updated': result['updated'],
        'total': result['total'],
    })


@api_bp.route('/imports', methods=['GET'])
def list_imports():
    """List real-data imports, newest first."""
    try:
        imports = queries.list_imports()
        return jsonify({'imports': imports, 'count': len(imports)})
    except Exception:
        return jsonify({'error': 'Failed to retrieve imports'}), 500


@api_bp.route('/imports/<int:import_id>', methods=['GET'])
def get_import_detail(import_id: int):
    """Get one import with per-machine row counts."""
    if import_id <= 0:
        return jsonify({'error': 'Import ID must be positive'}), 400
    try:
        detail = queries.get_import_detail(import_id)
        if detail is None:
            return jsonify({'error': f'Import {import_id} not found'}), 404
        return jsonify(detail)
    except Exception:
        return jsonify({'error': 'Failed to retrieve import'}), 500


@api_bp.route('/imports/<int:import_id>', methods=['DELETE'])
def delete_import(import_id: int):
    """Delete an import and cascade the removal to its measurements."""
    if import_id <= 0:
        return jsonify({'error': 'Import ID must be positive'}), 400
    try:
        result = queries.delete_import(import_id)
        if result is None:
            return jsonify({'error': f'Import {import_id} not found'}), 404
        return jsonify(result)
    except Exception:
        return jsonify({'error': 'Failed to delete import'}), 500


@api_bp.route('/simulations/<int:sim_id>/compare', methods=['GET'])
def compare_simulation(sim_id: int):
    """Compare the simulated hourly profile of one machine against real data.

    Query params:
        machine: machine code (required), e.g. 'HVAC-001'
        import_id: import to compare against; defaults to the latest import
    """
    if sim_id <= 0:
        return jsonify({'error': 'Simulation ID must be positive'}), 400

    machine = _validate_machine_code(request.args.get('machine'))
    if machine is None:
        return jsonify({'error': 'machine query parameter must be a valid machine code'}), 400

    raw_import = request.args.get('import_id')
    import_id = None
    if raw_import:
        import_id, error = _validate_positive_int(raw_import, 'import_id')
        if error:
            return jsonify({'error': error}), 400

    try:
        if not queries.validate_simulation_id(sim_id):
            return jsonify({'error': f'Simulation {sim_id} not found'}), 404
        if not queries.validate_machine_code(machine):
            return jsonify({'error': f'Machine {machine} not found'}), 404

        if import_id is None:
            imports = queries.list_imports()
            if not imports:
                return jsonify({'error': 'No real data imports available to compare'}), 404
            import_id = max(i['import_id'] for i in imports)
        elif queries.get_import_detail(import_id) is None:
            return jsonify({'error': f'Import {import_id} not found'}), 404

        return jsonify(queries.get_comparison(sim_id, machine, import_id))
    except Exception:
        return jsonify({'error': 'Failed to compare simulation with real data'}), 500
