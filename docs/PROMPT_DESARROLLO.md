# Prompt para Sesión de Desarrollo — Implementación del Simulador

Copiar este prompt al iniciar una nueva sesión de OpenCode para la implementación del simulador de maquinaria industrial.

---

## Contexto del Proyecto

SPACEWISE AI está en transición de un gemelo digital de edificio a un **simulador de maquinaria industrial**. La decisión está tomada: **implementar el cambio**. El catálogo de 110 equipos ya está disponible en `docs/CATALOGO_EQUIPOS.md`.

### Documentos Clave

| Archivo | Propósito |
|---------|-----------|
| `docs/CATALOGO_EQUIPOS.md` | **110 equipos industriales** con especificaciones técnicas completas (leer primero) |
| `docs/SIMULADOR_MAQUINARIA.md` | Arquitectura propuesta, estructura de datos, requerimientos |
| `docs/Datos Equipos.pdf` | Fuente original de los datos (referencia) |

### Estado Actual del Repositorio

```
Siemens-Spacewise/
├── docs/
│   ├── CATALOGO_EQUIPOS.md        ← 110 equipos con datos técnicos completos
│   ├── SIMULADOR_MAQUINARIA.md    ← Arquitectura y requerimientos
│   └── archive/                   ← Proyecto anterior (gemelo de edificio)
├── matlab/                        ← Gemelo digital anterior (referencia, no usar)
│   ├── config/, src/, scripts/, tests/, output/
├── orquestador.py                 ← Orquestador Python (adaptar)
└── requirements.txt
```

### Decisiones Tomadas

- ✅ **Cambio de enfoque**: de gemelo de edificio a simulador de maquinaria industrial
- ✅ **Catálogo disponible**: 110 equipos en `docs/CATALOGO_EQUIPOS.md`
- ✅ **Base de datos**: SQLite (mantener)
- ✅ **Fecha límite concurso**: 23 de octubre de 2026

---

## Tu Misión

Implementar el simulador de maquinaria industrial según los requerimientos de `docs/SIMULADOR_MAQUINARIA.md`, usando los datos de `docs/CATALOGO_EQUIPOS.md`.

### Entregables

1. **Motor de simulación MATLAB** que lea el catálogo y genere perfiles de consumo horario (8760 horas)
2. **Arquitectura modular**: cada máquina = configuración independiente
3. **Persistencia SQLite**: esquema actualizado para simulación de máquinas
4. **Scripts de ejecución**: init, load_catalog, run_simulation, export_results
5. **Tests unitarios**: cobertura mínima 80% en lógica crítica
6. **Backend web Python** (Flask o FastAPI) para servir datos
7. **Frontend HTML** con panel de visualización (consumos totales, parciales, individuales)
8. **Import/Export**: CSV/Excel para comparación con datos reales

### Prioridades

1. **Motor de simulación funcional** con el catálogo de 110 equipos
2. **Persistencia SQLite** con esquema correcto
3. **Exportación de resultados** (CSV por rangos temporales)
4. **Panel web básico** (puede ser MVP simple)
5. **Importación de datos reales** (comparación)

---

## Metodología de Trabajo (ODD — Organic Driven Development)

### Flujo con Subagentes

1. **Exploración** → Delegar a subagente `explore` para mapear código desconocido
   - Readonly, nunca modifica archivos
   - Retorna handoff de ~2k tokens máximo
   - Usar antes de implementar para entender flujo

2. **Implementación** → Delegar a subagente `general` (writer)
   - Especificar "allowed edit surfaces" (archivos exactos que puede tocar)
   - Incluir contexto relevante en el prompt
   - Para 2+ archivos, delegación es obligatoria

3. **Verificación** → Delegar a subagente `general` (verifier)
   - Ejecutar tests después de cada cambio significativo
   - Verificar que no se rompió nada existente

### Selección de Modelo según Tarea

