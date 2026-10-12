#!/usr/bin/env python3
"""Orquestador del simulador de maquinaria industrial SPACEWISE AI.

Modos de ejecución:
    once:       Ejecuta el pipeline completo una vez (init_db -> load_catalog -> 
                run_simulation -> export_results) y termina.
    continuous: Inicia simulación continua de MATLAB en background + Flask backend.
    full:       Igual que continuous + abre navegador en http://localhost:5000.

Requisitos: MATLAB R2026a+ con Database Toolbox, en el PATH o definiendo la
variable de entorno MATLAB_BIN. No requiere paquetes pip (solo stdlib).
"""

import argparse
import locale
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()
REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "matlab" / "scripts"
SCRIPTS = ["init_db", "load_catalog", "run_simulation", "export_results"]
DEFAULT_MATLAB = os.getenv("DEFAULT_MATLAB", "/usr/local/MATLAB/R2026a/bin/matlab")


def find_matlab() -> str:
    """Devuelve la ruta del ejecutable de MATLAB."""
    exe = os.environ.get("MATLAB_BIN")
    if exe:
        return exe
    which = shutil.which("matlab")
    if which:
        return which
    if DEFAULT_MATLAB.exists():
        return str(DEFAULT_MATLAB)
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
    """Construye el comando -batch: cd a scripts y ejecuta los pasos en orden."""
    steps = "; ".join(SCRIPTS)
    return f"cd('{SCRIPTS_DIR.as_posix()}'); {steps};"


def run_once(matlab: str, timeout: int) -> int:
    """Ejecuta el pipeline completo una vez (modo original)."""
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


def run_continuous(matlab: str, interval: int, open_browser: bool) -> int:
    """Ejecuta simulación continua + Flask backend en background."""
    logging.info("Starting continuous mode...")
    
    # Start MATLAB continuous simulation
    matlab_cmd = [
        matlab, "-batch",
        f"run('{(REPO_ROOT / 'matlab' / 'scripts' / 'run_continuous.m').as_posix()}')"
    ]
    
    logging.info("Starting MATLAB continuous simulation...")
    logging.info("Command: %s", " ".join(matlab_cmd))
    
    matlab_proc = subprocess.Popen(
        matlab_cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    
    # Start Flask backend
    flask_cmd = [sys.executable, "web/backend/app.py"]
    logging.info("Starting Flask backend...")
    logging.info("Command: %s", " ".join(flask_cmd))
    
    flask_proc = subprocess.Popen(
        flask_cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    
    # Wait a bit for Flask to start
    time.sleep(2)
    
    # Open browser if requested
    if open_browser:
        logging.info("Opening browser at http://localhost:5000")
        try:
            webbrowser.open("http://localhost:5000")
        except Exception as e:
            logging.warning("Could not open browser: %s", e)
    
    logging.info("=" * 60)
    logging.info("Services running:")
    logging.info("  - MATLAB continuous simulation (PID: %d)", matlab_proc.pid)
    logging.info("  - Flask backend (PID: %d)", flask_proc.pid)
    if open_browser:
        logging.info("  - Browser: http://localhost:5000")
    logging.info("Press Ctrl+C to stop all services")
    logging.info("=" * 60)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logging.info("\nReceived signal %d, shutting down...", signum)
        shutdown(matlab_proc, flask_proc)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Monitor processes
    try:
        while True:
            # Check if MATLAB process is still running
            matlab_ret = matlab_proc.poll()
            if matlab_ret is not None:
                logging.warning("MATLAB process exited with code %d", matlab_ret)
                if matlab_ret != 0:
                    # Print error output
                    _, stderr = matlab_proc.communicate()
                    if stderr:
                        logging.error("MATLAB error output:\n%s", stderr)
                shutdown(matlab_proc, flask_proc)
                return matlab_ret
            
            # Check if Flask process is still running
            flask_ret = flask_proc.poll()
            if flask_ret is not None:
                logging.warning("Flask process exited with code %d", flask_ret)
                shutdown(matlab_proc, flask_proc)
                return flask_ret
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("\nKeyboardInterrupt received, shutting down...")
        shutdown(matlab_proc, flask_proc)
        return 0


def shutdown(matlab_proc: subprocess.Popen, flask_proc: subprocess.Popen):
    """Termina ambos procesos de forma graceful."""
    logging.info("Stopping services...")
    
    # Terminate MATLAB
    if matlab_proc.poll() is None:
        logging.info("Stopping MATLAB simulation (PID: %d)...", matlab_proc.pid)
        matlab_proc.terminate()
        try:
            matlab_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logging.warning("MATLAB did not terminate gracefully, killing...")
            matlab_proc.kill()
    
    # Terminate Flask
    if flask_proc.poll() is None:
        logging.info("Stopping Flask backend (PID: %d)...", flask_proc.pid)
        flask_proc.terminate()
        try:
            flask_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logging.warning("Flask did not terminate gracefully, killing...")
            flask_proc.kill()
    
    logging.info("All services stopped")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orquestador del simulador de maquinaria industrial SPACEWISE AI (MATLAB)."
    )
    parser.add_argument(
        "--mode",
        choices=["once", "continuous", "full"],
        default="full",
        help="Modo de ejecución: 'once' (una sola vez), 'continuous' (continuo + Flask), "
             "'full' (continuo + Flask + navegador). Default: full",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Intervalo en segundos entre actualizaciones de simulación (default: 2)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir navegador automáticamente en modo 'full'",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Tiempo máximo de la corrida en segundos para modo 'once' (default: 3600)",
    )
    args = parser.parse_args()

    if not SCRIPTS_DIR.is_dir():
        logging.error("No existe la carpeta de scripts: %s", SCRIPTS_DIR)
        return 2

    matlab = find_matlab()
    logging.info("MATLAB: %s", matlab)

    if args.mode == "once":
        return run_once(matlab, args.timeout)
    elif args.mode == "continuous":
        return run_continuous(matlab, args.interval, open_browser=False)
    elif args.mode == "full":
        return run_continuous(matlab, args.interval, open_browser=not args.no_browser)
    else:
        logging.error("Modo no reconocido: %s", args.mode)
        return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    sys.exit(main())
