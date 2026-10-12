# Catálogo de Equipamiento Industrial — SPACEWISE AI

**Fuente**: Gemini Deep Research from "Datos Equipos.pdf"
**Fecha**: Octubre 2026
**Propósito**: Caracterización energética completa para simulación dinámica de 8760 horas

Informe de Caracterización y Perfilado
Energético de Equipamiento Industrial
para Simulación Dinámica (8760 Horas)
La simulación energética de alta resolución es un componente crítico para la optimización de
instalaciones industriales y centros de investigación. Para establecer una línea base de
consumo verdaderamente representativa, es imperativo aplicar el método de análisis hora por
hora (8760 horas), el cual simula el comportamiento térmico y eléctrico de una instalación a lo
largo de un año completo. Esta metodología, fuertemente respaldada por la ASHRAE Guideline
14, permite capturar la interacción dinámica entre las variaciones climáticas, los perfiles de
ocupación y la respuesta de los sistemas mecánicos[^1]. A diferencia de los métodos
simplificados, el análisis 8760 incorpora las fluctuaciones de carga parcial, los ciclos de trabajo
y la variabilidad estacional, resultando indispensable para el cumplimiento de normativas de
gestión energética como la ISO 50001[^4].
La precisión de estos modelos depende intrínsecamente de la calidad de los datos de entrada
electromecánicos. En el contexto de los sistemas rotativos y motores eléctricos, las normativas
internacionales como la IEC 60034-30-1 resultan fundamentales para clasificar la eficiencia
operativa. La transición hacia motores de clase Premium (IE3) y Super-Premium (IE4) no solo
reduce las pérdidas térmicas en un 20-30% respecto a modelos antiguos, sino que altera el
factor de potencia nominal y el comportamiento bajo carga parcial[^6]. Por lo tanto, caracterizar
un equipo requiere especificar no solo su potencia nominal, sino cómo su eficiencia y factor de
potencia varían dinámicamente según el estado de operación.
Paralelamente, la proliferación de Variadores de Frecuencia (VFD) y rectificadores activos ha
introducido distorsiones armónicas en las redes industriales. La normativa IEEE 519-2022
establece límites estrictos para la Distorsión Armónica Total (THD) y la Distorsión de Demanda
Total (TDD) en el Punto de Acoplamiento Común (PCC)[^9]. Mientras que una carga lineal (como
un motor de arranque directo o un calentador resistivo) presenta una THD baja, los equipos
controlados por electrónica de potencia pueden inyectar armónicos significativos, alterando la
calidad de la energía y requiriendo mitigación activa[^12]. Los perfiles detallados a continuación
incorporan estas métricas de calidad de energía, estableciendo una base exhaustiva para la
simulación de 100 equipos clave en entornos industriales y de investigación.

## HVAC Industrial (20 equipos)

### HVAC-001 — Chiller Centrífugo de Alta Eficiencia

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Trane CenTraVac CVHE |
| Potencia nominal | 350.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 595 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 18.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.75
- Variabilidad estacional: Alta. Pico de consumo en meses de verano; carga base en invierno.
- Ciclos de trabajo: Operación plena (30%), Operación parcial (60%), Standby (10%).
- Fracción de tiempo en cada estado: 0.3, 0.6, 0.1 respectivamente.

**Comportamiento dinámico:**

- Arranque: 60s, consumo 4.0x nominal
- Standby: 5% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Planta central de agua helada para refrigeración de procesos.
- Criticidad: CRITICA
- Dependencias: Requiere bombas primarias y torres de enfriamiento.
- Condiciones ambientales: El consumo aumenta drásticamente con la temperatura del bulbo húmedo exterior.

### HVAC-002 — Chiller Enfriado por Aire con VFD

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Carrier AquaForce 30KAV |
| Potencia nominal | 180.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 273 A |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 5.0 % (Con filtro armónico activo) |

**Perfil de consumo:**

- Operación: 16 h/día, 6 días/semana
- Factor de carga promedio: 0.65
- Variabilidad estacional: Muy dependiente de la temperatura del aire exterior.
- Ciclos de trabajo: Modulación continua Inverter (90%), Apagado (10%).
- Fracción de tiempo en cada estado: 0.9, 0.1.

**Comportamiento dinámico:**

- Arranque: 30s, consumo 1.5x nominal
- Standby: 2% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Climatización de naves de ensamblaje.
- Criticidad: ESENCIAL
- Dependencias: Red de agua helada secundaria.
- Condiciones ambientales: Rendimiento afectado por exposición solar directa y temperatura ambiente.

### HVAC-003 — Chiller de Tornillo Agua-Agua

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Daikin EWWD-FZ |
| Potencia nominal | 220.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 368 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 12.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.70
- Variabilidad estacional: Moderada. La carga del proceso suele dominar sobre el clima exterior.
- Ciclos de trabajo: Carga plena (20%), Carga parcial escalonada (75%), Standby (5%).
- Fracción de tiempo en cada estado: 0.2, 0.75, 0.05.

**Comportamiento dinámico:**

- Arranque: 45s, consumo 4.5x nominal
- Standby: 3% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Enfriamiento de inyectoras y procesos de manufactura.
- Criticidad: CRITICA
- Dependencias: Torres de enfriamiento de circuito cerrado.
- Condiciones ambientales: Operación interior estable, independiente del clima.

### HVAC-004 — Torre de Enfriamiento Circuito Cerrado

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | BAC FXV Series |
| Potencia nominal | 45.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 77 A |
| Factor de potencia nominal | 0.84 |
| Fases | 3 |
| THD esperado | 3.5 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.80
- Variabilidad estacional: Alta correlación con la humedad exterior.
- Ciclos de trabajo: Ventilador a plena capacidad (60%), Ventilador ciclando (40%).
- Fracción de tiempo en cada estado: 0.6, 0.4.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 6.0x nominal
- Standby: 0% de nominal (apagado)
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Rechazo térmico de chillers condensados por agua.
- Criticidad: CRITICA
- Dependencias: Chiller principal y bombas de condensación.
- Condiciones ambientales: Sensible al bulbo húmedo y vientos cruzados.

### HVAC-005 — Torre de Enfriamiento Tiro Forzado

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Marley NC Class |
| Potencia nominal | 30.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 52 A |
| Factor de potencia nominal | 0.83 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 6 días/semana
- Factor de carga promedio: 0.70
- Variabilidad estacional: Mayor uso durante turnos diurnos de verano.
- Ciclos de trabajo: Operación plena (50%), Parcial/apagado (50%).
- Fracción de tiempo en cada estado: 0.5, 0.5.

**Comportamiento dinámico:**

- Arranque: 15s, consumo 6.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Rechazo de calor de procesos secundarios.
- Criticidad: ESENCIAL
- Dependencias: Ninguna directa (válvulas termostáticas de control).
- Condiciones ambientales: Intemperie.

### HVAC-006 — Unidad Manejadora de Aire (AHU) Gran Caudal

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | York Solution AHU |
| Potencia nominal | 22.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 35 A |
| Factor de potencia nominal | 0.92 |
| Fases | 3 |
| THD esperado | 15.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 6 días/semana
- Factor de carga promedio: 0.60
- Variabilidad estacional: Constante (el caudal de ventilación es fijo por calidad de aire).
- Ciclos de trabajo: Volumen Variable (VAV) adaptativo (100% del tiempo operativo).
- Fracción de tiempo en cada estado: 1.0.

**Comportamiento dinámico:**

- Arranque: 20s, consumo 2.0x nominal (Arrancador suave/VFD).
- Standby: 5% de nominal (controladores de compuertas).
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Renovación y filtrado de aire en nave de producción.
- Criticidad: ESENCIAL
- Dependencias: Agua helada/caliente de caldera.
- Condiciones ambientales: Calidad del aire particulado exterior.

### HVAC-007 — Unidad Manejadora de Aire Cleanroom (Sala Blanca)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | FläktGroup CAIRplus |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 23 A |
| Factor de potencia nominal | 0.94 |
| Fases | 3 |
| THD esperado | 12.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.85
- Variabilidad estacional: Nula. Requiere presurización y filtrado constante 24/7.
- Ciclos de trabajo: Flujo volumétrico constante para mantener presiones positivas.
- Fracción de tiempo en cada estado: 1.0 (Plena carga continua).

**Comportamiento dinámico:**

- Arranque: 30s, consumo 1.5x nominal
- Standby: N/A (nunca se apaga).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Filtración HEPA y control T/HR en laboratorios farmacéuticos o semiconductores.
- Criticidad: CRITICA
- Dependencias: Monitoreo de presión diferencial.
- Condiciones ambientales: Estrictamente controladas.

### HVAC-008 — Sistema VRF Industrial Exterior

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Mitsubishi Electric City Multi |
| Potencia nominal | 56.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 84 A |
| Factor de potencia nominal | 0.96 |
| Fases | 3 |
| THD esperado | 8.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 5 días/semana
- Factor de carga promedio: 0.55
- Variabilidad estacional: Muy alta (funciona como bomba de calor en invierno).
- Ciclos de trabajo: Modulación continua del compresor Inverter.
- Fracción de tiempo en cada estado: 0.8 modulando, 0.2 standby/apagado.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 1.2x nominal (Arranque Inverter muy suave).
- Standby: 3% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Climatización de oficinas periféricas de la planta.
- Criticidad: FLEXIBLE
- Dependencias: Evaporadoras internas distribuidas.
- Condiciones ambientales: Temperatura ambiente (afecta coeficiente de desempeño COP).

### HVAC-009 — Unidad de Enfriamiento de Precisión (CRAC)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Vertiv Liebert PeX4 |
| Potencia nominal | 40.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 62 A |
| Factor de potencia nominal | 0.93 |
| Fases | 3 |
| THD esperado | 10.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana ● Factor de carga promedio: 0.80
- Variabilidad estacional: Nula. La carga proviene de servidores TI internos.
- Ciclos de trabajo: Compresor modulante continuo, ventilador EC constante.
- Fracción de tiempo en cada estado: 1.0 operación base.

**Comportamiento dinámico:**

- Arranque: 15s, consumo 2.5x nominal
- Standby: 5% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Climatización bajo piso falso en Data Center.
- Criticidad: CRITICA
- Dependencias: UPS.
- Condiciones ambientales: Carga térmica interna constante.

### HVAC-010 — Unidad In-Row para Data Center

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Schneider Electric Uniflair |
| Potencia nominal | 12.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 18 A |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 7.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.75
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Ventiladores acoplados a la carga instantánea del rack.
- Fracción de tiempo en cada estado: 1.0 operación variable.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 1.2x nominal
- Standby: 2% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Extracción de calor directa en pasillo caliente.
- Criticidad: CRITICA
- Dependencias: Suministro de agua helada del chiller central.
- Condiciones ambientales: Temperaturas del aire de retorno del rack.