| Tarea | Modelo recomendado | Por qué |
|-------|-------------------|---------|
| Diseño arquitectónico | Modelo más potente | Decisiones de alto impacto |
| Lógica compleja del motor | Modelo potente | Correctitud crítica |
| Tests unitarios | Modelo medio | Patrones repetitivos |
| Tareas mecánicas (renames) | Modelo ligero | No requiere razonamiento |
| Exploración de código | Modelo medio | Búsqueda y resumen |
| Backend web | Modelo potente | Seguridad crítica |
| Frontend HTML | Modelo medio | Patrones establecidos |

### Criterios de Routing

- **Tarea simple** (1 archivo, <50 líneas): inline, no delegar
- **Tarea media** (2-3 archivos): 1 writer delegated
- **Tarea compleja** (4+ archivos): explorer → writer → verifier
- **Investigación**: explorer read-only, nunca escribir

---

## Seguridad (PRIORIDAD MÁXIMA)

### Código MATLAB

- No usar `eval()` con inputs dinámicos
- Validar archivos de configuración del catálogo
- Consultas parametrizadas en SQLite (no concatenar SQL)
- No exponer rutas absolutas en outputs
- Manejar `rng(seed)` para reproducibilidad

### Código Python (backend web)

- **SQL parametrizado SIEMPRE** (NUNCA concatenar SQL)
- Validar y sanitizar TODOS los inputs de usuario
- No exponer stack traces en producción
- CORS configurado explícitamente (no wildcard `*`)
- Rate limiting en endpoints
- CSRF protection si hay formularios
- No servir archivos estáticos desde fuera del directorio permitido
- Usar rutas relativas o configurables

### Base de Datos

- Prepared statements siempre
- Validar tipos de datos antes de insertar
- No almacenar secrets en la BD
- Backup antes de migraciones de schema
- Migraciones versionadas y reversibles

### Secrets y Credenciales

- `.env` en `.gitignore` (verificar)
- Nunca commitear API keys, tokens, contraseñas
- Variables de entorno para configuración sensible

---

## Normativas y Buenas Prácticas

### Commits

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Sin "Co-Authored-By" ni atribución AI
- Work-unit commits: cada commit atómico y funcional
- Tests y docs en el mismo commit que el código

### Testing

- **MATLAB**: `matlab.unittest.TestCase`, coverage mínimo 80%
- **Python**: pytest para backend, coverage 80%
- Tests determinísticos (usar seeds para random)
- Cada feature nueva debe incluir tests

### Documentación

- Docstrings en TODAS las funciones públicas
- README.md actualizado con instrucciones de ejecución
- Comentarios en español para dominio, inglés para lógica técnica
- Diagramas de arquitectura (Mermaid) cuando la complejidad lo justifique

### Código

- Nombres descriptivos, sin abreviaciones crípticas
- Funciones cortas (<50 líneas idealmente)
- Sin magic numbers: todo en constantes con nombre
- Error handling explícito, nunca `catch` vacío
- Logging estructurado (DEBUG, INFO, WARNING, ERROR)
- Type hints en Python para funciones públicas

### MATLAB Específico

- `classdef` con métodos `Static`
- Tests en `matlab/tests/` con `matlab.unittest.TestCase`
- No usar `clear all` en scripts de producción
- `addpath` solo al inicio de scripts
- Validar inputs en funciones públicas (nargin, tipos)

### Python Específico

- Type hints en funciones públicas
- `pathlib.Path` en vez de `os.path`
- `logging` module, no `print()`
- Try/except específico, nunca `except Exception` genérico sin logging
- Virtual environment (`.venv/` ya existe)

---

## Consideraciones de Arquitectura

### Motor de Simulación

- **Entrada**: catálogo de máquinas desde `docs/CATALOGO_EQUIPOS.md`
- **Procesamiento**: perfiles horarios 8760h, ciclos de trabajo, estacionalidad
- **Salida**: mediciones horarias por máquina, totales, eventos
- **Persistencia**: SQLite con esquema para máquinas, simulaciones, mediciones

