# SPACEWISE AI — Presentación del Proyecto

## ¿Qué es SPACEWISE AI?

Un **sistema inteligente de gestión energética** para el Centro Espacial Nacional de Chile (CEN) que combina:

- **Gemelo digital** (modelo virtual del comportamiento energético del edificio)
- **IA predictiva** (algoritmos de ML para anticipar demanda y optimizar consumo)
- **Medición eléctrica Siemens** (sensores en tableros para datos en tiempo real)
- **Control automático** (ajuste de HVAC, iluminación y equipos)

**Meta**: reducir el consumo eléctrico anual entre **20% y 30%**, manteniendo confort y seguridad operacional.

---

## ¿Por qué este proyecto?

### El problema

Los centros de investigación como el CEN tienen:

- Consumo energético elevado y variable (laboratorios 24/7, oficinas, áreas comunes)
- Falta de visibilidad sobre consumo real por zona y equipo
- Control manual o estático de HVAC e iluminación
- Desaprovechamiento de fuentes renovables (fotovoltaica)
- Sin medición de impacto ambiental

### La oportunidad

Un sistema inteligente que:

- **Monitorea** el consumo en tiempo real
- **Predice** la demanda futura
- **Optimiza** el uso de energía
- **Controla** automáticamente los sistemas
- **Mide** la reducción de huella de carbono

**Replicabilidad**: el CEN es el caso de prueba, pero la solución puede adaptarse a universidades, laboratorios, edificios corporativos e infraestructura industrial.

---

## Objetivos

### Objetivo General

Diseñar, simular y validar un sistema inteligente de gestión energética para el CEN, integrando medición eléctrica Siemens, IA predictiva, gemelo digital y control operacional para reducir el consumo eléctrico anual entre 20% y 30%.

### Objetivos Específicos

1. **Caracterizar** los perfiles energéticos del edificio y desarrollar un gemelo digital
2. **Implementar** IA para predicción de demanda
3. **Optimizar** HVAC, iluminación y laboratorios
4. **Medir** reducción de huella de carbono
5. **Proponer** estrategia de control automático con IA

---

## ¿Qué hemos hecho hasta ahora?

### ✅ Avances

**Gemelo digital base funcionando**

- Modelo de simulación modular que permite añadir más dispositivos y mediciones
- Estructura del proyecto definida: objetivos, enfoque y alcance claros
- Documentación base revisada: directrices del proyecto, bases del concurso, propuestas iniciales
- Notion integrado para seguimiento de tareas, cronograma y notas de reuniones

**Ideas y decisiones clave**

- Medición desde tableros eléctricos (modular, escalable)
- IA para catalogar consumo por zona (cocina, laboratorios, oficinas) y definir rangos óptimos
- Dashboard funcional (priorizar resultados sobre estética)
- Control automático + medición (no solo medir, sino actuar)
- Integración de fuentes renovables (fotovoltaica) al mix energético

**Discusiones técnicas**

- Uso de sensores de presencia para detectar ocupación
- Iluminación regulable mediante potenciómetros
- Optimización parametrizada: que el sistema designe cuánta energía va a cada parte
- ML específico (no IA general) para predicción y optimización

### 📊 Estado actual de tareas

| Tarea | Estado |
|---|---|
| Definir bien las ideas | 🔄 En progreso |
| Definir boceto | ⏳ No iniciado |
| Lectura completa de bases y condiciones | ⏳ No iniciado |
| Lista de equipos para gemelo digital | ⏳ No iniciado |

---

## ¿Qué sigue?

### Próximos pasos inmediatos

1. **Obtener datos reales del CEN** para calibrar el gemelo digital
   - Visita al CEN para conocer componentes eléctricos, corrientes y configuraciones
   - Preguntas pendientes: componentes, corrientes, monofásico/multifásico

2. **Definir boceto del sistema completo**
   - Arquitectura general: sensores → gemelo digital → IA → control → dashboard
   - Flujo de datos y puntos de integración