### HVAC-011 — Fan Coil Hidrónico Industrial High-Static

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Carrier 42CT |
| Potencia nominal | 2.2 kW |
| Voltaje | 230 V |
| Corriente nominal | 10.8 A |
| Factor de potencia nominal | 0.88 |
| Fases | 1 |
| THD esperado | 4.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 5 días/semana
- Factor de carga promedio: 0.65
- Variabilidad estacional: Carga media todo el año.
- Ciclos de trabajo: Velocidad Alta (20%), Media (40%), Baja (30%), Apagado (10%).
- Fracción de tiempo en cada estado: 0.2, 0.4, 0.3, 0.1.

**Comportamiento dinámico:**

- Arranque: 2s, consumo 3.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Laboratorios secundarios y cuartos de control. ● Criticidad: NO_CRITICA
- Dependencias: Sistema hidrónico principal.
- Condiciones ambientales: Requisitos de ocupación humana.

### HVAC-012 — Fan Coil Encastrable Techo

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Daikin FWC-BT |
| Potencia nominal | 0.85 kW |
| Voltaje | 230 V |
| Corriente nominal | 4.3 A |
| Factor de potencia nominal | 0.85 |
| Fases | 1 |
| THD esperado | 5.0 % |

**Perfil de consumo:**

- Operación: 10 h/día, 5 días/semana
- Factor de carga promedio: 0.50
- Variabilidad estacional: Uso esporádico según clima exterior y ocupación.
- Ciclos de trabajo: Ciclado termostático (ON/OFF).
- Fracción de tiempo en cada estado: 0.5 ON, 0.5 OFF.

**Comportamiento dinámico:**

- Arranque: 2s, consumo 3.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Oficinas administrativas pequeñas.
- Criticidad: NO_CRITICA
- Dependencias: Chiller/Caldera de planta.
- Condiciones ambientales: Temperaturas de confort.

### HVAC-013 — Rooftop Package Unit con Bomba de Calor

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Trane Voyager |
| Potencia nominal | 35.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 58 A |
| Factor de potencia nominal | 0.87 |
| Fases | 3 |
| THD esperado | 6.0 % |

**Perfil de consumo:**

- Operación: 14 h/día, 6 días/semana
- Factor de carga promedio: 0.68
- Variabilidad estacional: Pico en verano e invierno (refrigeración/calefacción).
- Ciclos de trabajo: Compresor ON (60%), Ventilador sin compresor (30%), Apagado (10%).
- Fracción de tiempo en cada estado: 0.6, 0.3, 0.1.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 5.0x nominal
- Standby: 2% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Acondicionamiento de nave logística o almacén.
- Criticidad: ESENCIAL
- Dependencias: Ninguna (Autónomo).
- Condiciones ambientales: Instalado en la intemperie.

### HVAC-014 — Climatizador Evaporativo Industrial

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Seeley Breezair TBS500 |
| Potencia nominal | 7.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 13 A |
| Factor de potencia nominal | 0.82 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 10 h/día, 6 días/semana
- Factor de carga promedio: 0.70
- Variabilidad estacional: Exclusivo de meses cálidos y secos.
- Ciclos de trabajo: Ventilador y bomba de agua en estado estacionario ON.
- Fracción de tiempo en cada estado: 0.7 ON, 0.3 Standby.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 5.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Inyección de aire fresco y húmedo en líneas de ensamble calientes.
- Criticidad: FLEXIBLE
- Dependencias: Suministro de agua de red.
- Condiciones ambientales: Altamente dependiente de la depresión psicrométrica (baja humedad relativa).

### HVAC-015 — Deshumectador Industrial por Rotor Desecante

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Munters MX2 1500 |
| Potencia nominal | 28.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 44 A |
| Factor de potencia nominal | 0.91 |
| Fases | 3 |
| THD esperado | 4.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.82
- Variabilidad estacional: Pico en meses lluviosos/húmedos.
- Ciclos de trabajo: Resistencia térmica de regeneración y rotor girando 100%.
- Fracción de tiempo en cada estado: 0.8 Plena carga, 0.2 Modulado.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 2.0x nominal (combinación resistiva/inductiva).
- Standby: 5% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Control estricto de humedad en cuartos de secado o envasado de polvos.
- Criticidad: CRITICA
- Dependencias: Inyección de aire de proceso.
- Condiciones ambientales: Sensible a la humedad absoluta del aire exterior.

### HVAC-016 — Extractora de Aire Recirculante (Clasificación ATEX)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Systemair Danvent DV |
| Potencia nominal | 18.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 31 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 14.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.78
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Velocidad continua controlada por VFD antiexplosivo.
- Fracción de tiempo en cada estado: 1.0 ON.

**Comportamiento dinámico:**

- Arranque: 15s, consumo 1.5x nominal
- Standby: 0% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Extracción en zonas de solventes y atmósferas explosivas.
- Criticidad: ESENCIAL
- Dependencias: Sensores de vapores orgánicos (LEL).
- Condiciones ambientales: Ambientes industriales severos.

### HVAC-017 — Chiller Scroll Compacto Aire-Agua

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Stulz CyberCool 2 |
| Potencia nominal | 90.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 148 A |
| Factor de potencia nominal | 0.88 |
| Fases | 3 |
| THD esperado | 10.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 6 días/semana
- Factor de carga promedio: 0.62
- Variabilidad estacional: Mayor demanda en picos diurnos de verano.
- Ciclos de trabajo: Compresores múltiples encendiendo en cascada.
- Fracción de tiempo en cada estado: 0.2 (1 comp), 0.4 (2 comp), 0.2 (3 comp), 0.2 apagado.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 4.0x nominal (picos sucesivos).
- Standby: 2% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Enfriamiento de redes de laboratorios periféricos.
- Criticidad: ESENCIAL
- Dependencias: Red hidrónica local.
- Condiciones ambientales: Montaje exterior.

### HVAC-018 — Bomba de Calor Geotérmica Industrial

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WaterFurnace 7 Series |
| Potencia nominal | 42.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 68 A |
| Factor de potencia nominal | 0.89 |
| Fases | 3 |
| THD esperado | 5.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 7 días/semana
- Factor de carga promedio: 0.58
- Variabilidad estacional: Altamente eficiente todo el año debido a la inercia térmica del subsuelo.
- Ciclos de trabajo: Carga base continua, ciclos medios de termostato.
- Fracción de tiempo en cada estado: 0.6 ON, 0.4 OFF.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 3.0x nominal
- Standby: 2% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Calefacción de radiadores industriales/piso radiante.
- Criticidad: FLEXIBLE
- Dependencias: Lazo de intercambio geotérmico subterráneo.
- Condiciones ambientales: Temperatura del terreno profundo.

### HVAC-019 — Cortina de Aire Industrial Trifásica

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Thermoscreens HP2000 |
| Potencia nominal | 18.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 27 A |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 5 días/semana
- Factor de carga promedio: 0.80
- Variabilidad estacional: Calefacción resistiva activa sólo en invierno.
- Ciclos de trabajo: Accionada por switch de apertura de portón.
- Fracción de tiempo en cada estado: 0.2 ON pleno, 0.8 Apagado.

**Comportamiento dinámico:**

- Arranque: 2s, consumo 2.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Puerta de muelle de carga (andén logístico).
- Criticidad: NO_CRITICA
- Dependencias: Apertura de puerta externa.
- Condiciones ambientales: Infiltración de aire frío.

### HVAC-020 — Unidad Condensadora Remota para Chillers

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Güntner GFH |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 26 A |
| Factor de potencia nominal | 0.84 |
| Fases | 3 |
| THD esperado | 4.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.65
- Variabilidad estacional: Totalmente correlacionada a la carga de los compresores interiores.
- Ciclos de trabajo: Control de presión de condensación modulando los ventiladores.
- Fracción de tiempo en cada estado: 0.4 alta velocidad, 0.6 velocidad reducida.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 1.5x nominal
- Standby: 0% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Disipación de calor central (Dry Cooler).
- Criticidad: ESENCIAL
- Dependencias: Tuberías de gas refrigerante desde sala de máquinas.
- Condiciones ambientales: Temperatura exterior y obstrucciones.

## Compresores y Neumática (15 equipos)

### COMP-001 — Compresor de Tornillo Rotativo VSD

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Atlas Copco GA90 VSD |
| Potencia nominal | 90.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 136 A |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 28.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.65
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Velocidad del motor modulada según la presión de la red (30% a 100% rpm).
- Fracción de tiempo en cada estado: Modulación continua (1.0).

**Comportamiento dinámico:**

- Arranque: 15s, consumo 1.2x nominal (VSD minimiza picos de corriente).
- Standby: 10% de nominal (motor detenido pero electrónica y ventilación auxiliares operando).
- Flexibilidad: sí (como carga marginal de red).

**Contexto operativo:**

- Aplicación típica: Suministro de aire comprimido modulante primario.
- Criticidad: CRITICA
- Dependencias: Unidad secadora y red de filtrado.
- Condiciones ambientales: Requiere adecuada ventilación en el cuarto de compresores.

### COMP-002 — Compresor de Tornillo Velocidad Fija (Carga Base)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Kaeser CSD 125 |
| Potencia nominal | 75.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 128 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 5 días/semana
- Factor de carga promedio: 0.85
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Regulación carga (Load) / vacío (Unload).
- Fracción de tiempo en cada estado: 0.85 Carga, 0.15 Vacío.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 6.0x nominal (Estrella-Triángulo).
- Standby: 25% de nominal (Trabajo en vacío, motor girando sin compresión).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Operación constante como "carga base" de un sistema de múltiples compresores.
- Criticidad: ESENCIAL
- Dependencias: Válvula de admisión y descompresión.
- Condiciones ambientales: Calidad del aire aspirado.

### COMP-003 — Compresor de Tornillo Gran Caudal

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Ingersoll Rand R-Series 160 |
| Potencia nominal | 160.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 273 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 6 días/semana ● Factor de carga promedio: 0.90
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Plena carga casi ininterrumpida.
- Fracción de tiempo en cada estado: 0.95 Carga, 0.05 Vacío.

**Comportamiento dinámico:**

- Arranque: 12s, consumo 6.0x nominal
- Standby: 25% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Minería, siderurgia, o ensamblaje de gran formato.
- Criticidad: CRITICA
- Dependencias: Pulmón acumulador de gran volumen.
- Condiciones ambientales: Susceptible a saturación de filtros por polución.

