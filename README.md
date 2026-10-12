# Spacewise
Proyecto enfocado para el programa Siemens.

```
Siemens-Spacewise/
├── docs/              → Documentación (PDFs + Markdown)
├── matlab/
│   ├── config/        → spacewise_params.m (parámetros editables)
│   ├── src/           → 7 clases MATLAB (dt_*)
│   ├── scripts/       → 4 scripts de orquestación
│   ├── tests/         → 3 clases de unittest (13 tests)
│   └── output/        → Resultados de simulaciones (ya poblado)
├── orquestador.py     → Llama a MATLAB desde Python
├── requirements.txt   → (vacío, solo comentarios)
└── .gitignore
```

## NUEVOS REQUERIMIENTOS
Dada la falta de atencion y paticipacion  por el CEN, se modificara la finalidad del proyecto, siendo lo principal
cambiar a simulacion y comparacion. El nuevo enfoque es es simular sobre maquinaria especififica y consumos. Mas al area industrial y centro de investigacion.
Buscamos tener una base de almenos 100 maquinas y poder simular su comportamiento y consumo, para poder comparar y analizar los resultado, puediendo agregar mas en u futuro siguiendo
una estructura modular -> Cada carpeta de simulacion sera una maquina o equipo a simular.

### Requerimientos especificos
- [ ] Modificar estructura base de matlab para utilizar nuevo enfoque y arquitectura modular.
- [ ] Definir estructura para los archivos de simulacion, tipod e datos y entrega.
- [ ] Guardado de datos en base de datos local, sqlite de momento.
- [ ] Panel html que muestre los consumos totales (suma de todos), parciales (eligiendo que mauquina sumar) y individual (por cada maquina). FGraficos en timepo o comparativos.
- [ ] Opción en panel que permita cargar un archivo .xlsx o .csv (especificar que solo estas opciones) para hacer comparaciones de consumo y comportamientos.
- [ ] Opcion de exportar datos dgenerados en la simulacion por timepos. (1 semana, 1 dia, 1 mes, 1, año o rango personalizado.)

### Nuevo objetivo
Tener un panel comparador en el que visualizar puntos e interes quepermitan un ahorro o mejoras energeticas.