3. **Lista detallada de equipos y sensores**
   - Qué sensores Siemens necesitamos
   - Cuántos, dónde se instalan, costos

4. **Definir si el modelo corre en nube o local**
   - Evaluar eficiencia vs. dependencia de internet
   - Latencia y seguridad de datos

5. **Establecer presupuesto y materiales**
   - Reunión con profesor para definir costos
   - Materiales necesarios

### Hitos del concurso

| Fecha | Hito |
|---|---|
| **01 Sep – 18 Sep 2026** | Primera entrega y reuniones para dudas |
| **23 Oct 2026** | Entrega de proyectos |
| **09 Nov – 12 Nov 2026** | Presentaciones |
| **20 Nov 2026** | Aviso de finalistas |
| **26 Nov 2026** | Final virtual |
| **14 Dic – 18 Dic 2026** | Entrega de premios |

---

## Criterios de evaluación del concurso

| Criterio | Puntaje |
|---|---|
| Nivel de innovación de la solución | 25 |
| Uso efectivo de IA en la solución | 25 |
| Impacto y escalabilidad | 20 |
| Viabilidad técnica y económica | 15 |
| Presentación y demostración | 15 |

**Total**: 100 puntos

---

## Componentes del sistema

| Componente | Qué hace |
|---|---|
| **Medición eléctrica Siemens** | Sensores en tableros capturan datos de consumo en tiempo real (corriente, voltaje, potencia, energía) |
| **Gemelo Digital** | Modelo de simulación calibrado con datos reales; permite probar escenarios de ahorro sin riesgo |
| **IA Predictiva** | Algoritmos de ML entrenados con datos históricos y en tiempo real para predecir demanda y detectar anomalías |
| **Dashboard** | Interfaz funcional que muestra consumo, ahorro, proyecciones y alertas |
| **Control Automático** | Ajusta HVAC, iluminación y equipos según predicción de demanda, ocupación y tarifas |
| **Integración de Renovables** | Considera fuentes de energía propia (fotovoltaica) como parte del mix optimizado |

---

## Resultados esperados

### Impacto cuantificable

| Métrica | Meta |
|---|---|
| Reducción de consumo eléctrico anual | 20% a 30% |
| Reducción de huella de carbono | Medible vía dashboard |
| Precisión de predicción de demanda | >85% (estimado) |
| Tiempo de respuesta del control automático | <5 segundos |

### Entregables

1. Gemelo digital funcional calibrado con datos reales
2. Modelo de IA para predicción de demanda y optimización
3. Dashboard de visualización con métricas, ahorro y alertas
4. Estrategia de control automático con IA
5. Informe de impacto con medición de reducción de huella de carbono
6. Documento técnico y presentación para el concurso

---

## Equipo y organización

- **Línea**: 3 — Inteligencia Artificial
- **Participantes**: Vicente (autor principal), Javier (colaborador)
- **Herramientas**: Notion (seguimiento), MATLAB (simulación), Python (orquestador)
- **Repositorio**: `D:\Projects\Siemens`

---

## Resumen ejecutivo (para presentación oral)

**SPACEWISE AI** es un sistema inteligente de gestión energética para el Centro Espacial Nacional de Chile que combina gemelo digital, IA predictiva y medición eléctrica Siemens para reducir el consumo entre 20% y 30%.

**El problema**: los centros de investigación tienen consumo elevado y variable, sin visibilidad ni control inteligente.

**La solución**: un gemelo digital alimentado por datos reales que predice demanda, optimiza consumo y controla automáticamente HVAC, iluminación y equipos.

**Lo que llevamos**: gemelo digital base funcionando, ideas y decisiones clave definidas, estructura del proyecto clara.

**Lo que sigue**: obtener datos reales del CEN, definir boceto del sistema, lista de equipos, decidir nube vs. local, establecer presupuesto.

**Meta**: primera entrega en septiembre, entrega final en octubre, presentaciones en noviembre.

**Impacto**: replicable a universidades, laboratorios, edificios corporativos e industria.