### COMP-004 — Compresor de Tornillo Secundario

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Sullair LS90 |
| Potencia nominal | 90.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 153 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 8 h/día, 5 días/semana
- Factor de carga promedio: 0.50
- Variabilidad estacional: Usado para absorber picos diarios de turnos específicos.
- Ciclos de trabajo: Mayor tiempo en Unload (vacío) que los compresores base.
- Fracción de tiempo en cada estado: 0.4 Carga, 0.6 Vacío/Apagado.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 6.0x nominal
- Standby: 20% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Respaldo de red y absorción de transitorios.
- Criticidad: FLEXIBLE
- Dependencias: Controlador lógico programable maestro de secuenciación.
- Condiciones ambientales: Normal de cuarto de equipos.

### COMP-005 — Compresor de Tornillo Pequeño

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Boge C20 |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 26 A |
| Factor de potencia nominal | 0.84 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 5 días/semana
- Factor de carga promedio: 0.70
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Ciclado directo de ON y OFF, con corto período en vacío.
- Fracción de tiempo en cada estado: 0.7 Carga, 0.3 Apagado.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 5.0x nominal
- Standby: 20% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Taller de mantenimiento o sub-estación neumática aislada. ● Criticidad: NO_CRITICA
- Dependencias: Ninguna externa.
- Condiciones ambientales: Operación autónoma en el punto de uso.

### COMP-006 — Compresor de Tornillo Mediano

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | CompAir L45 |
| Potencia nominal | 45.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 77 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 5 días/semana
- Factor de carga promedio: 0.65
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Regulación de válvulas de admisión estándar.
- Fracción de tiempo en cada estado: 0.6 Carga, 0.4 Vacío.

**Comportamiento dinámico:**

- Arranque: 8s, consumo 6.0x nominal
- Standby: 25% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Herramientas neumáticas intermitentes y cilindros de línea.
- Criticidad: ESENCIAL
- Dependencias: Secador frigorífico independiente.
- Condiciones ambientales: Calidad estándar de red.

### COMP-007 — Compresor Centrífugo de Aire

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Atlas Copco ZH 350 |
| Potencia nominal | 350.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 585 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 2.5 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.95
- Variabilidad estacional: Eficiencia levemente superior con aire frío y denso de invierno.
- Ciclos de trabajo: Operación aerodinámica constante a altas revoluciones; válvulas de bypass (blow-off) previenen bombeo (surge).
- Fracción de tiempo en cada estado: 0.95 Diseño, 0.05 Bypass/Purga.

**Comportamiento dinámico:**

- Arranque: 20s, consumo 5.0x nominal
- Standby: 30% de nominal (Blow-off continuo sin apagar).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Industria de vidrio o automotriz, flujo de aire exento de aceite.
- Criticidad: CRITICA
- Dependencias: Intercoolers de agua helada vitales.
- Condiciones ambientales: Presión barométrica afecta la relación de compresión.

### COMP-008 — Compresor Centrífugo de Gran Volumen

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | FS-Elliott Polaris |
| Potencia nominal | 250.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 418 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 2.5 % |

**Perfil de consumo:**

- Operación: 24 h/día, 6 días/semana
- Factor de carga promedio: 0.88
- Variabilidad estacional: Baja.
- Ciclos de trabajo: Rotación continua de impulsores en distintas etapas.
- Fracción de tiempo en cada estado: 0.90 Plena carga, 0.10 Modulación Inlet Guide Vane (IGV).

**Comportamiento dinámico:**

- Arranque: 20s, consumo 5.0x nominal
- Standby: 30% de nominal
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Soplado de botellas PET o procesos petroquímicos.
- Criticidad: CRITICA
- Dependencias: Pre-filtros de altísima eficiencia.
- Condiciones ambientales: Requiere aire libre de vibraciones y turbulencias en la toma.

### COMP-009 — Compresor de Pistón Alta Presión (Booster)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Kaeser N253 Piston Booster |
| Potencia nominal | 22.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 37 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 10 h/día, 5 días/semana
- Factor de carga promedio: 0.50
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Arranques y paradas bruscos y repetitivos para recargar banco de alta presión.
- Fracción de tiempo en cada estado: 0.5 Carga (100%), 0.5 Apagado absoluto.

**Comportamiento dinámico:**

- Arranque: 3s, consumo 7.0x nominal (Gran inercia de compresión).
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Elevación de presión de 7 bar a 40 bar para corte láser o prueba hidrostática.
- Criticidad: ESENCIAL
- Dependencias: Necesita suministro previo de aire comprimido a 7 bar.
- Condiciones ambientales: Tendencia al sobrecalentamiento del bloque de pistones.

### COMP-010 — Compresor de Pistón de Taller

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Quincy QT-15 |
| Potencia nominal | 11.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 19 A |
| Factor de potencia nominal | 0.83 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 8 h/día, 5 días/semana
- Factor de carga promedio: 0.40
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Control presostático clásico (Enciende al bajar presión, apaga al llenar tanque).
- Fracción de tiempo en cada estado: 0.4 ON, 0.6 OFF.

**Comportamiento dinámico:**

- Arranque: 2s, consumo 7.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Uso neumático general en bahías de mantenimiento.
- Criticidad: NO_CRITICA
- Dependencias: Tanque receptor adyacente.
- Condiciones ambientales: Típicamente sucio y ruidoso.

### COMP-011 — Bomba de Vacío de Paletas Rotativas

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Busch R5 |
| Potencia nominal | 18.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 31 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 6 días/semana
- Factor de carga promedio: 0.80
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Evacuación inicial (carga alta) seguido de mantenimiento de vacío profundo.
- Fracción de tiempo en cada estado: 0.2 Evacuación, 0.8 Mantenimiento.

**Comportamiento dinámico:**

- Arranque: 5s, consumo 5.0x nominal
- Standby: 40% de nominal (trabajando en dead-head).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Envasado al vacío en industria alimentaria (carnes, quesos).
- Criticidad: CRITICA
- Dependencias: Aceite lubricante/sellador en óptimo estado.
- Condiciones ambientales: Viscosidad del aceite afectada por frío.

### COMP-012 — Bomba de Vacío Auxiliar

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Leybold SOGEVAC |
| Potencia nominal | 7.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 13 A |
| Factor de potencia nominal | 0.83 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 5 días/semana
- Factor de carga promedio: 0.70
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Ciclos de desgasificación esporádica.
- Fracción de tiempo en cada estado: 0.7 Carga, 0.3 Standby por bypass.

**Comportamiento dinámico:**

- Arranque: 3s, consumo 5.0x nominal
- Standby: 30% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Termoformado de envases plásticos o sujeción por vacío (CNC routers).
- Criticidad: ESENCIAL
- Dependencias: Filtrado de polvo para evitar entrada a la cámara.
- Condiciones ambientales: Limpieza regular de filtros.

### COMP-013 — Bomba de Vacío Seca (Dry Pump) con VFD

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Edwards GXS Dry |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 24 A |
| Factor de potencia nominal | 0.90 |
| Fases | 3 |
| THD esperado | 15.0 % (Electrónica integrada) |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.60
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Algoritmo interno ajusta RPM según la presión del gas de proceso.
- Fracción de tiempo en cada estado: Modulación continua (1.0).

**Comportamiento dinámico:**

- Arranque: 10s, consumo 1.5x nominal
- Standby: 10% de nominal (Modo Green/Standby inteligente).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Fabricación de semiconductores, recubrimientos PVD, procesos libres de hidrocarburos.
- Criticidad: CRITICA
- Dependencias: Suministro de nitrógeno para purga de laberintos.
- Condiciones ambientales: Ambientes asépticos.

### COMP-014 — Soplador de Lóbulos (Blower) para Presión Positiva

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Aerzen Delta Blower |
| Potencia nominal | 37.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 63 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.85
- Variabilidad estacional: Requiere bombear mayor volumen en verano al disminuir la densidad del aire.
- Ciclos de trabajo: Desplazamiento de gas a baja presión pero volumen alto y constante.
- Fracción de tiempo en cada estado: 1.0 Flujo base.

**Comportamiento dinámico:**

- Arranque: 15s, consumo 6.0x nominal
- Standby: N/A (Típicamente en configuración 1+1 redundante).
- Flexibilidad: sí (Rotación de redundancia).

**Contexto operativo:**

- Aplicación típica: Aireación biológica en Plantas de Tratamiento de Aguas Residuales (PTAR).
- Criticidad: CRITICA
- Dependencias: Demanda biológica de oxígeno (sensores D.O.).
- Condiciones ambientales: Instalación exterior bajo cubiertas.

### COMP-015 — Soplador Auxiliar de Transporte Neumático

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Gardner Denver Sutorbilt |
| Potencia nominal | 22.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 38 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 6 días/semana
- Factor de carga promedio: 0.75
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Se enciende y apaga sincronizado con tolvas pesadoras y silos.
- Fracción de tiempo en cada estado: 0.5 ON, 0.5 OFF.

**Comportamiento dinámico:**

- Arranque: 10s, consumo 6.0x nominal
- Standby: 0% de nominal
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Transporte de pellets de plástico o grano hacia extrusoras.
- Criticidad: ESENCIAL
- Dependencias: Válvulas rotativas o "esclusas".
- Condiciones ambientales: Concentración de partículas sólidas suspendidas.

## Motores Eléctricos (20 equipos)

### MOT-001 — Motor IE3 Bomba 1 (DOL)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB IE3 Cast Iron |
| Potencia nominal | 0.75 kW |
| Voltaje | 400 V |
| Corriente nominal | 1.7 A |
| Factor de potencia nominal | 0.78 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.80. Continuo, sin estacionalidad

**Comportamiento dinámico:**

Arranque 6x nominal (2s). Standby 0%

**Contexto operativo:**

Aplicación general de trasvase hídrico. Criticidad: ESENCIAL

### MOT-002 — Motor IE3 Extractor (DOL)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Siemens Simotics SD IE3 |
| Potencia nominal | 1.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 3.2 A |
| Factor de potencia nominal | 0.80 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.70. Constante

**Comportamiento dinámico:**

Arranque 6x nominal (3s). Standby 0%

**Contexto operativo:**

Ventilación de naves. Criticidad: ESENCIAL

### MOT-003 — Motor IE3 Agitador (DOL)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WEG W22 Premium |
| Potencia nominal | 3.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 6.1 A |
| Factor de potencia nominal | 0.82 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.65

**Comportamiento dinámico:**

Arranque 6x nominal (3s)

**Contexto operativo:**

Mezclador de tanques de reacción química. Criticidad: ESENCIAL

### MOT-004 — Motor IE3 Motorreductor (DOL)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | SEW Eurodrive DRN |
| Potencia nominal | 5.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 10.7 A |
| Factor de potencia nominal | 0.84 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.85

