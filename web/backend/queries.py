"""Database query functions with parameterized SQL statements.

All queries use parameterized statements to prevent SQL injection.
Connection management uses context managers for proper resource cleanup.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a read-only database connection.

    Read-only on purpose: sqlite3.connect() on a missing path silently creates
    an empty file, and the MATLAB side skips the schema creation when the file
    already exists, so it would then fail against a database without tables.
    The backend only reads, so it must never create or modify the file.

    Args:
        db_path: Path to SQLite database file. If None, uses default path.

    Returns:
        sqlite3.Connection with row_factory configured

    Raises:
        sqlite3.OperationalError: if the database file does not exist yet.
    """
    if db_path is None:
        # Default path relative to this file
        db_path = Path(__file__).parent.parent.parent / 'data' / 'spacewise.db'

    uri = Path(db_path).resolve().as_uri() + '?mode=ro'
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_machines(db_path: str = None) -> list[dict[str, Any]]:
    """Get all machines with basic info.

    Returns:
        List of machines with id, code, name, category, rated_power_kw
    """
    try:
        conn = get_db_connection(db_path)
    except sqlite3.OperationalError:
        return []  # database not created yet (simulator still starting)
    try:
        cursor = conn.execute("""
            SELECT 
                machine_id,
                machine_code,
                name,
                category,
                rated_power_kw,
                criticality,
                hours_per_day,
                load_factor
            FROM machines
            WHERE active = 1
            ORDER BY category, machine_code
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []  # tables not created yet
    finally:
        conn.close()


def get_machine_by_code(machine_code: str, db_path: str = None) -> dict[str, Any] | None:
    """Get detailed machine info by code.
    
    Args:
        machine_code: Machine code (e.g., 'HVAC-001')
        
    Returns:
        Machine details or None if not found
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT *
            FROM machines
            WHERE machine_code = ? AND active = 1
        """, (machine_code,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_simulations(db_path: str = None) -> list[dict[str, Any]]:
    """Get all simulations with basic info.
    
    Returns:
        List of simulations ordered by creation date (newest first)
    """
    try:
        conn = get_db_connection(db_path)
    except sqlite3.OperationalError:
        return []  # database not created yet (simulator still starting)
    try:
        cursor = conn.execute("""
            SELECT
                simulation_id,
                simulation_code,
                name,
                description,
                status,
                total_machines,
                total_hours,
                created_at
            FROM simulations
            ORDER BY created_at DESC, simulation_id DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []  # tables not created yet
    finally:
        conn.close()


def get_simulation_summary(simulation_id: int, db_path: str = None) -> dict[str, Any] | None:
    """Get simulation summary with KPIs.
    
    Args:
        simulation_id: Simulation ID
        
    Returns:
        Summary with total energy, peak power, avg power, etc. or None if not found
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT 
                sr.*,
                s.simulation_code,
                s.name,
                s.description,
                s.status,
                s.total_machines,
                s.total_hours
            FROM simulation_results sr
            JOIN simulations s ON sr.simulation_id = s.simulation_id
            WHERE sr.simulation_id = ?
        """, (simulation_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return _summary_from_hourly(conn, simulation_id)
    finally:
        conn.close()


_CATEGORY_COLUMNS = {
    'hvac': 'hvac_power_kw',
    'compressors': 'compressors_power_kw',
    'motors': 'motors_power_kw',
    'pumps': 'pumps_power_kw',
    'lighting': 'lighting_power_kw',
    'lab': 'lab_power_kw',
    'manufacturing': 'manufacturing_power_kw',
    'it': 'it_power_kw',
    'auxiliary': 'auxiliary_power_kw',
}


def _summary_from_hourly(conn: sqlite3.Connection, simulation_id: int) -> dict[str, Any] | None:
    """Build a partial summary from hourly_totals.

    The continuous simulation only appends hourly rows and never writes
    simulation_results, so the dashboard would get a 404 while it runs. This
    computes the same KPIs on the fly from the hours generated so far.
    """
    sim = conn.execute("""
        SELECT simulation_id, simulation_code, name, description, status,
               total_machines, total_hours
        FROM simulations WHERE simulation_id = ?
    """, (simulation_id,)).fetchone()
    if sim is None:
        return None

    category_sql = ', '.join(
        f'COALESCE(SUM({col}), 0) AS {key}' for key, col in _CATEGORY_COLUMNS.items())
    agg = conn.execute(f"""
        SELECT COUNT(*) AS hours,
               COALESCE(SUM(total_energy_kwh), 0) AS total_energy_kwh,
               COALESCE(AVG(total_power_kw), 0) AS avg_power_kw,
               COALESCE(MAX(total_power_kw), 0) AS peak_power_kw,
               {category_sql}
        FROM hourly_totals WHERE simulation_id = ?
    """, (simulation_id,)).fetchone()

    peak = conn.execute("""
        SELECT ts FROM hourly_totals WHERE simulation_id = ?
        ORDER BY total_power_kw DESC LIMIT 1
    """, (simulation_id,)).fetchone()

    try:
        top = conn.execute("""
            SELECT m.machine_code AS code, m.name AS name, m.category AS category,
                   SUM(mm.energy_kwh) AS energy
            FROM machine_measurements mm
            JOIN machines m ON mm.machine_id = m.machine_id
            WHERE mm.simulation_id = ?
            GROUP BY mm.machine_id
            ORDER BY energy DESC
            LIMIT 10
        """, (simulation_id,)).fetchall()
    except sqlite3.OperationalError:
        top = []

    summary = dict(sim)
    summary.update({
        'total_energy_kwh': agg['total_energy_kwh'],
        'avg_power_kw': agg['avg_power_kw'],
        'peak_power_kw': agg['peak_power_kw'],
        'peak_ts': peak['ts'] if peak else None,
        'energy_by_category_json': json.dumps({k: agg[k] for k in _CATEGORY_COLUMNS}),
        'top_machines_json': json.dumps([dict(r) for r in top]),
        'hours_processed': agg['hours'],
        'is_partial': True,
    })
    return summary


def get_hourly_totals(simulation_id: int, db_path: str = None) -> list[dict[str, Any]]:
    """Get hourly totals for a simulation (8760 points).
    
    Args:
        simulation_id: Simulation ID
        
    Returns:
        List of hourly data points with timestamp and power/energy values
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT 
                ts,
                hour_index,
                total_power_kw,
                total_energy_kwh,
                hvac_power_kw,
                compressors_power_kw,
                motors_power_kw,
                pumps_power_kw,
                lighting_power_kw,
                lab_power_kw,
                manufacturing_power_kw,
                it_power_kw,
                auxiliary_power_kw,
                machine_count,
                avg_load_factor
            FROM hourly_totals
            WHERE simulation_id = ?
            ORDER BY hour_index
        """, (simulation_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_machine_measurements(
    simulation_id: int,
    machine_code: str,
    db_path: str = None
) -> list[dict[str, Any]]:
    """Get measurements for a specific machine in a simulation.
    
    Args:
        simulation_id: Simulation ID
        machine_code: Machine code (e.g., 'HVAC-001')
        
    Returns:
        List of hourly measurements for the machine
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT 
                mm.ts,
                mm.hour_index,
                mm.active_power_kw,
                mm.energy_kwh,
                mm.load_factor,
                mm.power_factor,
                mm.current_a,
                mm.operation_state,
                mm.cycle_phase
            FROM machine_measurements mm
            JOIN machines m ON mm.machine_id = m.machine_id
            WHERE mm.simulation_id = ? AND m.machine_code = ?
            ORDER BY mm.hour_index
        """, (simulation_id, machine_code))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_export_data(
    simulation_id: int,
    start_ts: str = None,
    end_ts: str = None,
    db_path: str = None
) -> list[dict[str, Any]]:
    """Get data for export with optional date filtering.
    
    Args:
        simulation_id: Simulation ID
        start_ts: Start timestamp (YYYY-MM-DD HH:MM:SS) or None for all data
        end_ts: End timestamp (YYYY-MM-DD HH:MM:SS) or None for all data
        
    Returns:
        List of hourly data points within the specified range
    """
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT 
                ts,
                hour_index,
                total_power_kw,
                total_energy_kwh,
                hvac_power_kw,
                compressors_power_kw,
                motors_power_kw,
                pumps_power_kw,
                lighting_power_kw,
                lab_power_kw,
                manufacturing_power_kw,
                it_power_kw,
                auxiliary_power_kw
            FROM hourly_totals
            WHERE simulation_id = ?
        """
        params = [simulation_id]
        
        if start_ts:
            query += " AND ts >= ?"
            params.append(start_ts)
        
        if end_ts:
            query += " AND ts <= ?"
            params.append(end_ts)
        
        query += " ORDER BY hour_index"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def validate_simulation_id(simulation_id: int, db_path: str = None) -> bool:
    """Check if a simulation ID exists.
    
    Args:
        simulation_id: Simulation ID to validate
        
    Returns:
        True if exists, False otherwise
    """
    try:
        conn = get_db_connection(db_path)
    except sqlite3.OperationalError:
        return False
    try:
        cursor = conn.execute("""
            SELECT 1 FROM simulations WHERE simulation_id = ?
        """, (simulation_id,))
        return cursor.fetchone() is not None
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def validate_machine_code(machine_code: str, db_path: str = None) -> bool:
    """Check if a machine code exists.
    
    Args:
        machine_code: Machine code to validate
        
    Returns:
        True if exists, False otherwise
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT 1 FROM machines WHERE machine_code = ? AND active = 1
        """, (machine_code,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Real-measurement import (digital shadow): read-write helpers.
# The import_data / import_measurements tables from data/schema_simulator.sql
# already exist and are reused as the storage for real measurements.
# ---------------------------------------------------------------------------


def get_db_connection_rw(db_path: str = None) -> sqlite3.Connection:
    """Get a read-write database connection for the import path.

    Used only by the import/delete helpers. Like the read-only helper it
    refuses to touch a missing file: sqlite3.connect() on a non-existent path
    silently creates an empty database, and the MATLAB side skips schema
    creation when the file already exists.

    Args:
        db_path: Path to SQLite database file. If None, uses default path.

    Returns:
        sqlite3.Connection with row_factory and manual transaction control

    Raises:
        sqlite3.OperationalError: if the database file does not exist yet.
    """
    if db_path is None:
        # Default path relative to this file
        db_path = Path(__file__).parent.parent.parent / 'data' / 'spacewise.db'

    resolved = Path(db_path).resolve()
    if not resolved.exists():
        raise sqlite3.OperationalError(f'database file not found: {resolved}')
    conn = sqlite3.connect(str(resolved), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _next_import_code(conn: sqlite3.Connection) -> str:
    """Return an unused IMPORT-xxxxx code for a new import_data row."""
    next_id = conn.execute(
        "SELECT COALESCE(MAX(import_id), 0) + 1 FROM import_data"
    ).fetchone()[0]
    code = f'IMPORT-{next_id:05d}'
    while conn.execute(
        "SELECT 1 FROM import_data WHERE import_code = ?", (code,)
    ).fetchone():
        next_id += 1
        code = f'IMPORT-{next_id:05d}'
    return code


def insert_import(name: str, source: str = None, notes: str = None,
                  db_path: str = None) -> int:
    """Create an import_data header row and return its import_id.

    Args:
        name: Descriptive name (import_data.name, NOT NULL in the schema)
        source: Origin file name (import_data.source_file)
        notes: Free text (import_data.description)

    Returns:
        The new import_id.
    """
    conn = get_db_connection_rw(db_path)
    try:
        conn.execute('BEGIN')
        cursor = conn.execute("""
            INSERT INTO import_data (import_code, name, source_file, description)
            VALUES (?, ?, ?, ?)
        """, (_next_import_code(conn), name, source, notes))
        import_id = cursor.lastrowid
        conn.execute('COMMIT')
        return import_id
    except Exception:
        conn.execute('ROLLBACK')
        raise
    finally:
        conn.close()


def bulk_insert_real_measurements(import_id: int, rows: list[dict[str, Any]],
                                  db_path: str = None) -> int:
    """Insert validated real measurements for one import, atomically.

    Each row is a dict with keys: machine_code, ts, active_power_kw and the
    optional energy_kwh, current_a, power_factor, voltage_v, metadata_json.
    On failure the measurement insert is rolled back and the header row
    created by insert_import() is removed as well, so an import never exists
    without its data (all rows or none).

    Returns:
        Number of rows inserted.
    """
    payload = [
        (import_id,
         r.get('machine_code'),
         r.get('ts'),
         r.get('active_power_kw'),
         r.get('energy_kwh'),
         r.get('current_a'),
         r.get('power_factor'),
         r.get('voltage_v'),
         r.get('metadata_json'))
        for r in rows
    ]
    conn = get_db_connection_rw(db_path)
    try:
        conn.execute('BEGIN')
        conn.executemany("""
            INSERT INTO import_measurements (
                import_id, machine_code, ts, active_power_kw,
                energy_kwh, current_a, power_factor, voltage_v, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, payload)
        conn.execute("""
            UPDATE import_data
            SET total_records = (SELECT COUNT(*) FROM import_measurements WHERE import_id = ?),
                start_date = (SELECT MIN(ts) FROM import_measurements WHERE import_id = ?),
                end_date = (SELECT MAX(ts) FROM import_measurements WHERE import_id = ?)
            WHERE import_id = ?
        """, (import_id, import_id, import_id, import_id))
        conn.execute('COMMIT')
        return len(payload)
    except Exception:
        conn.execute('ROLLBACK')
        conn.execute('DELETE FROM import_data WHERE import_id = ?', (import_id,))
        raise
    finally:
        conn.close()


def list_imports(db_path: str = None) -> list[dict[str, Any]]:
    """List all real-data imports, newest first.

    Returns:
        List of import_data rows (id, code, name, source, dates, counts).
    """
    try:
        conn = get_db_connection(db_path)
    except sqlite3.OperationalError:
        return []  # database not created yet (simulator still starting)
    try:
        cursor = conn.execute("""
            SELECT
                import_id,
                import_code,
                name,
                source_file,
                import_date,
                description,
                start_date,
                end_date,
                total_records
            FROM import_data
            ORDER BY import_date DESC, import_id DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []  # tables not created yet
    finally:
        conn.close()


def get_import_detail(import_id: int, db_path: str = None) -> dict[str, Any] | None:
    """Get one import with its header data and per-machine row counts.

    Returns:
        Import detail dict, or None when the import_id does not exist.
    """
    try:
        conn = get_db_connection(db_path)
    except sqlite3.OperationalError:
        return None
    try:
        header = conn.execute("""
            SELECT
                import_id,
                import_code,
                name,
                source_file,
                import_date,
                description,
                start_date,
                end_date,
                total_records,
                metadata_json
            FROM import_data
            WHERE import_id = ?
        """, (import_id,)).fetchone()
        if header is None:
            return None
        detail = dict(header)
        machines = conn.execute("""
            SELECT
                COALESCE(machine_code, '') AS machine_code,
                COUNT(*) AS rows,
                MIN(ts) AS first_ts,
                MAX(ts) AS last_ts
            FROM import_measurements
            WHERE import_id = ?
            GROUP BY machine_code
            ORDER BY rows DESC, machine_code ASC
        """, (import_id,)).fetchall()
        detail['machines'] = [dict(row) for row in machines]
        return detail
    except sqlite3.OperationalError:
        return None  # tables not created yet
    finally:
        conn.close()


def delete_import(import_id: int, db_path: str = None) -> dict[str, Any] | None:
    """Delete an import and cascade the removal to its measurements.

    The schema has no ON DELETE CASCADE, so the child rows are removed
    explicitly inside one transaction.

    Returns:
        {'import_id': ..., 'rows_removed': n}, or None when it does not exist.
    """
    conn = get_db_connection_rw(db_path)
    try:
        conn.execute('BEGIN')
        exists = conn.execute(
            'SELECT 1 FROM import_data WHERE import_id = ?', (import_id,)
        ).fetchone()
        if exists is None:
            conn.execute('ROLLBACK')
            return None
        rows_removed = conn.execute(
            'DELETE FROM import_measurements WHERE import_id = ?', (import_id,)
        ).rowcount
        conn.execute('DELETE FROM import_data WHERE import_id = ?', (import_id,))
        conn.execute('COMMIT')
        return {'import_id': import_id, 'rows_removed': rows_removed}
    except Exception:
        conn.execute('ROLLBACK')
        raise
    finally:
        conn.close()


_REAL_SELECT = """
            SELECT
                import_meas_id,
                machine_code,
                ts,
                active_power_kw,
                energy_kwh,
                current_a,
                power_factor,
                voltage_v,
                metadata_json
            FROM import_measurements
            WHERE import_id = ?
        """


def _real_measurements_query(conn: sqlite3.Connection, import_id: int,
                             machine_code: str | None, start_ts: str | None,
                             end_ts: str | None) -> list[sqlite3.Row]:
    """Shared SELECT for real measurements (kept in one place for both helpers)."""
    query = _REAL_SELECT
    params: list[Any] = [import_id]
    if machine_code:
        query += ' AND machine_code = ?'
        params.append(machine_code)
    if start_ts:
        query += ' AND ts >= ?'
        params.append(start_ts)
    if end_ts:
        query += ' AND ts <= ?'
        params.append(end_ts)
    query += ' ORDER BY ts, import_meas_id'
    return conn.execute(query, params).fetchall()


def get_real_measurements(import_id: int, machine_code: str = None,
                          start_ts: str = None, end_ts: str = None,
                          db_path: str = None) -> list[dict[str, Any]]:
    """Get imported real measurements with optional machine/date filtering.

    Args:
        import_id: Import to read
        machine_code: Restrict to one machine, or None for all
        start_ts: Lower bound timestamp (inclusive), or None
        end_ts: Upper bound timestamp (inclusive), or None

    Returns:
        List of measurement dicts ordered by ts.
    """
    conn = get_db_connection(db_path)
    try:
        return [dict(row) for row in _real_measurements_query(
            conn, import_id, machine_code, start_ts, end_ts)]
    finally:
        conn.close()


def get_comparison(simulation_id: int, machine_code: str, import_id: int,
                   db_path: str = None) -> dict[str, Any]:
    """Compare the simulated hourly profile of one machine against real data.

    Alignment is by exact ts string equality ('YYYY-MM-DD HH:MM:SS'), matching
    the hourly grid the simulator writes. Hours where the real measurement is
    zero are still aligned hours but are excluded from MAPE/bias (division by
    zero guard). Empty overlap yields zero coverage and null error metrics,
    never an error.

    Returns:
        Dict with the aligned series plus mape_pct, mean_bias_pct,
        hours_compared and coverage_pct (share of simulation hours that have
        a real match).
    """
    conn = get_db_connection(db_path)
    try:
        sim_rows = conn.execute("""
            SELECT mm.ts, mm.active_power_kw
            FROM machine_measurements mm
            JOIN machines m ON mm.machine_id = m.machine_id
            WHERE mm.simulation_id = ? AND m.machine_code = ?
            ORDER BY mm.hour_index
        """, (simulation_id, machine_code)).fetchall()
        real_rows = _real_measurements_query(conn, import_id, machine_code, None, None)
    finally:
        conn.close()

    sim_by_ts: dict[str, float] = {}
    for row in sim_rows:
        sim_by_ts.setdefault(row['ts'], row['active_power_kw'])
    real_by_ts: dict[str, float] = {}
    for row in real_rows:
        if row['active_power_kw'] is None:
            continue
        real_by_ts.setdefault(row['ts'], row['active_power_kw'])

    common_ts = sorted(set(sim_by_ts) & set(real_by_ts))
    series = [
        {'ts': ts, 'simulated_kw': sim_by_ts[ts], 'real_kw': real_by_ts[ts]}
        for ts in common_ts
    ]

    # Percentage errors use only hours with a real reading above zero.
    apes = [abs(sim_by_ts[ts] - real_by_ts[ts]) / real_by_ts[ts] * 100.0
            for ts in common_ts if real_by_ts[ts] > 0]
    biases = [(sim_by_ts[ts] - real_by_ts[ts]) / real_by_ts[ts] * 100.0
              for ts in common_ts if real_by_ts[ts] > 0]

    sim_hours = len(sim_by_ts)
    return {
        'simulation_id': simulation_id,
        'machine_code': machine_code,
        'import_id': import_id,
        'series': series,
        'points': len(series),
        'hours_compared': len(common_ts),
        'coverage_pct': (len(common_ts) / sim_hours * 100.0) if sim_hours else 0.0,
        'mape_pct': (sum(apes) / len(apes)) if apes else None,
        'mean_bias_pct': (sum(biases) / len(biases)) if biases else None,
    }
