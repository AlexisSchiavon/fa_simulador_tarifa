# Hyperred FA Sandbox

**Simulador de Tarificación Dinámica Híbrida para Flecha Amarilla**

Sandbox profesional que implementa y demuestra el algoritmo de tarificación
híbrida diseñado para Grupo Flecha Amarilla (GFA) — combinando lo mejor de la
aviación (clases tarifarias + Revenue Management) con lo mejor de Flixbus
(escalamiento dinámico por ocupación + descuento de último momento).

> **GENIE S.C. × Lumixia · Proyecto Hyperred 25061 · 2026**

---

## Características principales

- **Simulador interactivo**: vende boletos uno a uno y observa el precio cambiar
  en tiempo real con desglose completo de factores
- **Comparador de modelos**: Aviación puro vs. Flixbus puro vs. Híbrido FA lado a lado
- **Seat Buyback**: simula la recompra de asientos con compensación al pasajero
- **Servicios adicionales Hyperred**: 5 add-ons basados en disposición a pagar real
- **Modo Presentación**: 3 actos automatizados para reuniones con stakeholders
- **Exportación a Excel**: reporte profesional multi-hoja del escenario
- **5 rutas reales**: corredor León – Silao – Irapuato – Querétaro

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI + Pydantic v2 |
| Base de datos | SQLite + SQLAlchemy 2.0 |
| Migraciones | Alembic |
| Frontend | HTMX + Alpine.js + Tailwind CSS (CDN) |
| Gráficos | Plotly (interactivos) |
| Exportación | openpyxl |
| Gestión de deps | uv |
| Servidor | uvicorn |

---

## Instalación

### Con `uv` (recomendado)

```bash
# 1. Instalar uv si no lo tienes
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 2. Clonar/entrar al directorio del proyecto
cd fa_simulador_tarifa

# 3. Instalar dependencias
uv sync

# 4. (Opcional) Crear migraciones iniciales con Alembic
uv run alembic upgrade head

# 5. Arrancar el servidor
uv run uvicorn app.main:app --reload
```

### Con `pip`

```bash
# 1. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Instalar dependencias
pip install -e ".[dev]"

# 3. Arrancar
uvicorn app.main:app --reload
```

### Variables de entorno

```bash
cp .env.example .env
# El archivo .env.example contiene todos los defaults necesarios.
# No se requiere configuración adicional para el sandbox local.
```

---

## Uso

Abre http://localhost:8000 en tu navegador. La base de datos se crea y el
seed se carga automáticamente al primer arranque.

| Ruta | Descripción |
|------|-------------|
| `/dashboard` | Vista general con las 5 rutas y próximos viajes |
| `/simulador` | Venta de boletos con precio dinámico en tiempo real |
| `/comparador` | Los 3 modelos lado a lado |
| `/escenarios` | Historial de simulaciones guardadas |
| `/presentacion` | Modo presentación para reuniones |
| `/docs` | Documentación automática de la API (FastAPI/Swagger) |
| `/health` | Estado del servicio |

---

## Estructura del proyecto

```
fa_simulador_tarifa/
├── app/
│   ├── main.py               # Entry point FastAPI
│   ├── config.py             # Settings con pydantic-settings
│   ├── database.py           # SQLAlchemy + sesión
│   ├── models/               # Modelos ORM
│   │   ├── ruta.py
│   │   ├── viaje.py
│   │   ├── boleto.py
│   │   ├── servicio_adicional.py
│   │   └── escenario.py
│   ├── schemas/              # Pydantic schemas (Fase 3)
│   ├── core/
│   │   ├── pricing_engine.py ⭐  # Motor de tarificación (Fase 2)
│   │   ├── models_comparacion.py
│   │   ├── seat_buyback.py
│   │   └── revenue_simulator.py
│   ├── api/routes/           # Endpoints FastAPI
│   ├── services/             # Lógica de negocio
│   ├── templates/            # HTML Jinja2
│   ├── static/               # CSS, JS, imágenes
│   └── seed/                 # Datos iniciales
├── tests/                    # pytest
├── docs/                     # Documentación técnica
├── alembic/                  # Migraciones de BD
├── pyproject.toml
└── alembic.ini
```

---

## Algoritmo de Tarificación Híbrida

```
P(t) = T_base × f_ocu(O) × f_ant(A) × f_dem(D) × f_seg(S) × f_lix(A,O)
```

**Sujeto a**: `P_min = T_base × 0.65` y `P_max = T_base × 3.50`

| Factor | Descripción | Rango |
|--------|-------------|-------|
| `f_ocu` | Ocupación actual del autobús | 0.85 – 2.00 |
| `f_ant` | Días de anticipación a la compra | 0.80 – 1.80 |
| `f_dem` | Nivel de demanda histórico (valle/normal/alta/temporada) | 0.90 – 1.45 |
| `f_seg` | Segmento del pasajero (ocio/negocios) | 0.95 – 1.25 |
| `f_lix` | Descuento último momento (Flixbus-style) | 0.72 / 1.00 |

Ver documentación completa en [docs/ALGORITMO.md](docs/ALGORITMO.md).

---

## Clases Tarifarias

| Clase | Nombre | Multiplicador | % Inventario |
|-------|--------|--------------|--------------|
| **E** | Económica | 0.65× – 1.00× | 30% |
| **S** | Estándar | 1.00× – 1.35× | 40% |
| **P** | Plus | 1.35× – 2.00× | 20% |
| **X** | Ejecutiva | 2.00× – 3.50× | 10% |

---

## Rutas del Sandbox (seed)

| ID | Origen | Destino | km | Tarifa Base | Tipo |
|----|--------|---------|----|------------|------|
| R1 | León | Querétaro | 160 | $380 | Plus |
| R2 | León | Irapuato | 50 | $140 | Regular |
| R3 | Irapuato | Querétaro | 110 | $280 | Plus |
| R4 | León | Silao | 30 | $90 | Alimentador |
| R5 | Silao | Querétaro | 130 | $320 | Plus |

---

## Roadmap

### Fase 2 — Core del algoritmo (siguiente)
- [ ] `app/core/pricing_engine.py` — motor puro con los 3 modelos
- [ ] Tests exhaustivos del pricing engine (15+ casos)
- [ ] `app/core/seat_buyback.py`
- [ ] `docs/ALGORITMO.md` completo

### Fase 3 — API completa
- [ ] Schemas Pydantic en `app/schemas/`
- [ ] Endpoints completos de simulación (vender, guardar, escenarios)
- [ ] Endpoint de comparación con generador de escenario aleatorio
- [ ] Exportación a Excel multi-hoja

### Fase 4 — Frontend pulido
- [ ] Dashboard con gráficos reales (datos de BD)
- [ ] Simulador completamente funcional end-to-end
- [ ] Comparador con datos reales del pricing engine
- [ ] Modo presentación con datos reales

### Fase 5 — Pulido
- [ ] Animaciones y transiciones
- [ ] Responsive (tablet)
- [ ] Tests de integración

---

## Tests

```bash
uv run pytest                          # todos los tests
uv run pytest tests/test_pricing_engine.py  # solo el motor
uv run pytest --cov=app                # con cobertura
```

---

## Linting / Formateo

```bash
uv run ruff check app/                 # linting
uv run ruff format app/                # auto-format
uv run black app/                      # formatter alternativo
```

---

*GENIE S.C. × Lumixia · Proyecto Hyperred 25061 · 2026*