**Comportamiento dinámico:**

Arranque 6x nominal (5s). Picos dinámicos mecánicos en carga intermitente

**Contexto operativo:**

Elevador de cangilones logístico. Criticidad: ESENCIAL

### MOT-005 — Motor IE3 Ventilador Tiro Inducido (Soft Start)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB IE3 Process Performance |
| Potencia nominal | 11.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 20.5 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.90

**Comportamiento dinámico:**

Arranque 5x nominal (10s rampa)

**Contexto operativo:**

Flujo de humos en chimenea de caldera. Criticidad: CRITICA

### MOT-006 — Motor IE3 Compresión Primaria (Soft Start)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WEG W22 |
| Potencia nominal | 22.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 39.8 A |
| Factor de potencia nominal | 0.87 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.75

**Comportamiento dinámico:**

Arranque 5x nominal (12s rampa)

**Contexto operativo:**

Accionamiento de bombas de amoníaco. Criticidad: ESENCIAL

### MOT-007 — Motor IE3 Molino A (Soft Start)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Siemens Simotics FD |
| Potencia nominal | 45.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 79.5 A |
| Factor de potencia nominal | 0.88 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 24 h/día, 6 días/semana. Factor carga: 0.95 (Alta densidad inercial)

**Comportamiento dinámico:**

Arranque 4x nominal (15s)

**Contexto operativo:**

Molienda primaria de crudo en cementera. Criticidad: CRITICA

### MOT-008 — Motor IE3 Molino B (Soft Start)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB High Voltage Induction |
| Potencia nominal | 75.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 131.0 A |
| Factor de potencia nominal | 0.88 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 24 h/día, 6 días/semana. Factor carga: 0.90

**Comportamiento dinámico:**

Arranque 4x nominal (20s)

**Contexto operativo:**

Refinación secundaria de partículas sólidas. Criticidad: CRITICA

### MOT-009 — Motor IE3 Trituradora (Soft Start)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WEG W50 |
| Potencia nominal | 160.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 275 A |
| Factor de potencia nominal | 0.89 |
| Fases | 3 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.85

**Comportamiento dinámico:**

Arranque 4x nominal (25s)

**Contexto operativo:**

Triturado de chatarra (Heavy-duty). Flexibilidad horaria si hay silos intermedios. Criticidad: CRITICA

### MOT-010 — Motor IE3 Cinta Carga Larga (Soft Start)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Siemens H-Compact |
| Potencia nominal | 500.0 kW |
| Voltaje | 3300 V |
| Corriente nominal | 855 A |
| Factor de potencia nominal | 0.89 |
| Fases | 3 |
| THD esperado | 2.0 % |

> **Nota**: Corregido a media tensión (3.3 kV). El original reportaba 400V, inviable para 500 kW.

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.80

**Comportamiento dinámico:**

Arranque 3x nominal (30s) con acople viscoso

**Contexto operativo:**

Transporte continuo transfronterizo de mineral desde la mina. Criticidad: CRITICA

### MOT-011 — Motor IE4 Síncrono Reluctancia + VFD

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB SynRM |
| Potencia nominal | 1.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 2.5 A (Mejorado por SynRM) |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 35.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 6 días/semana. Factor carga: 0.60. Variable

**Comportamiento dinámico:**

Arranque 1.1x nominal (10s controlados)

**Contexto operativo:**

Bomba de dosificación de aditivos químicos (alta exactitud). Criticidad: FLEXIBLE

### MOT-012 — Motor IE4 + VFD (Bomba B)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WEG W22 Magnet |
| Potencia nominal | 2.2 kW |
| Voltaje | 400 V |
| Corriente nominal | 3.6 A |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 35.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 6 días/semana. Factor carga: 0.65

**Comportamiento dinámico:**

Arranque 1.1x nominal

**Contexto operativo:**

Circulación de fluidos limpios industriales secundarios. Criticidad: FLEXIBLE

### MOT-013 — Motor IE4 + VFD (Ventilador A)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Siemens Simotics Reluctance |
| Potencia nominal | 5.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 9.0 A |
| Factor de potencia nominal | 0.96 |
| Fases | 3 |
| THD esperado | 32.0 % |

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.75

**Comportamiento dinámico:**

Arranque 1.2x nominal (15s)

**Contexto operativo:**

Ventilación adaptativa de ductos secundarios. Criticidad: FLEXIBLE

### MOT-014 — Motor IE4 + VFD (Ventilador B)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB SynRM |
| Potencia nominal | 11.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 17.5 A |
| Factor de potencia nominal | 0.96 |
| Fases | 3 |
| THD esperado | 30.0 % |

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.80

**Comportamiento dinámico:**

Arranque 1.2x nominal

**Contexto operativo:**

Manejadora de aire central. Criticidad: ESENCIAL

### MOT-015 — Motor IE4 + VFD (Mezclador)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WEG Super Premium |
| Potencia nominal | 18.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 28.5 A |
| Factor de potencia nominal | 0.97 |
| Fases | 3 |
| THD esperado | 28.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 5 días/semana. Factor carga: 0.70

**Comportamiento dinámico:**

Arranque 1.5x nominal (10s) superando viscosidad base

**Contexto operativo:**

Mezclador de resinas con perfiles de torque constante (Constant Torque). Criticidad: ESENCIAL

### MOT-016 — Motor IE4 + VFD (Cinta Clasificadora)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | SEW DRC |
| Potencia nominal | 30.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 46.0 A |
| Factor de potencia nominal | 0.97 |
| Fases | 3 |
| THD esperado | 25.0 % |

**Perfil de consumo:**

Operación: 16 h/día, 6 días/semana. Factor carga: 0.50

**Comportamiento dinámico:**

Arranque 1.5x nominal. Velocidad adaptativa según flujo logístico (sensores fotocélula)

**Contexto operativo:**

Centro de distribución e-commerce. Criticidad: FLEXIBLE

### MOT-017 — Motor IE4 + VFD + Active Filter (Bomba C)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB Drive + IE4 |
| Potencia nominal | 55.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 83.5 A |
| Factor de potencia nominal | 0.97 |
| Fases | 3 |
| THD esperado | 5.0 % (Con mitigación armónica IEEE 519) |

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.85

**Comportamiento dinámico:**

Arranque 1.2x nominal (20s)

**Contexto operativo:**

Bomba principal de red contraincendios / presurización crítica. Criticidad: CRITICA

### MOT-018 — Motor IE4 + VFD + AFE (Ventilador C)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Siemens G120 + Reluctance |
| Potencia nominal | 90.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 135.0 A |
| Factor de potencia nominal | 0.98 |
| Fases | 3 |
| THD esperado | <5.0 % (Active Front End) |

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.90

**Comportamiento dinámico:**

Arranque 1.2x nominal (25s)

**Contexto operativo:**

Tiro forzado de secadero industrial gigante. Criticidad: CRITICA

### MOT-019 — Motor IE4 + VFD (Extrusora de Plástico)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | WEG W22 Magnet |
| Potencia nominal | 160.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 240.0 A |
| Factor de potencia nominal | 0.98 |
| Fases | 3 |
| THD esperado | 4.0 % (AFE Incorporado) |

**Perfil de consumo:**

Operación: 24 h/día, 6 días/semana. Factor carga: 0.85

**Comportamiento dinámico:**

Arranque 1.5x nominal (30s) para vencer torque de arranque en material viscoso

**Contexto operativo:**

Producción de tubería HDPE; proceso de flujo constante y par alto a bajas RPM. Criticidad: CRITICA

### MOT-020 — Motor IE4 + VFD Centralizado (Main Drive)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ABB ACS880 + SynRM High Power |
| Potencia nominal | 315.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 470 A |
| Factor de potencia nominal | 0.98 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

Operación: 24 h/día, 7 días/semana. Factor carga: 0.95

**Comportamiento dinámico:**

Arranque 1.2x nominal (40s)

**Contexto operativo:**

Extractor de gases de horno en fundición metalúrgica. Regeneración al frenar. Criticidad: CRITICA

## Bombas y Sistemas Hidráulicos (15 equipos)

### BOMB-001 — Bomba Agua Procesos 1

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Grundfos CR 10 |
| Potencia nominal | 5.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 10.2 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 12 h/día, 7 días/semana
- Factor de carga promedio: 0.80
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Llenado de depósitos batch (ON 100%, OFF 0%).
- Fracción de tiempo: 0.5 ON, 0.5 OFF.

**Comportamiento dinámico:**

- Arranque: Directo, 6.0x nominal (2s).
- Standby: 0% ● Flexibilidad: sí (si el tanque pulmón tiene suficiente capacidad térmica/volumétrica).

**Contexto operativo:**

- Aplicación típica: Suministro de agua osmotizada a reactores.
- Criticidad: ESENCIAL

### BOMB-002 — Bomba Agua Procesos 2 (Respaldo)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Grundfos CR 10 (Redundancia) |
| Potencia nominal | 5.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 10.2 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 2 h/día (Ciclo de mantenimiento preventivo y testeo).
- Factor de carga promedio: 0.90
- Ciclos de trabajo: Mayormente inactiva.
- Fracción de tiempo: 0.08 ON, 0.92 OFF.

**Comportamiento dinámico:**

- Arranque: Directo, 6x.
- Standby: 0%
- Flexibilidad: sí

**Contexto operativo:**

- Aplicación típica: Redundancia N+1.
- Criticidad: ESENCIAL

### BOMB-003 — Bomba Alimentación Caldera 1

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | KSB Multitec |
| Potencia nominal | 18.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 33 A |
| Factor de potencia nominal | 0.87 |
| Fases | 3 |
| THD esperado | 2.5 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.75
- Variabilidad estacional: Aumenta la demanda de vapor en invierno.
- Ciclos de trabajo: Continua, manteniendo nivel en domo de caldera.
- Fracción de tiempo: 1.0 ON.

**Comportamiento dinámico:**

- Arranque: 5x nominal (arrancador suave).
- Standby: 0%
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Manejo de agua descalcificada a alta temperatura y alta presión (30 bar).
- Criticidad: CRITICA (si falla, detiene la producción de vapor).

### BOMB-004 — Bomba Alimentación Caldera 2

### BOMB-005 — Bomba Circulación Agua Helada (Primary Chilled Water)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Sulzer AHLSTAR (con VFD) |
| Potencia nominal | 45.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 68 A |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 20.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.70
- Variabilidad estacional: Perfectamente alineada con la demanda del chiller primario HVAC-001.
- Ciclos de trabajo: Regulación de flujo volumétrico mediante lazo PID midiendo presión diferencial (dP).
- Fracción de tiempo: 1.0 modulando.

**Comportamiento dinámico:**

