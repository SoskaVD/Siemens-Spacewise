# Documentación — SPACEWISE AI

## Estado Actual

**Sistema vigente**: simulador y gemelo digital de maquinaria industrial. La
fuente en tiempo de ejecución del catálogo son los módulos
`machines/<CODE>/machine.json` (una carpeta = una máquina; ver
[`../machines/_TEMPLATE/_README.md`](../machines/_TEMPLATE/_README.md));
`CATALOGO_EQUIPOS.md` queda como referencia histórica de datos y entrada única
de la migración `matlab/scripts/migrate_catalog.m`. El sistema compara la
simulación contra mediciones reales (CSV o feed continuo), estima el estado
actual por máquina y **recalibra el modelo desde los datos** (lazo cerrado del
gemelo: secciones *Simulado vs Real* y *Gemelo* del dashboard).

## Estructura

```
docs/
├── README.md                      ← Este archivo (índice)
├── CATALOGO_EQUIPOS.md            ← 110 equipos industriales (referencia histórica de datos)
├── SIMULADOR_MAQUINARIA.md        ← Arquitectura técnica y decisiones del sistema
├── Datos Equipos.pdf              ← Fuente original de los datos (Gemini Deep Research)
└── *.pdf                          ← Referencias del concurso Siemens
```

## Documentos Vigentes

| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `../README.md` (raíz) | Documentación operativa: estructura, configuración, uso, **API completa** (shadow + lazo cerrado) y testing | ✅ Vigente |
| `SIMULADOR_MAQUINARIA.md` | Arquitectura por capas, contratos (catálogo 26 columnas, códigos, estados), motor, lazo del gemelo, métricas y decisiones registradas | ✅ Vigente |
| `../machines/_TEMPLATE/_README.md` | Plantilla para definir nueva maquinaria (+ reglas de calibración `_calibration`/`.bak`) | ✅ Vigente |
| `../plant/` | Mundo físico simulado: planta sintética, runner de ingesta y demo de lazo cerrado (desarrollo/demo sin hardware) | ✅ Vigente |
| `../.env.example` | Todas las variables de configuración con sus valores por defecto | ✅ Vigente |
| `CATALOGO_EQUIPOS.md` | **110 equipos industriales** con especificaciones completas (solo referencia; ya no se parsea en runtime) | 📚 Referencia |

## Referencias del Concurso

| Archivo | Descripción |
|---------|-------------|
| `Bases y condiciones VF 2026 RFQ.pdf` | Bases oficiales del concurso |
| `Grupo 3 Directrices Proyecto Siemens SPACE WISE AI.pdf` | Directrices técnicas del proyecto |
| `PROYECTOS PROPUESTOS SIEMENS 23062026.pdf` | Propuestas iniciales del proyecto |
| `Datos Equipos.pdf` | Fuente original de los 110 equipos (Gemini Deep Research) |

## Fechas Clave del Concurso

- **23 de octubre de 2026**: Entrega de proyectos
- **Noviembre 2026**: Presentaciones
- **20 de noviembre de 2026**: Aviso de finalistas
