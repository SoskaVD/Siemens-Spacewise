# Simulador de Maquinaria Industrial — Nuevo Enfoque del Proyecto

> **ℹ️ Estado del documento (2026-10-23):** este es el documento de **planificación original** (fase de diseño). La implementación evoluciona y superó varias suposiciones: el pipeline CEN legado (`dt_*`) fue eliminado del repo, `sim_db.m` es independiente, y el catálogo ya no se parsea desde este markdown en runtime sino desde módulos `machines/<CODE>/machine.json` con autodescubrimiento por carpeta. Para el estado operativo actual ver [`README.md`](../README.md) y la guía de la plantilla en [`machines/_TEMPLATE/_README.md`](../machines/_TEMPLATE/_README.md).

**Fecha:** 2026-10-11
**Estado:** Planificación completa, datos listos para implementación (histórico)
**Contexto:** Cambio de enfoque debido a falta de participación del CEN (Centro Espacial Nacional)

> **📋 Catálogo disponible**: El catálogo de **110 equipos industriales** con especificaciones técnicas completas está en [`CATALOGO_EQUIPOS.md`](./CATALOGO_EQUIPOS.md). Este archivo contiene todos los datos necesarios para la implementación del simulador.

---

## 1. Cambio de Enfoque

### Proyecto Original
Gemelo digital energético de un edificio (12,000 m², 6 subsistemas, 22 dispositivos) con:
- Modelo matemático de perfiles por subsistema (HVAC, laboratorios, IT, iluminación, bombas, auxiliares)
- Escenarios E0-E5 basados en control de edificio
- Base de datos SQLite poblada con simulaciones
- Gráficos y exportación CSV

### Nuevo Objetivo
**Simulador y comparador de maquinaria industrial** para centros de investigación y entornos industriales:
- Simular comportamiento y consumo de al menos 100 máquinas individuales
- Arquitectura modular (cada máquina = configuración independiente)
- Panel HTML para visualizar consumos totales, parciales e individuales
- Comparación con datos reales (importación CSV/Excel)
- Exportación por rangos temporales

---

## 2. Requerimientos Específicos

### 2.1 Arquitectura
- [ ] **Estructura modular**: Cada carpeta de simulación representa una máquina o equipo
- [ ] **Biblioteca de máquinas**: Al menos 100 equipos con perfiles de consumo realistas
- [ ] **Configuración por máquina**: Archivos de definición con especificaciones técnicas y comportamiento

### 2.2 Simulación
- [ ] **Motor de simulación**: Generar consumo horario basado en perfiles de máquinas
- [ ] **Ciclos de trabajo**: Modelar estados operativos (arranque, operación, standby, apagado)
- [ ] **Variabilidad**: Considerar factores estacionales y operacionales
- [ ] **Conservación de energía**: Suma de consumos individuales = consumo total

### 2.3 Persistencia
- [ ] **Base de datos local**: SQLite para almacenar simulaciones y resultados
- [ ] **Esquema flexible**: Permitir agregar nuevas máquinas sin modificar estructura
- [ ] **Metadatos**: Versiones de simulación, parámetros, timestamps

### 2.4 Panel HTML
- [ ] **Consumos totales**: Suma de todas las máquinas
- [ ] **Consumos parciales**: Selección de máquinas para sumar
- [ ] **Consumos individuales**: Gráficos por máquina
- [ ] **Vistas temporales**: Gráficos en tiempo (serie temporal)
- [ ] **Vistas comparativas**: Comparar máquinas, períodos, escenarios

### 2.5 Importación/Exportación
- [ ] **Importar datos reales**: Archivos .xlsx o .csv para comparación
- [ ] **Exportar simulaciones**: Por rangos temporales (1 día, 1 semana, 1 mes, 1 año, personalizado)
- [ ] **Formatos estándar**: CSV, Excel, posiblemente JSON

---

## 3. Estructura de Datos Requerida por Máquina

### 3.1 Identificación
```
codigo:          Identificador único (formato: CATEGORIA-XXX)
nombre:          Nombre descriptivo del equipo
categoria:       Tipo de equipo (HVAC, compresor, motor, bomba, etc.)
fabricante:      Fabricante y modelo representativo
```

### 3.2 Especificaciones Eléctricas
```
potencia_nominal_kw:    Potencia nominal en kilowatts
voltaje_nominal_v:      Voltaje nominal (230 monofásico o 400 trifásico)
corriente_nominal_a:    Corriente nominal en amperes
factor_potencia:        Factor de potencia nominal (0.80-0.99)
fases:                  Número de fases (1 o 3)
thd_nominal_pct:        Distorsión armónica total esperada (%)
```