- Arranque: 1.2x nominal (lento y controlado por VFD).
- Standby: 5% (frecuencia mínima).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Loop primario de climatización central.
- Criticidad: CRITICA.

### BOMB-006 — Bomba Circulación Condensados

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Sulzer CPT |
| Potencia nominal | 30.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 54 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.80
- Variabilidad estacional: Constante, dependiente del caudal torre de enfriamiento.
- Ciclos de trabajo: Caudal fijo.
- Fracción de tiempo: 1.0 ON.

### BOMB-007 — Grupo de Presión Principal (Booster Set Múltiple)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Grundfos Hydro MPC |
| Potencia nominal | 11.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 17 A |
| Factor de potencia nominal | 0.96 |
| Fases | 3 |
| THD esperado | 30.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.65
- Variabilidad estacional: Moderada.
- Ciclos de trabajo: Las bombas entran en cascada vía VFD según la demanda instantánea de las canillas/válvulas de la planta.
- Fracción de tiempo: Modulación estocástica constante.

**Comportamiento dinámico:**

- Arranque: Sin pico perceptible (Cascade inverter).
- Standby: 5%
- Flexibilidad: sí (en cierta medida compensada por el pulmón neumático).

**Contexto operativo:**

- Aplicación típica: Red de agua potable presurizada. Criticidad: CRITICA.

### BOMB-008 — Grupo de Presión Secundario (Agua Cruda)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | DAB Booster |
| Potencia nominal | 7.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 14 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % (DOL) |

**Perfil de consumo:**

Operación 10h/día. Carga: 0.60. Ciclos ON/OFF crudos guiados por presostato de vejiga

**Comportamiento dinámico:**

Arranque 6x (milisegundos)

**Contexto operativo:**

Suministro de riego y lavado bruto. Criticidad: ESENCIAL

### BOMB-009 — Equipo de Presión Lavado Alta Presión

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Kärcher HDS (Fija) |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 27 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 4.0 % |

**Perfil de consumo:**

- Operación: 4 h/día, 5 días/semana
- Factor de carga promedio: 0.95
- Variabilidad estacional: Ninguna.
- Ciclos de trabajo: Operado en ventanas estrictas al final del turno para sanitización (CIP / Washdown).
- Fracción de tiempo: 1.0 (en esas 4 hs).

### BOMB-010 — Bomba de Desplazamiento Positivo (Aceite Térmico)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Allweiler (Engranajes) |
| Potencia nominal | 22.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 40 A |
| Factor de potencia nominal | 0.86 |
| Fases | 3 |
| THD esperado | 2.5 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.85
- Variabilidad estacional: Mayor consumo en arranques fríos (viscosidad extrema).
- Ciclos de trabajo: Flujo volumétrico constante y alto par.
- Fracción de tiempo: 1.0 continua.

**Comportamiento dinámico:**

- Arranque: Alto torque estático (3x con Softstarter de Heavy-Duty).
- Standby: N/A
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Calentamiento de aceite diatérmico para marmitas. Criticidad: CRITICA.

### BOMB-011 — Bomba de Trasiego de Combustible (Fuel Oil)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Viking Pump |
| Potencia nominal | 4.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 7.8 A |
| Factor de potencia nominal | 0.82 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

Operación 2h/día, carga 0.80. Ciclos de reabastecimiento al tanque diario de calderas y generadores

**Comportamiento dinámico:**

Arranque 5x. Flexibilidad total (hasta agotar tanque diario)

**Contexto operativo:**

Cuarto de tanques. Criticidad: NO_CRITICA

### BOMB-012 — Bomba de Lóbulos Rotativos (Lodos)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Wangen Pumpen |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 27 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

Operación 16h/día. Carga: 0.90. Continua durante los turnos para evacuar fluido no newtoniano de los clarificadores

**Comportamiento dinámico:**

Arranque alto par

**Contexto operativo:**

Planta efluentes. Criticidad: ESENCIAL

### BOMB-013 — Bomba Dosificadora de Ácido (Membrana)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | ProMinent Gamma/ X |
| Potencia nominal | 0.75 kW |
| Voltaje | 230 V |
| Corriente nominal | 4.0 A |
| Factor de potencia nominal | 0.80 |
| Fases | 1 |
| THD esperado | 15.0 % (Electrónica integrada de pulsos) |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.30
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Inyecciones de micro-pulsos electromagnéticos dependientes del sensor de pH de la red.
- Fracción de tiempo: Modulación discreta estocástica.

**Comportamiento dinámico:**

- Arranque: Instantáneo sin pico inercial.
- Standby: 5% (pantalla).
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Ajuste de pH en torres de enfriamiento y reactores. Criticidad: CRITICA.

### BOMB-014 — Bomba Dosificadora de Soda Cáustica

### BOMB-015 — Bomba Dosificadora de Polímeros (Floculante)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Milton Roy (Motorizada) |
| Potencia nominal | 1.5 kW |
| Voltaje | 230 V |
| Corriente nominal | 8.1 A |
| Factor de potencia nominal | 0.80 |
| Fases | 1 |
| THD esperado | 10.0 % |

**Perfil de consumo:**

Operación 24h/día. Carga 0.50. Velocidad controlada por inverter mono a trifásico interno para viscosidades altas

**Comportamiento dinámico:**

Sin picos. Flexibilidad: Sí. Criticidad: ESENCIAL

## Iluminación Industrial (10 equipos)

### ILUM-001 — Circuito LED High Bay (Nave Principal)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Philips CoreLine HighBay (Lote agrupado de 20 un.) |
| Potencia nominal | 3.0 kW (Total circuito) |
| Voltaje | 230 V |
| Corriente nominal | 13.7 A |
| Factor de potencia nominal | 0.95 |
| Fases | 1 |
| THD esperado | 10.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 1.0
- Variabilidad estacional: Ninguna en naves sin luz natural.
- Ciclos de trabajo: Siempre encendido sin atenuación (No-Dimmable).
- Fracción de tiempo en cada estado: 1.0 ON.

**Comportamiento dinámico:**

- Arranque: Inrush current muy elevado por carga de capacitores (microsegundos, imperceptible en energía, relevante para breakers).
- Standby: 0%
- Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Iluminación a 10 metros de altura en piso de ensamble.
- Criticidad: CRITICA.

### ILUM-002 — Circuito LED High Bay (Almacén con control DALI)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Osram PrevaLED (Lote agrupado) |
| Potencia nominal | 2.0 kW |
| Voltaje | 230 V |
| Corriente nominal | 9.1 A |
| Factor de potencia nominal | 0.95 |
| Fases | 1 |
| THD esperado | 12.0 % |

**Perfil de consumo:**

- Operación: 24 h/día (Activo intermitente).
- Factor de carga promedio: 0.40
- Variabilidad estacional: Varía si hay lucernarios (Daylight harvesting).
- Ciclos de trabajo: Sensores de movimiento atenúan al 10% y suben al 100% cuando entra un autoelevador.
- Fracción de tiempo en cada estado: 0.2 (100%), 0.8 (10%).

### ILUM-003 — Tubos Fluorescentes T8 (Oficinas de Producción)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Genérico 2x36W con Balasto Electrónico (Lote) |
| Potencia nominal | 4.5 kW |
| Voltaje | 230 V |
| Corriente nominal | 21.7 A |
| Factor de potencia nominal | 0.90 |
| Fases | 1 |
| THD esperado | 15.0 % |

**Perfil de consumo:**

12 h/día, 5 días/semana. Factor de carga 1.0. Operación atada al horario del personal administrativo

**Contexto operativo:**

Tecnología de transición/obsoleta. Criticidad: NO_CRITICA

### ILUM-004 — Iluminación Exterior LED (Perímetro de Seguridad)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Schréder Ampera |
| Potencia nominal | 1.5 kW |
| Voltaje | 230 V |
| Corriente nominal | 6.6 A |
| Factor de potencia nominal | 0.98 |
| Fases | 1 |
| THD esperado | 8.0 % |

**Perfil de consumo:**

Operación 12h/día (promedio). Control fotocélula. Aumenta sus horas operativas en los meses de invierno. Factor de carga: 1.0. Criticidad: ESENCIAL

### ILUM-005 — Vapor de Sodio HPS (Patio de Maniobras Logístico)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Genérico 400W HPS (Lote de 20 campanas) |
| Potencia nominal | 8.0 kW |
| Voltaje | 230 V |
| Corriente nominal | 40.9 A |
| Factor de potencia nominal | 0.85 (Compensado) |
| Fases | 1 |
| THD esperado | 8.0 % |

**Perfil de consumo:**

12 h/día promedio nocturno. Factor de carga: 1.0

**Comportamiento dinámico:**

Requiere 15 minutos para alcanzar intensidad nominal y restrike time (tiempo de re-encendido). Carece de flexibilidad para apagados rápidos

**Contexto operativo:**

Iluminación masiva para carga y descarga exterior. Criticidad: ESENCIAL

### ILUM-006 — Circuito LED Cleanroom (IP65/Estanco)

### ILUM-007 — Iluminación de Inspección QC (Alta reproducción

### ILUM-008 — Sistema de Alumbrado de Emergencia (Centralizado)

### ILUM-009 — Focos Halógenos de Prueba Térmica

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Bancos resistivos de cuarzo infrarrojos |
| Potencia nominal | 5.0 kW |
| Voltaje | 230 V |
| Corriente nominal | 21.7 A |
| Factor de potencia nominal | 1.00 (Puramente resistivo) |
| Fases | 1 |
| THD esperado | 0.0 % |

**Perfil de consumo:**

Uso esporádico (4 h/día, 5 días/semana) en el área de I+D para curado térmico de muestras o stress tests. Criticidad: FLEXIBLE

### ILUM-010 — LED de Cultivo/Bioterio (Fotoperiodo estricto)

## Laboratorios y Equipos de Prueba (10 equipos)

### LAB-001 — Cámara Climática Farmacéutica (Mediana)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Memmert ICH26017 |
| Potencia nominal | 1.55 kW |
| Voltaje | 230 V |
| Corriente nominal | 6.7 A |
| Factor de potencia nominal | 0.98 |
| Fases | 1 |
| THD esperado | 5.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.60
- Variabilidad estacional: Aislado completamente del exterior.
- Ciclos de trabajo: Control PID rápido conectando resistencia (calor) y compresor R290 (frío) para mantener 40°C/75% RH.
- Fracción de tiempo en cada estado: Fluctuación termodinámica constante, sumando 60% de la energía máxima.

**Comportamiento dinámico:**

- Arranque: 2 minutos hasta estabilizar presiones.
- Standby: 10% (pantalla TwinDISPLAY operando). ● Flexibilidad: no

