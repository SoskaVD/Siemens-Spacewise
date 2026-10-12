#!/usr/bin/env python3
"""Tests de integración del simulador de maquinaria industrial.

Verifica que el pipeline completo de MATLAB funcione correctamente:
init_db -> load_catalog -> run_simulation -> export_results

Requisitos: MATLAB R2026a+ con Database Toolbox.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestIntegration(unittest.TestCase):
    """Tests de integración del pipeline completo."""

    def setUp(self):
        """Prepara el entorno de prueba."""
        self.repo_root = Path(__file__).resolve().parent.parent
        self.scripts_dir = self.repo_root / "matlab" / "scripts"
        self.data_dir = self.repo_root / "data"
        self.db_path = self.data_dir / "spacewise.db"
        
        # Find MATLAB
        self.matlab_bin = os.environ.get("MATLAB_BIN") or shutil.which("matlab")
        if not self.matlab_bin:
            self.skipTest("MATLAB no disponible (defina MATLAB_BIN o agregue al PATH)")

    def test_01_init_db(self):
        """Test 01: init_db.m crea la base de datos y esquema correctamente."""
        # Remove existing DB if present
        if self.db_path.exists():
            self.db_path.unlink()
        
        # Run init_db
        result = self._run_matlab_script("init_db")
        
        # Verify
        self.assertEqual(result.returncode, 0, "init_db failed")
        self.assertTrue(self.db_path.exists(), "Database file not created")
        self.assertGreater(self.db_path.stat().st_size, 0, "Database file is empty")

    def test_02_load_catalog(self):
        """Test 02: load_catalog.m carga el catálogo de 110 máquinas."""
        # Ensure DB exists
        if not self.db_path.exists():
            self._run_matlab_script("init_db")
        
        # Run load_catalog
        result = self._run_matlab_script("load_catalog")
        
        # Verify
        self.assertEqual(result.returncode, 0, "load_catalog failed")
        self.assertIn("Loaded 110 machines", result.stdout, 
                      "Catalog loading message not found")

    def test_03_run_simulation(self):
        """Test 03: run_simulation.m ejecuta simulación completa."""
        # Ensure catalog is loaded
        if not self.db_path.exists():
            self._run_matlab_script("init_db")
            self._run_matlab_script("load_catalog")
        
        # Run simulation
        result = self._run_matlab_script("run_simulation")
        
        # Verify
        self.assertEqual(result.returncode, 0, "run_simulation failed")
        self.assertIn("Simulation completed", result.stdout,
                      "Simulation completion message not found")
        self.assertIn("Total energy:", result.stdout,
                      "Energy summary not found")

    def test_04_export_results(self):
        """Test 04: export_results.m exporta datos correctamente."""
        # Ensure simulation has run
        if not self.db_path.exists():
            self._run_matlab_script("init_db")
            self._run_matlab_script("load_catalog")
            self._run_matlab_script("run_simulation")
        
        # Run export
        result = self._run_matlab_script("export_results")
        
        # Verify
        self.assertEqual(result.returncode, 0, "export_results failed")
        
        # Check export directory exists and has files
        export_dir = self.repo_root / "data" / "export"
        self.assertTrue(export_dir.exists(), "Export directory not created")
        
        exported_files = list(export_dir.glob("*"))
        self.assertGreater(len(exported_files), 0, "No files exported")

    def test_05_full_pipeline(self):
        """Test 05: Pipeline completo desde cero."""
        # Clean slate
        if self.db_path.exists():
            self.db_path.unlink()
        
        export_dir = self.repo_root / "data" / "export"
        if export_dir.exists():
            shutil.rmtree(export_dir)
        
        # Run full pipeline
        scripts = ["init_db", "load_catalog", "run_simulation", "export_results"]
        for script in scripts:
            result = self._run_matlab_script(script)
            self.assertEqual(result.returncode, 0, f"{script} failed")
        
        # Final verification
        self.assertTrue(self.db_path.exists(), "Database not created")
        self.assertTrue(export_dir.exists(), "Export directory not created")
        self.assertGreater(len(list(export_dir.glob("*"))), 0, "No files exported")

    def _run_matlab_script(self, script_name: str) -> subprocess.CompletedProcess:
        """Ejecuta un script de MATLAB y retorna el resultado."""
        script_path = self.scripts_dir / f"{script_name}.m"
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        cmd = [self.matlab_bin, "-batch", f"run('{script_path.as_posix()}')"]
        
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout per script
            cwd=str(self.repo_root)
        )


class TestOrchestrator(unittest.TestCase):
    """Tests del orquestador Python."""

    def test_orchestrator_help(self):
        """Test: orquestador.py muestra ayuda correctamente."""
        repo_root = Path(__file__).resolve().parent.parent
        orchestrator = repo_root / "orquestador.py"
        
        result = subprocess.run(
            [sys.executable, str(orchestrator), "--help"],
            capture_output=True,
            text=True,
            cwd=str(repo_root)
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("simulador de maquinaria", result.stdout.lower())

    def test_orchestrator_scripts_config(self):
        """Test: orquestador.py tiene los scripts correctos configurados."""
        repo_root = Path(__file__).resolve().parent.parent
        orchestrator = repo_root / "orquestador.py"
        
        # Read orchestrator source
        source = orchestrator.read_text(encoding="utf-8")
        
        # Verify new pipeline
        self.assertIn("init_db", source)
        self.assertIn("load_catalog", source)
        self.assertIn("run_simulation", source)
        self.assertIn("export_results", source)
        
        # Verify old pipeline is removed
        self.assertNotIn("seed_devices", source)
        self.assertNotIn("run_simulations", source)
        self.assertNotIn("query_reports", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