### 3.3 Perfil de Consumo
```
horas_operacion_dia:       Horas de operación típicas por día
dias_operacion_semana:     Días de operación por semana (1-7)
factor_carga_promedio:     Factor de carga promedio (0-1)
variabilidad_estacional:   Descripción de variación anual
ciclos_trabajo:            Estructura de estados operativos:
  - arranque:   {duracion_seg, consumo_multiplo}
  - operacion:  {factor_carga, duracion_horas}
  - standby:    {factor_consumo, duracion_horas}
  - apagado:    {consumo_cero}
```

### 3.4 Comportamiento Dinámico
```
tiempo_arranque_seg:    Tiempo típico de arranque
consumo_arranque_mult:  Múltiplo de consumo durante arranque (ej: 6x)
consumo_standby_pct:    Porcentaje de consumo en standby
flexibilidad:           Booleano - ¿se puede desplazar a otros horarios?
```

### 3.5 Contexto Operativo
```
aplicacion:         Descripción de uso típico
criticidad:         CRITICA | ESENCIAL | FLEXIBLE | NO_CRITICA
dependencias:       Otras máquinas requeridas para operar
condiciones_amb:    Factores ambientales que afectan consumo
```

---

## 4. Categorías de Equipos (Distribución Sugerida)

| Categoría | Cantidad | Ejemplos |
|-----------|----------|----------|
| HVAC industrial | 20 | Chillers, cooling towers, fan coils, AHUs, VRF, precision cooling |
| Compresores y neumática | 15 | Tornillo, pistón, centrífugos, sistemas de vacío |
| Motores eléctricos | 20 | AC/DC 0.75kW-500kW, con/sin variador |
| Bombas y sistemas hidráulicos | 15 | Centrífugas, desplazamiento positivo, presurización |
| Iluminación industrial | 10 | LED industrial, fluorescente, vapor de sodio |
| Laboratorios y equipos de prueba | 10 | Cámaras climáticas, bancos de carga, hornos |
| Equipos de manufactura | 10 | CNC, soldadoras, prensas, inyección |
| Servidores y TI | 5 | Racks, UPS, refrigeración data center |
| Equipos auxiliares | 5 | Ascensores, transportadores, ventilación |
| **Total** | **100** | |

---

## 5. Estructura de Archivos Propuesta

```
Siemens-Spacewise/
├── docs/                          → Documentación
│   ├── SIMULADOR_MAQUINARIA.md    → Este documento
│   └── catalogo_maquinas/         → Definiciones de máquinas
│       ├── HVAC/
│       │   ├── HVAC-001.md
│       │   └── ...
│       ├── compresores/
│       ├── motores/
│       └── ...
├── matlab/
│   ├── config/
│   │   └── simulacion_params.m    → Parámetros globales de simulación
│   ├── src/
│   │   ├── sim_engine.m           → Motor de simulación de máquinas
│   │   ├── sim_machine.m          → Clase/base de máquina individual
│   │   ├── sim_catalog.m          → Carga catálogo de máquinas
│   │   ├── sim_db.m               → Capa SQLite (reutilizar dt_db.m)
│   │   ├── sim_analysis.m         → Análisis y agregación
│   │   └── sim_export.m           → Exportación de resultados
│   ├── scripts/
│   │   ├── init_db.m              → Inicializar base de datos
│   │   ├── load_catalog.m         → Cargar catálogo de máquinas
│   │   ├── run_simulation.m       → Ejecutar simulación completa
│   │   └── export_results.m       → Exportar resultados
│   └── tests/
│       ├── test_sim_engine.m
│       ├── test_sim_machine.m
│       └── ...
├── web/                           → Panel HTML (nuevo)
│   ├── backend/
│   │   ├── app.py                 → Flask/FastAPI
│   │   ├── routes.py
│   │   └── queries.py
│   └── frontend/
│       ├── index.html
│       ├── js/
│       │   ├── charts.js
│       │   ├── selectors.js
│       │   └── api.js
│       └── css/
├── data/
│   ├── spacewise.db               → Base de datos SQLite
│   ├── import/                    → Archivos CSV/Excel importados
│   └── export/                    → Resultados exportados
└── orquestador.py                 → Orquestador Python (actualizar)
```

---

## 6. Formato de Salida para Informe

El informe que se solicitará a Claude debe incluir:

### 6.1 Secciones del Informe
1. **Resumen ejecutivo**: Estado actual, cambio de enfoque, próximos pasos
2. **Análisis de factibilidad**: Qué se puede reutilizar, qué hay que reescribir
3. **Arquitectura técnica**: Diagramas de componentes, flujo de datos
4. **Plan de implementación**: Fases, tareas, estimaciones de tiempo
5. **Riesgos y mitigaciones**: Identificación de problemas potenciales
6. **Recomendaciones**: Estrategia sugerida para el concurso