### Panel Web

- **Backend**: Flask (simpler) o FastAPI (más moderno)
- **Frontend**: HTML + JavaScript vanilla + Chart.js (bajo riesgo)
- **Endpoints**: listar máquinas, obtener series temporales, totales, exportar
- **Seguridad**: autenticación básica si es necesario, validación de inputs

### Estructura de Archivos

```
Siemens-Spacewise/
├── docs/                          ← Documentación
├── matlab/
│   ├── config/
│   │   └── simulacion_params.m    ← Parámetros globales
│   ├── src/
│   │   ├── sim_engine.m           ← Motor de simulación
│   │   ├── sim_catalog.m          ← Carga catálogo desde .md
│   │   ├── sim_machine.m          ← Perfil de máquina individual
│   │   ├── sim_db.m               ← Capa SQLite
│   │   ├── sim_analysis.m         ← Análisis y agregación
│   │   └── sim_export.m           ← Exportación CSV/Excel
│   ├── scripts/
│   │   ├── init_db.m
│   │   ├── load_catalog.m
│   │   ├── run_simulation.m
│   │   └── export_results.m
│   └── tests/
├── web/
│   ├── backend/
│   │   ├── app.py                 ← Flask/FastAPI
│   │   ├── routes.py
│   │   └── queries.py
│   └── frontend/
│       ├── index.html
│       ├── js/
│       │   ├── charts.js
│       │   └── api.js
│       └── css/
├── data/
│   ├── spacewise.db               ← Base de datos SQLite
│   ├── import/                    ← CSV/Excel importados
│   └── export/                    ← Resultados exportados
└── orquestador.py                 ← Actualizar para nuevo flujo
```

---

## Reglas de Oro

1. **Leer `docs/CATALOGO_EQUIPOS.md` primero**: contiene los datos de los 110 equipos
2. **No romper lo que funciona**: si hay tests pasando, deben seguir pasando
3. **Commits pequeños y frecuentes**: facilita review y rollback
4. **Documentar decisiones**: si tomás una decisión de diseño, comentala
5. **Preguntar antes de asumir**: si hay ambigüedad, preguntar al usuario
6. **Seguridad primero**: ante duda, elegir la opción más conservadora
7. **Validar con tests**: cada cambio significativo debe tener tests
8. **Performance consciente**: medir antes de optimizar
9. **Accesibilidad web**: WCAG 2.1 nivel AA mínimo
10. **Usar el catálogo**: los datos de las máquinas ya están en `docs/CATALOGO_EQUIPOS.md`

---

## Primeros Pasos

1. Leer `docs/CATALOGO_EQUIPOS.md` completo (110 equipos)
2. Leer `docs/SIMULADOR_MAQUINARIA.md` para entender la arquitectura
3. Explorar `matlab/` para ver qué se puede reutilizar del gemelo anterior
4. Diseñar el esquema de base de datos para simulación de máquinas
5. Implementar `sim_catalog.m` que lea el catálogo desde markdown
6. Implementar `sim_engine.m` que genere perfiles horarios
7. Implementar persistencia SQLite
8. Crear scripts de ejecución
9. Implementar backend web (Flask/FastAPI)
10. Crear panel HTML básico
11. Agregar exportación CSV
12. Implementar importación de datos reales (comparación)

---

## Recursos

- `docs/CATALOGO_EQUIPOS.md` — 110 equipos con datos técnicos completos
- `docs/SIMULADOR_MAQUINARIA.md` — Arquitectura y requerimientos
- `docs/README.md` — Índice de documentación
- `docs/archive/` — Proyecto anterior (gemelo de edificio, referencia)
- `matlab/` — Gemelo anterior (puede servir de referencia para estructura)

---

**Nota**: Este prompt asume que la nueva sesión no tiene contexto previo. El catálogo de equipos ya está listo en `docs/CATALOGO_EQUIPOS.md`. La tarea es implementar el simulador según esa base.
