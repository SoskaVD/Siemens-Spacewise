# Documentación — SPACEWISE AI

## Estado Actual

**Decisión tomada**: implementar el simulador de maquinaria industrial. La fuente en tiempo de ejecución del catálogo son los módulos `machines/<CODE>/machine.json` (ver `machines/_TEMPLATE/_README.md` en la raíz del repo); `CATALOGO_EQUIPOS.md` queda como referencia histórica de datos y entrada única de la migración `matlab/scripts/migrate_catalog.m`. El sistema compara la simulación contra mediciones reales importadas por CSV (sección "Simulado vs Real" del dashboard). Fecha límite del concurso: 23 de octubre de 2026.

## Estructura

```
docs/
├── README.md                      ← Este archivo
├── CATALOGO_EQUIPOS.md            ← 110 equipos industriales (referencia histórica de datos)
├── SIMULADOR_MAQUINARIA.md        ← Documento de planificación original (pre-implementación)
├── archive/                       ← Documentación del proyecto anterior
│   ├── PLAN_GEMELO_DIGITAL.md
│   ├── SPACEWISE_AI_Presentacion.md
│   └── SPACEWISE_AI_Report.md
├── Datos Equipos.pdf              ← Fuente original de los datos (Gemini Deep Research)
└── *.pdf                          ← Referencias del concurso Siemens
```

## Documentos Vigentes

| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `../README.md` (raíz) | Documentación operativa actual: módulos, API, import/compare y **lazo cerrado del gemelo** (feed, estado, calibración) | ✅ Vigente |
| `../machines/_TEMPLATE/_README.md` | Plantilla para definir nueva maquinaria (+ reglas de calibración `_calibration`/`.bak`) | ✅ Vigente |
| `../plant/` | Mundo físico simulado: planta sintética, runner de ingesta y demo de lazo cerrado (sin hardware) | ✅ Vigente |
| `CATALOGO_EQUIPOS.md` | **110 equipos industriales** con especificaciones completas (solo referencia; ya no se parsea en runtime) | 📚 Referencia |
| `SIMULADOR_MAQUINARIA.md` | Planificación original del simulador (decisiones y preguntas de la fase de diseño) | 📚 Histórico de diseño |

## Referencias del Concurso

| Archivo | Descripción |
|---------|-------------|
| `Bases y condiciones VF 2026 RFQ.pdf` | Bases oficiales del concurso |
| `Grupo 3 Directrices Proyecto Siemens SPACE WISE AI.pdf` | Directrices técnicas del proyecto |
| `PROYECTOS PROPUESTOS SIEMENS 23062026.pdf` | Propuestas iniciales del proyecto |
| `Datos Equipos.pdf` | Fuente original de los 110 equipos (Gemini Deep Research) |

## Archivo Histórico (`archive/`)

Documentación del proyecto anterior (gemelo digital de edificio). Se mantiene como referencia pero **no representa el enfoque actual**.

| Archivo | Descripción |
|---------|-------------|
| `PLAN_GEMELO_DIGITAL.md` | Plan técnico del gemelo de edificio |
| `SPACEWISE_AI_Presentacion.md` | Presentación del proyecto anterior |
| `SPACEWISE_AI_Report.md` | Informe extenso del proyecto anterior |

## Fechas Clave del Concurso

- **23 de octubre de 2026**: Entrega de proyectos
- **Noviembre 2026**: Presentaciones
- **20 de noviembre de 2026**: Aviso de finalistas