### 6.2 Preguntas Clave a Responder
- ¿Es viable hacer el cambio completo en 12 días?
- ¿Qué componentes del gemelo actual se pueden reutilizar?
- ¿Cuál es la complejidad real de cada requerimiento?
- ¿Qué tecnologías son más adecuadas para el panel HTML?
- ¿Cómo presentar el proyecto en el concurso si no se completa el cambio?
- ¿Cuál es el MVP (producto mínimo viable) para la fecha de entrega?

### 6.3 Criterios de Evaluación del Concurso
| Criterio | Puntaje |
|----------|---------|
| Nivel de innovación | 25 |
| Uso efectivo de IA | 25 |
| Impacto y escalabilidad | 20 |
| Viabilidad técnica y económica | 15 |
| Presentación y demostración | 15 |

---

## 7. Restricciones y Consideraciones

### 7.1 Tiempo
- **Fecha límite concurso**: 23 de octubre de 2026 (entrega de proyectos)
- **Días disponibles**: ~12 días desde hoy
- **Presentaciones**: Noviembre 2026

### 7.2 Equipo
- Vicente (autor principal)
- Javier (colaborador)
- Experiencia: MATLAB, Python básico
- Sin experiencia en desarrollo web frontend/backend

### 7.3 Datos
- **Catálogo disponible**: `docs/CATALOGO_EQUIPOS.md` con 110 equipos industriales (fuente: Gemini Deep Research, validado)
- Datos basados en especificaciones técnicas públicas de fabricantes reales
- El sistema debe estar diseñado para calibrarse con mediciones reales en fase 2

### 7.4 Tecnología
- MATLAB para motor de simulación
- Python para orquestador y backend web
- SQLite para persistencia
- HTML/JavaScript para panel (tecnologías a definir)

---

## 8. Búsqueda de Información (Gemini Deep Research) — ✅ Completado

La búsqueda se ejecutó y los resultados están en **`docs/CATALOGO_EQUIPOS.md`** (110 equipos, 9 categorías, tabla resumen CSV incluida).

El prompt original usado fue:

````
# Objetivo

Necesito información técnica detallada sobre 100 equipos industriales y de centros
de investigación para construir un simulador de consumo energético. Los datos deben
ser realistas y coherentes entre sí, permitiendo simular el comportamiento de consumo
horario de cada equipo a lo largo de un año.

# Categorías de equipos (distribución sugerida)

Buscá equipos que cubran estas categorías, con cantidades aproximadas:

**HVAC industrial (20 equipos)**
- Chillers, cooling towers, fan coils, AHUs, VRF, precision cooling

**Compresores y neumática (15 equipos)**
- Compresores de tornillo, pistón, centrífugos, sistemas de vacío

**Motores eléctricos (20 equipos)**
- Motores AC/DC de diversas potencias (0.75kW a 500kW), con/sin variador

**Bombas y sistemas hidráulicos (15 equipos)**
- Bombas centrífugas, de desplazamiento positivo, sistemas de presurización

**Iluminación industrial (10 equipos)**
- LED industrial, fluorescente, vapor de sodio, iluminación de precisión

**Laboratorios y equipos de prueba (10 equipos)**
- Cámaras climáticas, bancos de carga, equipos de medición, hornos de laboratorio

**Equipos de manufactura (10 equipos)**
- CNC, soldadoras, prensas, máquinas de inyección

**Servidores y TI (5 equipos)**
- Racks de servidores, UPS, sistemas de refrigeración de data center

**Equipos auxiliares (5 equipos)**
- Ascensores, transportadores, sistemas de ventilación

# Datos técnicos requeridos por equipo

Para cada equipo necesito:

1. **Identificación**
   - Código (formato: CATEGORIA-XXX, ej: HVAC-001)
   - Nombre descriptivo
   - Fabricante y modelo representativo (puede ser genérico)
   - Categoría

2. **Especificaciones eléctricas**
   - Potencia nominal (kW)
   - Voltaje nominal (V): 230 monofásico o 400 trifásico
   - Corriente nominal (A)
   - Factor de potencia nominal
   - Fases (1 o 3)
   - THD esperado (%)

3. **Perfil de consumo**
   - Horas de operación típicas por día
   - Días de operación por semana
   - Factor de carga promedio (0-1)
   - Variabilidad estacional
   - Ciclos de trabajo: estados (arranque, operación plena, standby, apagado)
   - Fracción de tiempo en cada estado

4. **Comportamiento dinámico**
   - Tiempo típico de arranque (segundos/minutos)
   - Consumo durante arranque (múltiplo de nominal)
   - Consumo en standby (% de nominal)
   - ¿Es carga flexible?

5. **Contexto operativo**
   - Aplicación típica
   - Criticidad (CRITICA / ESENCIAL / FLEXIBLE / NO_CRITICA)
   - Dependencias
   - Condiciones ambientales que afectan consumo

