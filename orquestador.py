#!/usr/bin/env python3
"""Orquestador del simulador de maquinaria industrial SPACEWISE AI.

Modos de ejecución:
    once:       Ejecuta el pipeline completo una vez (init_db -> load_catalog ->
                run_simulation -> export_results) y termina.
    continuous: Prepara la base de datos y levanta la simulación continua de
                MATLAB junto con el servidor web (API + dashboard).
    full:       Igual que continuous y además abre el dashboard en el navegador
                (modo por defecto).

Los defaults de --mode y --interval pueden fijarse en el archivo .env de la
raíz con las variables MODE y SIM_INTERVAL (la línea de comando gana siempre).
Ver .env.example para todas las variables.

En continuous/full el orquestador:
    1. crea data/spacewise.db con el esquema si todavía no existe,
    2. lanza la simulación continua en MATLAB (se reinicia sola si falla; la
       simulación retoma desde la última hora guardada),
    3. lanza Flask, que sirve la API y el dashboard en http://127.0.0.1:5000,
    4. espera a que el servidor responda y abre el navegador,
    5. al presionar Ctrl+C detiene todos los procesos.

Los registros de cada proceso quedan en data/logs/.

Requisitos: MATLAB R2026a+ con Database Toolbox (en el PATH o con la variable
de entorno MATLAB_BIN) y, para el dashboard, las dependencias de
requirements.txt (Flask).
"""

import argparse
import importlib.util
import locale
import logging
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv es opcional: solo lee un .env local
    def load_dotenv(*args, **kwargs):
        return False


REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(REPO_ROOT / ".env")

SCRIPTS_DIR = REPO_ROOT / "matlab" / "scripts"
SCRIPTS = ["init_db", "load_catalog", "run_simulation", "export_results"]
DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "spacewise.db"
SCHEMA_PATH = DATA_DIR / "schema_simulator.sql"
LOG_DIR = DATA_DIR / "logs"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
# Defaults de ejecución: la línea de comando gana sobre estas variables de .env.
MODE = os.getenv("MODE", "full").strip() or "full"
SIM_INTERVAL = os.getenv("SIM_INTERVAL", "2")
MAX_MATLAB_RESTARTS = 3


# ---------------------------------------------------------------------------
# MATLAB
# ---------------------------------------------------------------------------

def _matlab_candidates() -> list:
    """Rutas habituales de instalación de MATLAB, de la versión más nueva a la más antigua."""
    exe = "matlab.exe" if os.name == "nt" else "matlab"
    roots = []
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                roots.append(Path(base) / "MATLAB")
    else:
        roots += [Path("/usr/local/MATLAB"), Path.home() / "MATLAB", Path("/opt/MATLAB")]

    found = []
    for root in roots:
        if root.is_dir():
            found += sorted(root.glob(f"R20*/bin/{exe}"), reverse=True)
    return found


def find_matlab() -> str:
    """Devuelve la ruta del ejecutable de MATLAB.

    Orden: MATLAB_BIN, PATH, DEFAULT_MATLAB (variable de entorno o .env) y, por
    último, las carpetas de instalación habituales.
    """
    exe = os.environ.get("MATLAB_BIN")
    if exe:
        return exe
    which = shutil.which("matlab")
    if which:
        return which
    default = os.environ.get("DEFAULT_MATLAB")
    if default and Path(default.strip()).exists():
        return str(Path(default.strip()))
    candidates = _matlab_candidates()
    if candidates:
        return str(candidates[0])
    raise RuntimeError(
        "No se encontró MATLAB. Defina la variable de entorno MATLAB_BIN "
        "o agregue la carpeta bin de MATLAB al PATH."
    )


def console_encoding() -> str:
    """Encoding de salida de MATLAB cuando su stdout es redirigido.

    En Windows MATLAB escribe usando la página de códigos OEM de la consola
    (p. ej. cp850), no la ANSI ni UTF-8.
    """
    if os.name == "nt":
        try:
            import ctypes

            oem = ctypes.windll.kernel32.GetOEMCP()
            if oem:
                return f"cp{oem}"
        except Exception:
            pass
    return locale.getpreferredencoding(False)


