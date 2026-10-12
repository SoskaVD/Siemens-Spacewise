# Feature: Simulador de Maquinaria Industrial

## Objetivo
Implementar un simulador completo de maquinaria industrial que genere perfiles de consumo horario (8760h) para 110 equipos, con persistencia SQLite, backend web Python, y panel de visualización HTML.

## Contexto
- **Motivación:** Concurso interno Siemens Spacewise
- **Fecha límite:** 23 octubre 2026
- **Base:** Catálogo de 110 equipos en `docs/CATALOGO_EQUIPOS.md`
- **Referencia:** Gemelo digital anterior (edificio) en `matlab/`

## Alcance
1. Motor de simulación MATLAB (perfiles horarios 8760h)
2. Persistencia SQLite (esquema adaptado para máquinas)
3. Scripts de ejecución (init, load_catalog, run_simulation, export_results)
4. Tests unitarios (cobertura 80%)
5. Backend web Python (Flask)
6. Frontend HTML (Chart.js)
7. Import/Export CSV/Excel

## Restricciones
- MATLAB R2026a+ con Database Toolbox
- Python 3.9+
- Seguridad: SQL parametrizado, no eval(), validar inputs
- Commits convencionales (feat:, fix:, test:, docs:)
- Tests en cada tarea

## Criterios de aceptación
- [ ] Motor genera perfiles horarios para 110 máquinas
- [ ] SQLite almacena máquinas, simulaciones, mediciones
- [ ] Scripts ejecutan pipeline completo sin errores
- [ ] Tests unitarios pasan (cobertura ≥80%)
- [ ] Backend sirve datos vía API REST
- [ ] Frontend visualiza consumos totales, parciales, individuales
- [ ] Export CSV por rangos temporales
- [ ] Import CSV para comparación con datos reales

## Checklist de tareas

### Fase 1: Setup y commits iniciales
- [x] **T1.1** Commitear archivos actuales en main (docs, config, README) — commit c5e3c32
- [x] **T1.2** Crear rama `feature/simulador-maquinaria`
- [x] **T1.3** Diseñar esquema SQLite para simulación — data/schema_simulator.sql

### Fase 2: Motor MATLAB (prioridad alta)
- [x] **T2.1** Implementar `sim_catalog.m` (parser de markdown)
- [x] **T2.2** Implementar `sim_machine.m` (perfil individual)
- [x] **T2.3** Implementar `sim_engine.m` (motor de simulación)
- [x] **T2.4** Implementar `sim_db.m` (capa SQLite, adaptar de dt_db.m)
- [x] **T2.5** Implementar `sim_analysis.m` (análisis y agregación)
- [x] **T2.6** Implementar `sim_export.m` (exportación CSV/Excel)
- [x] **T2.7** Crear script `init_db.m` (inicializar schema)
- [x] **T2.8** Crear script `load_catalog.m` (cargar catálogo)
- [x] **T2.9** Crear script `run_simulation.m` (ejecutar simulación)
- [x] **T2.10** Crear script `export_results.m` (exportar resultados)
- [ ] **T2.11** Tests unitarios del motor (cobertura 80%)

### Fase 3: Backend web (prioridad media)
- [ ] **T3.1** Implementar `web/backend/app.py` (Flask app)
- [ ] **T3.2** Implementar `web/backend/routes.py` (endpoints API)
- [ ] **T3.3** Implementar `web/backend/queries.py` (queries SQL parametrizadas)
- [ ] **T3.4** Tests unitarios del backend (pytest)

### Fase 4: Frontend (prioridad media)
- [ ] **T4.1** Crear `web/frontend/index.html` (estructura base)
- [ ] **T4.2** Implementar `web/frontend/js/api.js` (llamadas a API)
- [ ] **T4.3** Implementar `web/frontend/js/charts.js` (Chart.js)
- [ ] **T4.4** Implementar `web/frontend/css/styles.css` (estilos)

### Fase 5: Integración y entrega
- [x] **T5.1** Actualizar `orquestador.py` para nuevo flujo
- [x] **T5.2** Tests de integración (pipeline completo)
- [x] **T5.3** Documentación (README, instrucciones de ejecución)
- [ ] **T5.4** Merge a main
- [ ] **T5.5** Limpiar output del gemelo anterior (opcional)

## Progreso
- **Estado:** 🟢 Fase 5 en progreso (T5.3 completado)
- **Tarea actual:** T5.4 (Merge a main)
- **Siguiente:** T5.5 (Limpieza opcional)

## Decisiones de diseño
1. **Framework web:** Flask (más simple que FastAPI para MVP rápido)
2. **Frontend:** HTML vanilla + Chart.js (sin build tools, bajo riesgo)
3. **Parsing catálogo:** Leer markdown directamente (sin conversión a JSON)
4. **Estrategia de ramas:** 1 rama feature + merge a main al final
5. **Esquema SQLite:** 3 tablas principales (machines, simulations, measurements) + tablas auxiliares

## Arquitectura
```
docs/CATALOGO_EQUIPOS.md
    ↓
sim_catalog.m (parser)
    ↓
sim_engine.m (motor 8760h)
    ↓
sim_db.m (SQLite)
    ↓
web/backend/app.py (Flask API)
    ↓
web/frontend/index.html (Chart.js)
```

## Evidencia de commits
- (se actualizará con cada commit)

## Próximos pasos
1. Commitear archivos actuales en main
2. Crear rama feature/simulador-maquinaria
3. Diseñar esquema SQLite detallado
4. Implementar sim_catalog.m