# Formato de entrega

Entregá la información en formato Markdown con:
1. Introducción metodológica (2-3 párrafos)
2. Los 100 equipos detallados individualmente con tablas estructuradas
3. Tabla resumen consolidada en formato CSV-like
4. Bibliografía/fuentes consultadas

# Restricciones

- Datos realistas y coherentes
- Valores típicos de la industria, no números inventados
- Si no hay datos exactos, usar valores representativos y aclararlo
- Priorizar equipos comunes, no ultra-especializados
````

---

## 9. Informe Estructurado (Claude) — ✅ Completado

El análisis de factibilidad se realizó y la decisión tomada es **implementar el simulador**. El prompt de implementación actualizado está en **`docs/PROMPT_DESARROLLO.md`**.

El prompt original de análisis fue:

````
# Contexto

Adjunto el documento `SIMULADOR_MAQUINARIA.md` que describe el nuevo enfoque del proyecto SPACEWISE AI. También adjunto el archivo con los 100 equipos industriales obtenido de una investigación previa.

# Tarea

Generá un informe técnico estructurado que evalúe la factibilidad de este cambio de enfoque y proponga un plan de implementación concreto.

# Secciones requeridas del informe

1. **Resumen ejecutivo** (1 página)
   - Estado actual del proyecto
   - Naturaleza del cambio propuesto
   - Recomendación clara: proceder/pausar/pivotar

2. **Análisis de factibilidad**
   - Componentes reutilizables del gemelo actual
   - Componentes que requieren reescritura
   - Nuevos componentes a desarrollar
   - Complejidad estimada por componente (baja/media/alta)

3. **Arquitectura técnica propuesta**
   - Diagrama de componentes
   - Flujo de datos
   - Decisiones tecnológicas recomendadas (con justificación)

4. **Plan de implementación**
   - Fases con entregables concretos
   - Estimación de tiempo por fase
   - Dependencias entre tareas
   - MVP para fecha de entrega del concurso

5. **Análisis de riesgos**
   - Riesgos técnicos
   - Riesgos de plazo
   - Riesgos de calidad
   - Estrategias de mitigación

6. **Estrategia de presentación para el concurso**
   - Qué mostrar si no se completa el cambio
   - Cómo enmarcar el proyecto para maximizar puntaje
   - Demo en vivo: qué es viable mostrar

# Preguntas específicas a responder

- ¿Es realista hacer el cambio completo en el tiempo disponible?
- ¿Cuál es el MVP más impactante para la fecha de entrega?
- ¿Qué tecnologías minimizan el riesgo dado que no hay experiencia en web?
- ¿Cómo mantener coherencia narrativa con lo ya presentado?
- ¿Qué hacer con el gemelo digital ya desarrollado?

# Restricciones

- El informe debe ser práctico y accionable, no teórico
- Considerar que el equipo no tiene experiencia en desarrollo web
- Priorizar viabilidad sobre perfección
- El concurso se evalúa el 23 de octubre de 2026

# Criterios de evaluación del concurso (para contextualizar recomendaciones)

| Criterio | Puntaje |
|----------|---------|
| Nivel de innovación | 25 |
| Uso efectivo de IA | 25 |
| Impacto y escalabilidad | 20 |
| Viabilidad técnica y económica | 15 |
| Presentación y demostración | 15 |
````

---

## 10. Próximos Pasos

1. ~~**Ejecutar búsqueda de información** con el prompt de la Sección 8 (Gemini Deep Research)~~ ✅ Hecho → `docs/CATALOGO_EQUIPOS.md`
2. ~~**Revisar y validar** los equipos obtenidos~~ ✅ Hecho (110 equipos validados, MOT-010 corregido)
3. ~~**Solicitar informe estructurado a Claude** con el prompt de la Sección 9~~ ✅ Hecho
4. ~~**Tomar decisión final**: ¿Hacer el cambio completo o mantener gemelo actual?~~ ✅ Decisión: implementar simulador
5. **Ejecutar `docs/PROMPT_DESARROLLO.md`** en nueva sesión de OpenCode para implementación

---

## 11. Referencias

- **Catálogo de equipos**: `docs/CATALOGO_EQUIPOS.md` (110 equipos industriales)
- **Prompt de implementación**: `docs/PROMPT_DESARROLLO.md`
- Documento original del gemelo: `docs/archive/PLAN_GEMELO_DIGITAL.md`
- Presentación del proyecto: `docs/archive/SPACEWISE_AI_Presentacion.md`
- Directrices Siemens: `docs/Grupo 3 Directrices Proyecto Siemens SPACE WISE AI.pdf`
- Bases del concurso: `docs/Bases y condiciones VF 2026 RFQ.pdf`

---

**Autor:** Vicente
**Revisión:** Pendiente