def build_batch() -> str:
    """Construye el comando -batch: agrega paths y ejecuta los pasos en orden."""
    # Agregar paths a src y config ANTES de ejecutar scripts
    src_path = REPO_ROOT / "matlab" / "src"
    config_path = REPO_ROOT / "matlab" / "config"
    scripts_path = REPO_ROOT / "matlab" / "scripts"

    add_paths = (
        f"addpath('{src_path.as_posix()}'); "
        f"addpath('{config_path.as_posix()}'); "
        f"addpath('{scripts_path.as_posix()}');"
    )

    # Ejecutar los pasos usando run() con rutas absolutas
    steps = "; ".join(
        f"run('{(scripts_path / f'{script}.m').as_posix()}')" for script in SCRIPTS
    )
    return f"{add_paths} {steps};"


def run_once(matlab: str, timeout: int) -> int:
    """Ejecuta el pipeline completo una vez."""
    cmd = [matlab, "-batch", build_batch()]

    logging.info("MATLAB: %s", matlab)
    logging.info("Pasos: %s", ", ".join(SCRIPTS))
    logging.info("Ejecutando: %s", " ".join(cmd))

    t0 = time.perf_counter()
    encoding = console_encoding()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            text=True,
            encoding=encoding,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logging.error("Tiempo agotado tras %d s.", timeout)
        return 3

    elapsed = time.perf_counter() - t0
    logging.info(
        "Pipeline finalizado en %.1f s con código %d.", elapsed, proc.returncode
    )
    return proc.returncode


# ---------------------------------------------------------------------------
# Base de datos y servidor web
# ---------------------------------------------------------------------------

def ensure_database() -> None:
    """Crea data/spacewise.db con el esquema si no existe o está vacía.

    Se hace antes de lanzar nada para que Flask encuentre la base desde el
    primer segundo (MATLAB tarda en arrancar). Las rutinas de MATLAB no vuelven
    a crear el esquema cuando el archivo ya existe, por eso debe quedar completo.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    has_schema = False
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='simulations'"
            ).fetchone()
            has_schema = row is not None
        finally:
            conn.close()
    if has_schema:
        logging.info("Base de datos existente: %s", DB_PATH)
        return

    if not SCHEMA_PATH.exists():
        raise RuntimeError(f"No se encontró el esquema SQL: {SCHEMA_PATH}")

    if DB_PATH.exists():
        DB_PATH.unlink()  # archivo vacío/inválido creado por un arranque fallido
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    logging.info("Base de datos creada: %s", DB_PATH)


def check_web_dependencies() -> None:
    """Verifica que Flask esté instalado antes de lanzar el servidor."""
    missing = [m for m in ("flask", "flask_cors") if importlib.util.find_spec(m) is None]
    if missing:
        raise RuntimeError(
            "Faltan dependencias del dashboard (" + ", ".join(missing) + "). "
            "Instálelas con: pip install -r requirements.txt"
        )


def wait_for_server(timeout: float = 30.0) -> bool:
    """Espera hasta que Flask responda en /api/health."""
    url = f"http://{HOST}:{PORT}/api/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Procesos
# ---------------------------------------------------------------------------

def open_log(name: str):
    """Abre un archivo de registro en data/logs/ para la salida de un proceso."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return open(LOG_DIR / name, "ab")


def start_matlab_continuous(matlab: str, interval: int, log) -> subprocess.Popen:
    """Lanza la simulación continua de MATLAB."""
    script = (REPO_ROOT / "matlab" / "scripts" / "run_continuous.m").as_posix()
    env = dict(os.environ, SIM_INTERVAL=str(interval))
    return subprocess.Popen(
        [matlab, "-batch", f"run('{script}')"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )


def start_flask(log) -> subprocess.Popen:
    """Lanza el servidor Flask (API + dashboard)."""
    env = dict(os.environ, HOST=HOST, PORT=str(PORT), PYTHONUNBUFFERED="1")
    return subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "web" / "backend" / "app.py")],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )


