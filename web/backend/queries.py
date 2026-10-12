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
