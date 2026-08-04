#!/usr/bin/env python3
"""Orquestador del gemelo digital SPACEWISE AI.

Al ejecutarse inicia el pipeline completo de MATLAB:
    init_db -> seed_devices -> run_simulations -> query_reports

init_db borra y recrea bd/spacewise.db (reset limpio) para evitar datos
duplicados entre corridas.

Requisitos: MATLAB R2026a+ con Database Toolbox, en el PATH o definiendo la
variable de entorno MATLAB_BIN. No requiere paquetes pip (solo stdlib).
"""

import argparse
import locale
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "matlab" / "scripts"
SCRIPTS = ["init_db", "seed_devices", "run_simulations", "query_reports"]
DEFAULT_MATLAB = Path(r"C:\Program Files\MATLAB\R2026a\bin\matlab.exe")


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orquestador del gemelo digital SPACEWISE AI (MATLAB)."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="tiempo máximo de la corrida en segundos (default: 3600).",
    )
    args = parser.parse_args()

    if not SCRIPTS_DIR.is_dir():
        logging.error("No existe la carpeta de scripts: %s", SCRIPTS_DIR)
        return 2

    matlab = find_matlab()
    cmd = [matlab, "-batch", build_batch()]

    logging.info("MATLAB: %s", matlab)
    logging.info("Pasos: %s", ", ".join(SCRIPTS))
    logging.info("Ejecutando: %s", " ".join(cmd))

    t0 = time.perf_counter()
    encoding = console_encoding()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(SCRIPTS_DIR),
            text=True,
            encoding=encoding,
            errors="replace",
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        logging.error("Tiempo agotado tras %d s.", args.timeout)
        return 3

    elapsed = time.perf_counter() - t0
    logging.info(
        "Pipeline finalizado en %.1f s con código %d.", elapsed, proc.returncode
    )
    return proc.returncode


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    sys.exit(main())
