# SPACEWISE AI — Gemelo Digital Energético Inteligente

## 1. Introducción

### 1.1 Contexto del Proyecto

**SPACEWISE AI** se enmarca en el **"Concurso Interuniversitario de Innovación 2026"** organizado por el **Centro Nacional de Investigación y Desarrollo Aeroespacial (CEN)**, en colaboración con la **Universidad Técnica Federico Santa María (UTFSM)**, la **Universidad de Chile (UCHILE)**, la **Universidad de Santiago de Chile (USACH)** y **SIEMENS**.

El concurso busca fomentar el desarrollo de soluciones innovadoras en tres líneas: satélites, carga útil (payload) e inteligencia artificial. SPACEWISE AI compite en la **Línea 3: Inteligencia Artificial**, cuyo objetivo es aplicar IA para optimizar la operación, mantenimiento y/o uso de recursos dentro de las instalaciones del CEN, mejorando la eficiencia, reduciendo costos y aumentando la autonomía de los sistemas.

### 1.2 Objetivo General

> Diseñar, simular y validar un sistema inteligente de gestión energética para el Centro Espacial Nacional de Chile, integrando medición eléctrica Siemens, IA predictiva, gemelo digital y control operacional para reducir el consumo eléctrico anual entre **20% y 30%**, manteniendo continuidad operacional, confort térmico y seguridad energética.

### 1.3 Objetivos Específicos

1. Caracterizar los perfiles energéticos del edificio y desarrollar un modelo digital del comportamiento energético (gemelo digital).
2. Implementar IA para predicción de demanda.
3. Optimizar HVAC, iluminación y laboratorios.
4. Medir reducción de huella de carbono.
5. Proponer una estrategia de control automático con IA.

---

## 2. Problema Detectado

### 2.1 El Problema

El consumo energético en centros de investigación como el CEN es elevado, variable y difícil de gestionar de forma eficiente. Los edificios de este tipo combinan laboratorios especializados, oficinas administrativas, áreas comunes y equipamiento crítico que operates 24/7, generando perfiles de consumo heterogéneos que no se adaptan a estrategias de ahorro convencionales.

La problemática central se resume en:

- **Falta de visibilidad** sobre el consumo real por zona, equipo y franja horaria.
- **Ausencia de modelos predictivos** que permitan anticipar la demanda y ajustar la operación.
- **Desaprovechamiento de fuentes de energía renovable** (fotovoltaica) que no se integran de forma inteligente al mix energético.
- **Control manual o estático** de HVAC e iluminación, sin adaptación a condiciones reales de ocupación y clima.
- **Sin medición de impacto ambiental** que permita cuantificar la huella de carbono y las mejoras logradas.

### 2.2 Relevancia para el CEN

El Centro Espacial Nacional es la infraestructura más avanzada de Chile para investigación aeroespacial. Su operación requiere condiciones térmicas, de iluminación y de energía estables, pero también enfrenta la presión de reducir costos operativos y su huella de carbono. Un sistema inteligente de gestión energética que funcione como piloto en el CEN puede replicarse en otras infraestructuras similares: universidades, laboratorios, centros tecnológicos.

---

## 3. Solución Propuesta

### 3.1 Descripción General

SPACEWISE AI propone un **gemelo digital energético** — un modelo virtual del comportamiento energético del edificio — alimentado por datos reales de sensores Siemens, que utiliza algoritmos de inteligencia artificial para:

- **Monitorear** el consumo eléctrico en tiempo real por zona y equipo.
- **Predecir** la demanda energética futura usando modelos de machine learning.
- **Optimizar** el consumo de HVAC, iluminación y equipamiento de laboratorios.
- **Comparar** el comportamiento simulado contra datos reales para detectar desviaciones y oportunidades de ahorro.
- **Controlar** automáticamente los sistemas para maximizar el ahorro sin comprometer confort ni seguridad.

### 3.2 Componentes del Sistema

| Componente | Descripción |
|---|---|
| **Medición eléctrica Siemens** | Sensores y medidores instalados en tableros eléctricos para capturar datos de consumo en tiempo real (corriente, voltaje, potencia, energía). |
| **Gemelo Digital** | Modelo de simulación del comportamiento energético del edificio, calibrado con datos reales. Permite probar escenarios de ahorro sin riesgo. |
| **IA Predictiva** | Algoritmos de ML entrenados con datos históricos y en tiempo real para predecir demanda, detectar anomalías y sugerir ajustes. |
| **Dashboard de Visualización** | Interfaz que muestra resultados de consumo, ahorro, proyecciones y alertas. (Nota del equipo: preferencia por un dashboard funcional, no solo estético.) |
| **Control Automático** | Estrategia de control con IA que ajusta HVAC, iluminación y equipos según predicción de demanda, ocupación y tarifas. |
| **Integración de Renovables** | Modelo que considera fuentes de energía propia (paneles fotovoltaicos) como parte del mix energético optimizado. |