**Contexto operativo:**

- Aplicación típica: Estudios de estabilidad para cosmética o fármacos conforme a directrices ICH Q1A18.
- Criticidad: CRITICA (una interrupción eléctrica arruina estudios de meses).

### LAB-002 — Cámara Climática de Gran Volumen (Peltier)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Memmert HPP75019 |
| Potencia nominal | 1.05 kW (Tecnología termoeléctrica) |
| Voltaje | 230 V |
| Corriente nominal | 4.6 A |
| Factor de potencia nominal | 0.98 |
| Fases | 1 |
| THD esperado | 5.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.50
- Ciclos de trabajo: Intercambio de polaridad en celdas Peltier para frío/calor silencioso.
- Fracción de tiempo en cada estado: 1.0 (Corriente DC pulsante interna).

**Comportamiento dinámico:**

- Arranque: Totalmente suave (electrónico).
- Standby: 5% de nominal.
- Flexibilidad: no. Criticidad: CRITICA.

### LAB-003 — Horno Mufla de Alta Temperatura

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Nabertherm L 9/11 |
| Potencia nominal | 6.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 8.6 A |
| Factor de potencia nominal | 1.00 (Resistivo) |
| Fases | 3 |
| THD esperado | 0.0 % |

**Perfil de consumo:**

- Operación: 4 h/día, 3 días/semana
- Factor de carga promedio: 0.65
- Ciclos de trabajo: Rampa de calentamiento rápida a 1100°C (100% carga), seguido de meseta de mantenimiento (30% carga), y apagado térmico (0%).
- Fracción de tiempo en cada estado: 0.2 rampa, 0.8 meseta.

**Comportamiento dinámico:**

- Arranque: Sin pico inductivo (1.0x).
- Standby: 0% de nominal.
- Flexibilidad: sí (ensayos diferibles). Criticidad: ESENCIAL.

### LAB-004 — Banco de Ensayos Universales (Tracción)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Instron 5980 |
| Potencia nominal | 3.5 kW |
| Voltaje | 230 V |
| Corriente nominal | 17.8 A |
| Factor de potencia nominal | 0.85 |
| Fases | 1 |
| THD esperado | 15.0 % (Servomotores de precisión) |

**Perfil de consumo:**

- Operación: 6 h/día, 5 días/semana
- Factor de carga promedio: 0.40
- Ciclos de trabajo: Posicionamiento a baja carga, y picos de 1 segundo al punto de fractura del material (ruptura de probeta).
- Fracción de tiempo en cada estado: 0.8 standby productivo, 0.2 tracción activa.

**Comportamiento dinámico:**

- Arranque: Regeneración dinámica posible al retroceder el cabezal.
- Flexibilidad: sí. Criticidad: ESENCIAL.

### LAB-005 — Campana de Extracción de Gases (Fume Hood)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Waldner Secuflow |
| Potencia nominal | 1.5 kW |
| Voltaje | 230 V |
| Corriente nominal | 8.1 A |
| Factor de potencia nominal | 0.80 |
| Fases | 1 |
| THD esperado | 2.0 % |

**Perfil de consumo:**

- Operación: 10 h/día, 5 días/semana
- Factor de carga promedio: 0.90 ● Variabilidad estacional: Impacta indirectamente al robar aire climatizado del edificio.
- Ciclos de trabajo: Motor de extracción ON continuo mientras se opera con ácidos.
- Fracción de tiempo: 1.0 (en horas de uso).

### LAB-006 — Cromatógrafo HPLC

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Agilent 1260 Infinity II |
| Potencia nominal | 0.8 kW |
| Voltaje | 230 V |
| Corriente nominal | 3.6 A |
| Factor de potencia nominal | 0.95 |
| Fases | 1 |
| THD esperado | 5.0 % |

**Perfil de consumo:**

Operación 24h/día, 7 días/semana. Factor de carga 0.30. La inyección de muestras es puntual, la electrónica se mantiene purgando e iterando termostatos del horno de columnas. Standby largo consumiendo 80% del tiempo. Criticidad: ESENCIAL

### LAB-007 — Espectrómetro de Masas

### LAB-008 — Centrífuga Refrigerada de Piso

### LAB-009 — Autoclave de Esterilización

### LAB-010 — Incubadora CO2

## Equipos de Manufactura (10 equipos)

### MAN-001 — Centro de Torneado CNC

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Haas ST-1024 |
| Potencia nominal | 11.2 kW |
| Voltaje | 400 V |
| Corriente nominal | 19.5 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 12.0 % (Servos en ejes y husillo) |

**Perfil de consumo:**

- Operación: 16 h/día, 5 días/semana
- Factor de carga promedio: 0.45
- Variabilidad estacional: Nula. ● Ciclos de trabajo: Desbaste de metal (50%), Cambio de herramienta rápido (15%), Carga de nueva pieza en bruto (25%), Idle/Limpieza (10%).
- Fracción de tiempo: Altamente dinámico en segundos.

**Comportamiento dinámico:**

- Arranque: El husillo acelera a 4000 rpm en 2 segundos demandando 1.5x In a la red mediante su VFD interno25.
- Standby: 10% (pantallas, bombas de lubricación).
- Flexibilidad: sí (La orden de trabajo puede ejecutarse en otro turno).

**Contexto operativo:**

- Aplicación típica: Mecanizado de precisión en series medias. Criticidad: ESENCIAL.

### MAN-002 — Centro de Mecanizado Multitarea (Fresado/Torneado)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Mazak Integrex J-20026 |
| Potencia nominal | 18.5 kW |
| Voltaje | 400 V |
| Corriente nominal | 33.0 A |
| Factor de potencia nominal | 0.85 |
| Fases | 3 |
| THD esperado | 15.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 5 días/semana
- Factor de carga promedio: 0.55
- Ciclos de trabajo: Empleo simultáneo del husillo de torno y la fresadora superior en los 5 ejes, generando un consumo agregado fluctuante, atenuado por la función de standby integrada de la máquina (ahorra consumos de energía inactiva)27.
- Fracción de tiempo: Constante dinamismo según programa (código G).

### MAN-003 — Prensa Hidráulica (Conformado profundo)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Genérico 500 Toneladas |
| Potencia nominal | 45.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 79 A |
| Factor de potencia nominal | 0.82 |
| Fases | 3 |
| THD esperado | 2.5 % |

**Perfil de consumo:**

- Operación: 16 h/día, 5 días/semana
- Factor de carga promedio: 0.60
- Ciclos de trabajo: La bomba principal (carga base) mantiene la presión del tanque. El acumulador descarga la energía de forma cuasi-instantánea para el estampado, requiriendo que la bomba recupere la presión tras cada golpe.
- Fracción de tiempo: Bomba en vacío (60%), Bomba comprimiendo (40%).

### MAN-004 — Máquina de Inyección de Plástico

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Engel / Arburg |
| Potencia nominal | 75.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 120 A (Mixto reactivo/resistivo) |
| Factor de potencia nominal | 0.90 |
| Fases | 3 |
| THD esperado | 10.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 6 días/semana
- Factor de carga promedio: 0.70
- Ciclos de trabajo: Bandas calefactoras (resistivas, 40% de potencia) más motor plastificador y bomba de presión (inductivas, 60% potencia) inyectando a 1500 bar de forma cíclica (cada 15 a 60 segundos).
- Fracción de tiempo: Calor mantenido continuo. Motores ON/OFF.

### MAN-005 — Brazo Robótico de Soldadura

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Yaskawa Motoman |
| Potencia nominal | 8.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 14.5 A |
| Factor de potencia nominal | 0.80 |
| Fases | 3 |
| THD esperado | 20.0 % |

**Perfil de consumo:**

- Operación: 16 h/día, 5 días/semana
- Factor de carga promedio: 0.35
- Ciclos de trabajo: Posicionamiento veloz, pausa (1s), arco de soldadura pulsado MAG (alta intensidad, baja duración). Repetición.
- Fracción de tiempo: 0.6 Movimiento, 0.2 Arco de soldadura (gran potencia), 0.2 Standby.

### MAN-006 — Máquina de Corte Láser Fibra

### MAN-007 — Soldadora de Punto Estática

### MAN-008 — Extrusora de Aluminio

### MAN-009 — Máquina Paletizadora / Empacadora

### MAN-010 — Horno de Curado UV (Pintura/Tintas)

## Servidores y TI (5 equipos)

### TI-001 — Rack de Servidores Computación HPC

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Rack Clúster Genérico (ej. Dell/HPE mixto) |
| Potencia nominal | 15.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 22 A (Típicamente distribuido a 230V interno) |
| Factor de potencia nominal | 0.99 (PFC Activo) |
| Fases | 3 |
| THD esperado | 4.0 % |

**Perfil de consumo:**

- Operación: 24 h/día, 7 días/semana
- Factor de carga promedio: 0.85
- Variabilidad estacional: Nula.
- Ciclos de trabajo: Procesamiento en lote para simulaciones de gemelo digital de la fábrica, rindiendo la carga computacional muy alta y estable a nivel térmico.
- Fracción de tiempo: 1.0 operando.

### TI-002 — Rack de Telecomunicaciones (Switches y Routers)

### TI-003 — Sistema UPS Trifásico Central (Pérdidas operativas)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | APC Symmetra 100kVA |
| Potencia nominal | 6.0 kW (Pérdida por calor de rectificador/inversor) |
| Voltaje | 400 V |
| Corriente nominal | N/A (Se simula como disipación interna) |
| Factor de potencia nominal | 0.95 |
| Fases | 3 |
| THD esperado | 3.0 % |

**Perfil de consumo:**

Modela estrictamente la ineficiencia del inversor de estado sólido, operando 24/7. Agrega picos de recarga esporádicos luego de que la red flaquee, demandando potencia para reponer el amperaje de los bancos de baterías14. Criticidad: CRITICA

### TI-004 — Arreglo de Almacenamiento NAS/SAN

### TI-005 — Unidad de Monitoreo y Climatización de Baterías

## Equipos Auxiliares (5 equipos)

### AUX-001 — Ascensor de Pasajeros (Tracción VVVF)

**Especificaciones:**

| Campo | Valor |
|-------|-------|
| Fabricante/Modelo | Kone MonoSpace |
| Potencia nominal | 11.0 kW |
| Voltaje | 400 V |
| Corriente nominal | 18 A |
| Factor de potencia nominal | 0.90 |
| Fases | 3 |
| THD esperado | 15.0 % (VFD incorporado) |

**Perfil de consumo:**