def stop_process(proc: subprocess.Popen, name: str) -> None:
    """Detiene un proceso y sus hijos (MATLAB lanza procesos auxiliares)."""
    if proc is None or proc.poll() is not None:
        return
    logging.info("Deteniendo %s (PID %d)...", name, proc.pid)
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_continuous(matlab: str, interval: int, open_browser: bool) -> int:
    """Prepara la base y ejecuta simulación continua + dashboard."""
    try:
        check_web_dependencies()
        ensure_database()
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 2

    matlab_log = open_log("matlab.log")
    flask_log = open_log("flask.log")

    logging.info("Iniciando servidor web...")
    flask_proc = start_flask(flask_log)

    logging.info("Iniciando simulación continua de MATLAB...")
    matlab_proc = start_matlab_continuous(matlab, interval, matlab_log)
    restarts = 0
    matlab_done = False

    def shutdown() -> None:
        logging.info("Deteniendo servicios...")
        stop_process(matlab_proc, "MATLAB")
        stop_process(flask_proc, "Flask")
        matlab_log.close()
        flask_log.close()
        logging.info("Servicios detenidos")

    def on_signal(signum, frame):
        logging.info("Señal %d recibida.", signum)
        shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    if not wait_for_server():
        logging.error(
            "El servidor web no respondió en el puerto %d. Revise %s",
            PORT, LOG_DIR / "flask.log",
        )
        shutdown()
        return 1

    url = f"http://{HOST}:{PORT}"
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as exc:  # el navegador no es crítico
            logging.warning("No se pudo abrir el navegador: %s", exc)

    logging.info("=" * 60)
    logging.info("Servicios activos:")
    logging.info("  - Simulación continua MATLAB (PID %d)", matlab_proc.pid)
    logging.info("  - Servidor web / dashboard (PID %d): %s", flask_proc.pid, url)
    logging.info("  - Registros: %s", LOG_DIR)
    logging.info("Presione Ctrl+C para detener todo")
    logging.info("=" * 60)

    try:
        while True:
            if flask_proc.poll() is not None:
                logging.error(
                    "El servidor web terminó con código %d. Revise %s",
                    flask_proc.returncode, LOG_DIR / "flask.log",
                )
                shutdown()
                return flask_proc.returncode or 1

            if not matlab_done:
                code = matlab_proc.poll()
                if code is not None:
                    if code == 0:
                        logging.info(
                            "La simulación terminó. El dashboard sigue activo; "
                            "Ctrl+C para salir."
                        )
                        matlab_done = True
                    elif restarts < MAX_MATLAB_RESTARTS:
                        restarts += 1
                        logging.warning(
                            "MATLAB terminó con código %d. Reiniciando (%d/%d); "
                            "la simulación continúa desde la última hora guardada. "
                            "Detalle en %s",
                            code, restarts, MAX_MATLAB_RESTARTS, LOG_DIR / "matlab.log",
                        )
                        time.sleep(5)
                        matlab_proc = start_matlab_continuous(matlab, interval, matlab_log)
                    else:
                        logging.error(
                            "MATLAB falló %d veces. El dashboard sigue activo con los datos "
                            "generados. Revise %s",
                            MAX_MATLAB_RESTARTS + 1, LOG_DIR / "matlab.log",
                        )
                        matlab_done = True
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orquestador del simulador de maquinaria industrial SPACEWISE AI (MATLAB)."
    )
    parser.add_argument(
        "--mode",
        choices=["once", "continuous", "full"],
        default=MODE,
        help="Modo de ejecución: 'once' (una sola vez), 'continuous' (continuo + dashboard), "
             "'full' (continuo + dashboard + navegador). Default: variable MODE del .env, "
             "o 'full' si no está definida",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(SIM_INTERVAL),
        help="Segundos de tiempo real entre cada hora simulada (default: variable "
             "SIM_INTERVAL del .env, o 2 si no está definida)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir navegador automáticamente en modo 'full'",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("ONCE_TIMEOUT", "3600")),
        help="Tiempo máximo de la corrida en segundos para modo 'once' "
             "(default: variable ONCE_TIMEOUT del .env, o 3600)",
    )
    args = parser.parse_args()

    if not SCRIPTS_DIR.is_dir():
        logging.error("No existe la carpeta de scripts: %s", SCRIPTS_DIR)
        return 2

    try:
        matlab = find_matlab()
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 2
    logging.info("MATLAB: %s", matlab)

    if args.mode == "once":
        return run_once(matlab, args.timeout)
    return run_continuous(matlab, max(1, args.interval),
                          open_browser=(args.mode == "full" and not args.no_browser))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    sys.exit(main())