### 3.3 Enfoque y Alcance

- **Enfoque**: orientado a centros de investigación (CEN como caso de prueba), con potencial de replicabilidad en universidades, laboratorios y escuelas.
- **No competir con otros proyectos**: SPACEWISE AI se enfoca en la gestión energética, no en satélites ni payloads.
- **Gemelo digital**: simulación para comparación y variación de datos reales, no un modelo 3D decorativo.
- **IA**: usada para comparar, interpretar resultados y proyectar escenarios. El uso real se basa en algoritmos de ML.

---

## 4. Alternativas de Solución Consideradas

Durante el proceso de diseño del proyecto, el equipo discutió y evaluó diversas alternativas:

| Alternativa | Decisión | Justificación |
|---|---|---|
| Medición desde tableros eléctricos vs. sensores puntuales | **Tableros** | Medir desde el tablero eléctrico con salida modular por cada diferencial o automático permite cobertura completa y escalabilidad. |
| Modelo en nube vs. local | **Por definir** | Se evalúa eficiencia del modelo vs. producto. Dependencia de internet y latencia son factores críticos. |
| IA general vs. ML específico | **ML específico** | IA para interpretar datos y factores, no como solución genérica. Algoritmos de ML entrenados para predicción y optimización. |
| Dashboard estético vs. funcional | **Funcional** | Priorizar resultados claros sobre visualización elaborada. |
| Solo medición vs. medición + control | **Medición + control** | No basta con medir; el sistema debe poder actuar sobre los equipos para optimizar el consumo. |
| IA para catalogar consumo por zona | **Incorporado** | Que la IA pueda identificar qué tipo de consumo corresponde a cada zona (cocina, laboratorios, oficinas) y definir rangos óptimos. |

---

## 5. Ideas y Discusiones del Equipo

Las siguientes ideas surgieron de las sesiones de brainstorming y reuniones del equipo, registradas en las notas de proyecto:

### 5.1 Ideas de Vicente

- **Medición modular**: partir desde los tableros eléctricos, con salida modular por cada diferencial o automático. Esto permite granularidad y escalabilidad.
- **IA para catalogar consumo**: usar IA para que el sistema pueda identificar y catalogar el tipo de consumo por zona (ej: cocina, refrigerador, microondas), y en base a eso definir rangos esperados u óptimos de consumo.
- **Dashboard funcional**: priorizar resultados sobre estética. "Lo odio" — el dashboard debe ser útil, no bonito.

### 5.2 Ideas de Javier

- **Entorno virtual con IoT**: el gemelo digital como entorno virtual que integra monitoreo y simulación de consumos, con control y monitoreo remoto inalámbrico.
- **Sensores + simulación**: con sensores se monitorea el consumo real, y esos datos alimentan la simulación para hacer predicciones.
- **Optimización parametrizada**: un código comparador que se considere IA, que optimice el uso de energía parametrizándolo y que designe cuánta energía va a cada parte con sus debidos protocolos.

### 5.3 Discusiones de las Reuniones

**Reunión 29 de julio — Enfoque, IA, GD, Ahorro:**

- ¿El ahorro esperado es 20% o 30%? Se planteó utilizar fuentes de energía propia (renovables) como complemento.
- Uso de sensores de medición, incluyendo **sensores de presencia** para detectar ocupación.
- **Iluminación regulable** mediante potenciómetros para ajuste fino.
- El gemelo digital es la simulación para comparación y variación de datos reales.
- El uso de IA es para comparar, interpretar resultados y hacer proyecciones. El uso real se basa en algoritmos de ML.

**Reunión 03 de agosto (reunión propia):**

- El gemelo digital base ya está funcionando de forma modular, permitiendo añadir más dispositivos y mediciones.
- Falta obtener datos reales para comparar y calibrar el modelo.
- Ideas futuras: añadir más fuentes de energía al modelo.

**Preguntas pendientes para el CEN:**