- Operación: 24 h/día (Disponibilidad), pero solo acumula ~3 h/día efectivas de viajes.
- Factor de carga promedio: 0.30
- Ciclos de trabajo: Aceleración con VFD (consumo max), viaje crucero, y frenado regenerativo (devuelve energía a la red mediante resistencias o inversores KEB)13.
- Fracción de tiempo: 0.1 Viaje, 0.9 Standby (luces de cabina, puertas).

**Comportamiento dinámico:**

- Arranque: Completamente suavizado por VFD, sin impacto inductivo clásico.
- Standby: 10%
- Flexibilidad: no. Criticidad: ESENCIAL.

### AUX-002 — Montacargas Hidráulico de Carga Pesada

### AUX-003 — Cinta Transportadora de Línea de Ensamble

### AUX-004 — Portón Levadizo Automático (Andén Logístico)

### AUX-005 — Compactadora de Residuos (Baler)

## Tabla Resumen Consolidada (Formato CSV)

```
CSV)
Los datos detallados se recogen en esta matriz delimitada por el carácter pipe (|), compatible
con esquemas de importación tabular de simuladores de carga y motores de planeación
energética y optimización de micro-redes, facilitando el análisis en base a Energy Performance
Indicators (EnPIs)4.
Code snippet
r_carga|criticidad
HVAC-001|Chiller Centrifugo CVHE|HVAC industrial|350.0|400|3|0.85|24|7|0.75|CRITICA
HVAC-002|Chiller Aire 30KAV|HVAC industrial|180.0|400|3|0.95|16|6|0.65|ESENCIAL
HVAC-003|Chiller Tornillo EWWD|HVAC industrial|220.0|400|3|0.86|24|7|0.70|CRITICA
HVAC-004|Torre Enfriamiento BAC|HVAC industrial|45.0|400|3|0.84|24|7|0.80|CRITICA
HVAC-005|Torre Marley NC|HVAC industrial|30.0|400|3|0.83|16|6|0.70|ESENCIAL
HVAC-006|AHU York Solution|HVAC industrial|22.0|400|3|0.92|16|6|0.60|ESENCIAL
HVAC-007|AHU Cleanroom Flakt|HVAC industrial|15.0|400|3|0.94|24|7|0.85|CRITICA
HVAC-008|VRF Mitsubishi City Multi|HVAC industrial|56.0|400|3|0.96|12|5|0.55|FLEXIBLE
HVAC-009|CRAC Vertiv Liebert|HVAC industrial|40.0|400|3|0.93|24|7|0.80|CRITICA
HVAC-010|In-Row Schneider|HVAC industrial|12.0|400|3|0.95|24|7|0.75|CRITICA
HVAC-011|Fan Coil Carrier 42CT|HVAC industrial|2.2|230|1|0.88|12|5|0.65|NO_CRITICA
HVAC-012|Fan Coil Daikin|HVAC industrial|0.85|230|1|0.85|10|5|0.50|NO_CRITICA
HVAC-013|Rooftop Trane Voyager|HVAC industrial|35.0|400|3|0.87|14|6|0.68|ESENCIAL
HVAC-014|Climatizador Seeley|HVAC industrial|7.5|400|3|0.82|10|6|0.70|FLEXIBLE
HVAC-015|Deshumectador Munters|HVAC industrial|28.0|400|3|0.91|24|7|0.82|CRITICA
HVAC-016|Extractora Ex Systemair|HVAC industrial|18.5|400|3|0.85|24|7|0.78|ESENCIAL
HVAC-017|Chiller Stulz CyberCool|HVAC industrial|90.0|400|3|0.88|16|6|0.62|ESENCIAL
HVAC-018|Geotermia WaterFurnace|HVAC industrial|42.0|400|3|0.89|12|7|0.58|FLEXIBLE
HVAC-019|Cortina Thermoscreens|HVAC industrial|18.0|400|3|0.95|12|5|0.80|NO_CRITICA
HVAC-020|Condensadora Guntner|HVAC industrial|15.0|400|3|0.84|24|7|0.65|ESENCIAL
COMP-001|Compresor VSD Atlas Copco|Compresores y
neumatica|90.0|400|3|0.95|24|7|0.65|CRITICA
COMP-002|Compresor Fijo Kaeser|Compresores y
neumatica|75.0|400|3|0.85|16|5|0.85|ESENCIAL
COMP-003|Compresor Ingersoll Rand|Compresores y
neumatica|160.0|400|3|0.85|24|6|0.90|CRITICA
COMP-004|Compresor Sullair LS90|Compresores y
neumatica|90.0|400|3|0.85|8|5|0.50|FLEXIBLE
COMP-005|Compresor Boge C20|Compresores y
neumatica|15.0|400|3|0.84|12|5|0.70|NO_CRITICA
COMP-006|Compresor CompAir L45|Compresores y
neumatica|45.0|400|3|0.85|16|5|0.65|ESENCIAL
COMP-007|Centrifugo Atlas Copco ZH|Compresores y
neumatica|350.0|400|3|0.86|24|7|0.95|CRITICA
COMP-008|Centrifugo FS-Elliott|Compresores y
neumatica|250.0|400|3|0.86|24|6|0.88|CRITICA
COMP-009|Piston Booster Kaeser|Compresores y
neumatica|22.0|400|3|0.85|10|5|0.50|ESENCIAL
COMP-010|Piston Taller Quincy|Compresores y
neumatica|11.0|400|3|0.83|8|5|0.40|NO_CRITICA
COMP-011|Bomba Vacio Busch|Compresores y neumatica|18.5|400|3|0.85|24|6|0.80|CRITICA
COMP-012|Bomba Vacio Leybold|Compresores y neumatica|7.5|400|3|0.83|12|5|0.70|ESENCIAL
COMP-013|Vacio Seca Edwards GXS|Compresores y
neumatica|15.0|400|3|0.90|24|7|0.60|CRITICA
COMP-014|Soplador Aerzen Delta|Compresores y
neumatica|37.0|400|3|0.85|24|7|0.85|CRITICA
COMP-015|Soplador Gardner Denver|Compresores y
neumatica|22.0|400|3|0.85|16|6|0.75|ESENCIAL
MOT-001|Motor IE3 Bomba 1|Motores electricos|0.75|400|3|0.78|16|5|0.80|ESENCIAL
MOT-002|Motor IE3 Extractor|Motores electricos|1.5|400|3|0.80|16|5|0.70|ESENCIAL
MOT-003|Motor IE3 Agitador|Motores electricos|3.0|400|3|0.82|16|5|0.65|ESENCIAL
MOT-004|Motor IE3 Reductor|Motores electricos|5.5|400|3|0.84|16|5|0.85|ESENCIAL
MOT-005|Motor IE3 Ventilador|Motores electricos|11.0|400|3|0.86|24|7|0.90|CRITICA
MOT-006|Motor IE3 Compresor|Motores electricos|22.0|400|3|0.87|16|5|0.75|ESENCIAL
MOT-007|Motor IE3 Molino A|Motores electricos|45.0|400|3|0.88|24|6|0.95|CRITICA
MOT-008|Motor IE3 Molino B|Motores electricos|75.0|400|3|0.88|24|6|0.90|CRITICA
MOT-009|Motor IE3 Trituradora|Motores electricos|160.0|400|3|0.89|16|5|0.85|CRITICA
MOT-010|Motor IE3 Cinta Carga|Motores electricos|500.0|400|3|0.89|24|7|0.80|CRITICA
MOT-011|Motor IE4 VFD Bomba A|Motores electricos|1.5|400|3|0.95|16|6|0.60|FLEXIBLE
MOT-012|Motor IE4 VFD Bomba B|Motores electricos|2.2|400|3|0.95|16|6|0.65|FLEXIBLE
MOT-013|Motor IE4 VFD Fan A|Motores electricos|5.5|400|3|0.96|24|7|0.75|FLEXIBLE
MOT-014|Motor IE4 VFD Fan B|Motores electricos|11.0|400|3|0.96|24|7|0.80|ESENCIAL
MOT-015|Motor IE4 VFD Mixer|Motores electricos|18.5|400|3|0.97|16|5|0.70|ESENCIAL
MOT-016|Motor IE4 VFD Cinta|Motores electricos|30.0|400|3|0.97|16|6|0.50|FLEXIBLE
MOT-017|Motor IE4 VFD Bomba C|Motores electricos|55.0|400|3|0.97|24|7|0.85|CRITICA
MOT-018|Motor IE4 VFD Fan C|Motores electricos|90.0|400|3|0.98|24|7|0.90|CRITICA
MOT-019|Motor IE4 VFD Extrusor|Motores electricos|160.0|400|3|0.98|24|6|0.85|CRITICA
MOT-020|Motor IE4 VFD Main|Motores electricos|315.0|400|3|0.98|24|7|0.95|CRITICA
BOMB-001|Bomba Grundfos CR 1|Bombas e hidraulica|5.5|400|3|0.85|12|7|0.80|ESENCIAL
BOMB-002|Bomba Grundfos CR 2|Bombas e hidraulica|5.5|400|3|0.85|2|7|0.90|ESENCIAL
BOMB-003|Bomba KSB Caldera 1|Bombas e hidraulica|18.5|400|3|0.87|24|7|0.75|CRITICA
BOMB-004|Bomba KSB Caldera 2|Bombas e hidraulica|18.5|400|3|0.87|24|7|0.75|CRITICA
BOMB-005|Bomba Sulzer Chilled|Bombas e hidraulica|45.0|400|3|0.95|24|7|0.70|CRITICA
BOMB-006|Bomba Sulzer Condens|Bombas e hidraulica|30.0|400|3|0.86|24|7|0.80|ESENCIAL
BOMB-007|Grupo Presion Principal|Bombas e hidraulica|11.0|400|3|0.96|24|7|0.65|CRITICA
BOMB-008|Grupo Presion Secundario|Bombas e hidraulica|7.5|400|3|0.85|10|7|0.60|ESENCIAL
BOMB-009|Equipo Presion Lavado|Bombas e hidraulica|15.0|400|3|0.86|4|5|0.95|FLEXIBLE
BOMB-010|Bomba Aceite Termico|Bombas e hidraulica|22.0|400|3|0.86|24|7|0.85|CRITICA
BOMB-011|Bomba Trasiego Fuel|Bombas e hidraulica|4.0|400|3|0.82|2|5|0.80|NO_CRITICA
BOMB-012|Bomba Lobulos Wangen|Bombas e hidraulica|15.0|400|3|0.85|16|6|0.90|ESENCIAL
BOMB-013|Dosificadora Acido|Bombas e hidraulica|0.75|230|1|0.80|24|7|0.30|CRITICA
BOMB-014|Dosificadora Soda|Bombas e hidraulica|0.75|230|1|0.80|24|7|0.30|CRITICA
BOMB-015|Dosificadora Floculante|Bombas e hidraulica|1.5|230|1|0.80|24|7|0.50|ESENCIAL
ILUM-001|LED HighBay Principal|Iluminacion industrial|3.0|230|1|0.95|24|7|1.00|CRITICA
ILUM-002|LED HighBay Almacen|Iluminacion industrial|2.0|230|1|0.95|24|7|0.40|FLEXIBLE
ILUM-003|Fluorescente T8 Oficinas|Iluminacion industrial|4.5|230|1|0.90|12|5|1.00|NO_CRITICA
ILUM-004|LED Exterior Perimetro|Iluminacion industrial|1.5|230|1|0.98|12|7|1.00|ESENCIAL
ILUM-005|Sodio HPS Patio|Iluminacion industrial|8.0|230|1|0.85|12|7|1.00|ESENCIAL
ILUM-006|LED Cleanroom|Iluminacion industrial|2.5|230|1|0.95|24|7|1.00|CRITICA
ILUM-007|LED Inspeccion QC|Iluminacion industrial|1.0|230|1|0.95|8|5|1.00|ESENCIAL
ILUM-008|Alumbrado Emergencia|Iluminacion industrial|0.5|230|1|0.90|24|7|1.00|CRITICA
ILUM-009|Halogenos Prueba Termica|Iluminacion industrial|5.0|230|1|1.00|4|5|1.00|FLEXIBLE
ILUM-010|LED Cultivo Bioterio|Iluminacion industrial|1.2|230|1|0.95|12|7|1.00|CRITICA
LAB-001|Camara Memmert ICH260|Laboratorios|1.55|230|1|0.98|24|7|0.60|CRITICA
LAB-002|Camara Memmert HPP750|Laboratorios|1.05|230|1|0.98|24|7|0.50|CRITICA
LAB-003|Horno Mufla|Laboratorios|6.0|400|3|1.00|4|3|0.65|ESENCIAL
LAB-004|Banco Ensayo Universal|Laboratorios|3.5|230|1|0.85|6|5|0.40|ESENCIAL
LAB-005|Campana Extraccion|Laboratorios|1.5|230|1|0.80|10|5|0.90|ESENCIAL
LAB-006|Cromatografo HPLC|Laboratorios|0.8|230|1|0.95|24|7|0.30|ESENCIAL
LAB-007|Espectrometro Masas|Laboratorios|2.0|230|1|0.90|24|7|0.80|CRITICA
LAB-008|Centrifuga Refrigerada|Laboratorios|2.5|230|1|0.85|4|5|0.60|ESENCIAL
LAB-009|Autoclave Esterilizacion|Laboratorios|9.0|400|3|1.00|4|5|0.80|CRITICA
LAB-010|Incubadora CO2|Laboratorios|0.6|230|1|0.98|24|7|0.20|CRITICA
MAN-001|Torno CNC Haas ST-10|Equipos manufactura|11.2|400|3|0.85|16|5|0.45|ESENCIAL
MAN-002|Centro Mazak Integrex|Equipos manufactura|18.5|400|3|0.85|16|5|0.55|CRITICA
MAN-003|Prensa Hidraulica|Equipos manufactura|45.0|400|3|0.82|16|5|0.60|ESENCIAL
MAN-004|Inyectora Plastico|Equipos manufactura|75.0|400|3|0.90|24|6|0.70|CRITICA
MAN-005|Brazo Robot Soldadura|Equipos manufactura|8.0|400|3|0.80|16|5|0.35|ESENCIAL
MAN-006|Corte Laser Fibra|Equipos manufactura|30.0|400|3|0.90|16|5|0.80|CRITICA
MAN-007|Soldadora Punto|Equipos manufactura|60.0|400|3|0.80|16|5|0.10|ESENCIAL
MAN-008|Extrusora Aluminio|Equipos manufactura|110.0|400|3|0.95|16|5|0.85|CRITICA
MAN-009|Paletizadora|Equipos manufactura|5.5|400|3|0.85|16|5|0.50|NO_CRITICA
MAN-010|Horno Curado UV|Equipos manufactura|22.0|400|3|0.95|8|5|1.00|ESENCIAL
TI-001|Rack HPC|Servidores y TI|15.0|400|3|0.99|24|7|0.85|CRITICA
TI-002|Rack Telecom|Servidores y TI|5.0|230|1|0.98|24|7|0.70|CRITICA
TI-003|UPS Symmetra 100kVA|Servidores y TI|6.0|400|3|0.95|24|7|1.00|CRITICA
TI-004|Storage SAN NAS|Servidores y TI|3.5|230|1|0.98|24|7|0.90|CRITICA
TI-005|Climatizacion Baterias|Servidores y TI|2.0|230|1|0.95|24|7|0.60|CRITICA
AUX-001|Ascensor Kone|Equipos auxiliares|11.0|400|3|0.90|24|7|0.30|ESENCIAL
AUX-002|Montacargas Hidraulico|Equipos auxiliares|22.0|400|3|0.82|24|6|0.15|FLEXIBLE
AUX-003|Cinta Transportadora|Equipos auxiliares|4.0|400|3|0.85|16|6|0.70|ESENCIAL
AUX-004|Porton Logistico|Equipos auxiliares|1.5|230|1|0.75|24|6|0.10|NO_CRITICA
AUX-005|Compactadora Residuos|Equipos auxiliares|5.5|400|3|0.80|2|5|0.80|FLEXIBLE
```

