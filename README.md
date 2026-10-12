# Simulador de Maquinaria Industrial - Siemens Spacewise

Sistema de simulación energética de maquinaria industrial con 110 equipos, generación de perfiles horarios (8760h), persistencia SQLite, backend Flask y panel web con visualización Chart.js.

## Características

- **Motor de simulación MATLAB**: Genera perfiles de consumo horario para 110 máquinas industriales
- **Catálogo de equipos**: 110 equipos con especificaciones eléctricas y perfiles de consumo
- **Persistencia SQLite**: Almacena máquinas, simulaciones, mediciones horarias y resultados
- **Backend Flask API**: Endpoints REST para consultar datos y exportar resultados
- **Panel web**: Visualización interactiva con Chart.js (gráficos horarios, por categoría, top consumidores)
- **Exportación**: CSV y JSON con filtros por fecha
- **Importación**: Comparación con datos reales (CSV/Excel)

## Requisitos

### MATLAB
- MATLAB R2026a o superior
- Database Toolbox (para SQLite)
- Agregar `matlab/bin` al PATH o definir `MATLAB_BIN`

### Python
- Python 3.9+
- Dependencias en `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

## Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone <repo-url>
   cd Siemens-Spacewise
   ```

2. **Instalar dependencias Python**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verificar MATLAB**:
   ```bash
   matlab -batch "disp('MATLAB OK')"
   ```

## Uso

### 1. Ejecutar simulación completa (pipeline MATLAB)

```bash
python orquestador.py
```

Esto ejecuta en orden:
- `init_db.m`: Crea la base de datos SQLite con el esquema
- `load_catalog.m`: Carga el catálogo de 110 máquinas
- `run_simulation.m`: Ejecuta simulación de 8760 horas
- `export_results.m`: Exporta resultados a CSV

### 2. Iniciar backend web

```bash
cd web/backend
python app.py
```

El servidor se inicia en `http://localhost:5000`

### 3. Acceder al panel web

Abrir en el navegador:
```
http://localhost:5000
```

O abrir directamente:
```
web/frontend/index.html
```

## Estructura del proyecto

```
Siemens-Spacewise/
├── docs/
│   ├── CATALOGO_EQUIPOS.md       # Catálogo de 110 equipos
│   └── SIMULADOR_MAQUINARIA.md   # Especificaciones técnicas
├── matlab/
│   ├── config/
│   │   └── simulacion_params.m   # Parámetros de simulación
│   ├── src/
│   │   ├── sim_catalog.m         # Parser del catálogo
│   │   ├── sim_engine.m          # Motor de simulación
│   │   ├── sim_machine.m         # Perfil individual de máquina
│   │   ├── sim_db.m              # Capa SQLite
│   │   ├── sim_analysis.m        # Análisis y agregación
│   │   └── sim_export.m          # Exportación CSV/Excel
│   ├── scripts/
│   │   ├── init_db.m             # Inicializar base de datos
│   │   ├── load_catalog.m        # Cargar catálogo
│   │   ├── run_simulation.m      # Ejecutar simulación
│   │   └── export_results.m      # Exportar resultados
│   └── tests/
│       ├── test_sim_catalog.m    # Tests del parser
│       ├── test_sim_machine.m    # Tests de perfiles
│       ├── test_sim_engine.m     # Tests del motor
│       └── test_sim_db.m         # Tests de base de datos
├── web/
│   ├── backend/
│   │   ├── app.py                # Aplicación Flask
│   │   ├── routes.py             # Endpoints API
│   │   ├── queries.py            # Consultas SQL parametrizadas
│   │   └── tests/
│   │       └── test_api.py       # Tests del backend (28 tests)
│   └── frontend/
│       ├── index.html            # Panel principal
│       ├── js/
│       │   ├── api.js            # Cliente API
│       │   └── charts.js         # Visualizaciones Chart.js
│       └── css/
│           └── styles.css        # Estilos
├── data/
│   ├── spacewise.db              # Base de datos SQLite
│   └── export/                   # Resultados exportados
├── tests/
│   └── test_integration.py       # Tests de integración
├── orquestador.py                # Orquestador del pipeline MATLAB
└── requirements.txt              # Dependencias Python
```

## API Endpoints

### Máquinas
- `GET /api/machines` - Lista todas las máquinas
- `GET /api/machines/<code>` - Detalle de una máquina

### Simulaciones
- `GET /api/simulations` - Lista simulaciones
- `GET /api/simulations/<id>/summary` - Resumen de simulación
- `GET /api/simulations/<id>/hourly` - Totales horarios
- `GET /api/simulations/<id>/machines/<code>` - Mediciones de máquina
- `GET /api/simulations/<id>/export?format=csv&start=...&end=...` - Exportar datos

### Salud
- `GET /health` - Estado del servidor

## Testing

### Tests MATLAB
```bash
cd matlab/tests
matlab -batch "runtests"
```

### Tests Python Backend
```bash
cd web/backend
pytest tests/ -v
```

### Tests de Integración
```bash
python -m pytest tests/test_integration.py -v
```

## Seguridad

- **SQL parametrizado**: Todas las consultas usan placeholders (`?`)
- **Validación de inputs**: Machine codes, IDs, fechas validados con regex
- **CORS**: Configurado con orígenes explícitos
- **Sin stack traces**: Errores genéricos en producción
- **Variables de entorno**: Configuración sensible en `.env`

## Documentación adicional

- `docs/CATALOGO_EQUIPOS.md` - Catálogo completo de 110 equipos
- `docs/SIMULADOR_MAQUINARIA.md` - Especificaciones técnicas del simulador
- `docs/archive/` - Documentación del proyecto anterior (gemelo digital)

## Estado del proyecto

✅ Motor de simulación MATLAB completo  
✅ Persistencia SQLite funcional  
✅ Tests unitarios (13 MATLAB + 28 Python)  
✅ Backend Flask API  
✅ Panel web con visualizaciones  
✅ Exportación CSV/JSON  
✅ Documentación actualizada  

## Licencia

Proyecto interno Siemens Spacewise.

## Contacto

Para consultas sobre el simulador, contactar al equipo de desarrollo.