- Ver componentes eléctricos del edificio.
- Conocer las corrientes y configuraciones (monofásico/multifásico).
- Materiales disponibles y costos/presupuesto.

---

## 6. Resultados Esperados

### 6.1 Impacto Cuantificable

| Métrica | Meta |
|---|---|
| Reducción de consumo eléctrico anual | 20% a 30% |
| Reducción de huella de carbono | Medible vía dashboard |
| Precisión de predicción de demanda | >85% (estimado) |
| Tiempo de respuesta del control automático | <5 segundos |

### 6.2 Entregables del Proyecto

1. **Gemelo digital funcional** del comportamiento energético del CEN, calibrado con datos reales.
2. **Modelo de IA** para predicción de demanda y optimización de consumo.
3. **Dashboard de visualización** con métricas de consumo, ahorro, proyecciones y alertas.
4. **Estrategia de control automático** con IA para HVAC, iluminación y laboratorios.
5. **Informe de impacto** con medición de reducción de huella de carbono.
6. **Documento técnico y presentación** para el concurso.

### 6.3 Replicabilidad

El sistema está diseñado para ser modular y replicable. El CEN funciona como caso de prueba, pero la solución puede adaptarse a:

- Universidades y centros de formación técnica.
- Laboratorios de investigación.
- Edificios corporativos con perfiles de consumo similares.
- Infraestructura industrial liviana.

---

## 7. Cronograma del Concurso

| Fecha | Hito | Tipo |
|---|---|---|
| 12 Jun 2026 | Charla informativa | Charla |
| 23 Jun 2026 | Charlas informativas | Charla |
| 30 Jun 2026 | Reunión laboratorios electrónica | Reunión |
| 03 Jul 2026 | Cierre de inscripciones | Deadline |
| 08 Jul 2026 | Webinar introductoria | Charla |
| 01 Sep – 18 Sep 2026 | Primera entrega y reuniones para dudas | Entrega / Deadline |
| 23 Oct 2026 | Entrega de proyectos | Entrega / Deadline |
| 09 Nov – 12 Nov 2026 | Presentaciones | Presentación / Deadline |
| 20 Nov 2026 | Aviso de finalistas | Aviso / Deadline |
| 26 Nov 2026 | Final virtual | Deadline / Presentación / Aviso |
| 14 Dic – 18 Dic 2026 | Entrega de premios | Premiación |

---

## 8. Estado Actual del Proyecto

### 8.1 Avance

| Tarea | Estado |
|---|---|
| Definir bien las ideas | En progreso |
| Definir boceto | No iniciado |
| Lectura completa de bases y condiciones | No iniciado |
| Lista de equipos para gemelo digital | No iniciado |

### 8.2 Logros

- **Gemelo digital base funcionando**: el modelo de simulación ya opera de forma modular, permitiendo añadir más dispositivos y mediciones.
- **Estructura del proyecto definida**: objetivos, enfoque y alcance claros.
- **Documentación base**: directrices del proyecto, bases del concurso y propuestas iniciales revisadas.
- **Notion integrado**: seguimiento de tareas, cronograma y notas de reuniones centralizado.

### 8.3 Pendientes

- Obtener datos reales del CEN para calibrar el gemelo digital.
- Definir boceto del sistema completo.
- Lectura completa y análisis detallado de las bases y condiciones del concurso.
- Lista detallada de equipos y sensores necesarios para el gemelo digital.
- Visita al CEN para conocer componentes eléctricos, corrientes y configuraciones.
- Definir si el modelo corre en nube o local.
- Establecer presupuesto y materiales.

---

## 9. Criterios de Evaluación del Concurso

Según las bases del concurso, los proyectos de la Línea 3 (Inteligencia Artificial) serán evaluados sobre 100 puntos:

| Criterio | Puntaje |
|---|---|
| **Nivel de innovación** de la solución | 25 |
| **Uso efectivo de IA** en la solución | 25 |
| **Impacto y escalabilidad** | 20 |
| **Viabilidad técnica y económica** | 15 |
| **Presentación y demostración** | 15 |

---

## 10. Equipo y Organización

- **Línea**: 3 — Inteligencia Artificial.
- **Participantes**: Vicente (autor principal), Javier (colaborador).
- **Herramientas de seguimiento**: Notion (tareas, cronograma, notas), MATLAB (simulación y gemelo digital), Python (orquestador).
- **Repositorio**: `D:\Projects\Siemens` — estructura con `docs/`, `matlab/`, `db/`, `orquestador.py`.