## Bibliografía

1. [8760 Energy Model - Greensleeves Tech](https://www.greensleevestech.com/8760-energy-model/)
2. [8760 Hourly Energy Analysis Benefits | PDF | Hvac | Air Conditioning](https://www.scribd.com/document/355432124/811-584-pdf)
3. [Energy Standard for Data Centers - ASHRAE](https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90_4_2022_g_20240131.pdf)
4. [ISO 50001 energy planning software | HOMER Pro & HOMER Grid](https://homerenergy.com/iso-50001/)
5. [Energy Baseline (EnB) in ISO 50001: How to Define It and Use It in](https://audit-advisor.com/en/iso-information-portal/2r24uj8841-energy-baselineenb-in-iso-50001-how-to)
6. [Motor Efficiency Classes IE1 IE2 IE3 IE4: 4 Essential IEC 60034 Facts](https://www.instrumentationblog.in/motor-efficiency-classes-iec-60034/)
7. [What Is IE3 and IE4 Motor Efficiency? | IEC 60034-30-1 Guide](https://www.4q-systems.com/what-is-ie3-and-ie4-motor-efficiency/)
8. [IE3 vs IE4 Motors: Efficiency Classes Explained (IEC 60034-30-1)](https://www.fabrico.io/blog/ie3-vs-ie4-motor-efficiency/)
9. [IEEE 519 THD Compliance at VFD MCC Bus: Assessment Guide](https://industrialmonitordirect.com/blogs/knowledgebase/ieee-519-thd-compliance-at-vfd-mcc-bus-assessment-guide)
10. [Understanding Harmonics in Power Systems: IEEE 519 Explained](https://www.rexpowermagnetics.com/knowledge-hub/understanding-harmonics-in-power-systems-ieee-519-guidelines-explained/)
11. [IEEE 519 Harmonic Limits Explained: What Your VFDs Are Doing to](https://softnitro.com/ieee-519-harmonic-limits-explained/)
12. [IEEE 519 Harmonic Distortion Limits: Guide to Compliance](https://www.ytelect.com/blog/ieee-519-harmonic-distortion-limits-guide-to-compliance_b337)
13. [IEEE 519-2022 Review What has changed from the previous 2014](https://library.e.abb.com/public/a7965e127ce44d089c1c2beace68aacd/Tech_Note_158_IEEE_519-2022+Review.pdf?x-sign=zoeBsqxVX1a1WQ9vQYQrE4QVCzmBlxU9j64YbBFzBlEyK3FfqtL6aBzK5ErAXQXD)
14. [Electrical Load Calculation Explained — kW, kVA & Demand Factor](https://mepmasterguide.com/electrical-load-calculation-explained/)
15. [Electric motors - IEC](https://iec.ch/government-regulators/electric-motors)
16. [ANSI/ASHRAE/IES Standard 90.1-2019 Performance Rating Method](https://www.energycodes.gov/sites/default/files/2023-12/90_1_2019_Appendix_G_PRM_2023.11.pdf)
17. [DS_Memmert Climate chamber ICH260 - Memmert GmbH](https://www.memmert.com/en/products/climate-chambers/climate-chamber/ich260-2/pdf)
18. [Memmert compressor-cooled stability test chamber](https://www.memmert-ce.com/products/climate-chamber-compressor-ich-memmert/)
19. [Memmert Climate Chambers english D13643 - Hettich Labinstrument](https://www.hettichlabinstrument.se/wp-content/uploads/2017/06/BR-Climate-Chambers-english-D13643.pdf)
20. [Climate chamber for stability testing ICH750L - vol. 769 litres](https://www.memmert.com/en/products/climate-chambers/climate-chamber/ich750l-2)
21. [Memmert Climate chamber - OMC Limited](https://www.omcbd.com/product/memmert-climate-chamber/)
22. [IEEE 399 – Recommended Practice for Industrial and Commercial](https://filipinoengineer.com/blog/2022/08/ieee-399-recommended-practice-for-industrial-and-commercial-power-systems-analysis.html)
23. [IEEE Std 399 Brown Book: Is the 1997 Version Still Valid?](https://industrialmonitordirect.com/blogs/knowledgebase/ieee-std-399-brown-book-for-power-system-coordination-studies)
24. [Haas ST-10 CNC Lathe Specifications | PDF - Scribd](https://www.scribd.com/document/538350331/ST-10Y-Datasheet)
25. [torque hhaas chart](https://www.haascnc.com/content/dam/haascnc/productivity/spindles/torque-chart-jpg/torque-chart-machine-pdp-binder-/UMC-1000SS%20Torque%20Binder.pdf)
26. [Multi-Tasking Machines INTEGREX j-200 NEO - Products](https://www.mazak.com/eu-en/products/integrex-j-200-neo/)
27. [Mazak-HCN-Brochure.pdf](https://www.cottandco.com/media/upload/Mazak-HCN-Brochure.pdf)
28. [Power factor: Technical overview | Eskom](https://www.eskom.co.za/eas/wp-content/uploads/2021/05/POWER-FACTOR-TECHNICAL-OVERVIEW.pdf)
29. [Power Factor Formula (PF = kW ÷ kVA) with Examples - CalcPanel](https://calcpanel.com/guides/power-factor-guide)
30. [Energy performance indicators: ISO 50001 strategies - Gradhoc](https://gradhoc.com/Art%C3%ADculo/industrial-energy-efficiency-indicators/)