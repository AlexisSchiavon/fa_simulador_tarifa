# Modelo de Datos — Hyperred FA Sandbox

## Diagrama ER (simplificado)

```
rutas (R1..R5)
  │
  ├──< viajes (1 ruta → N viajes)
  │       │
  │       └──< boletos (1 viaje → N boletos)
  │               │
  │               └──< servicios_boleto (1 boleto → N servicios)
  │                           │
  │                           └──> servicios_adicionales (SA1..SA5)
  │
  └──< escenarios
          │
          └──< boletos (1 escenario → N boletos, nullable)
```

## Tablas

### `rutas`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | VARCHAR(10) PK | "R1"–"R5" |
| origen | VARCHAR(100) | Ciudad de origen |
| destino | VARCHAR(100) | Ciudad de destino |
| distancia_km | INTEGER | Kilómetros |
| tarifa_base_mxn | NUMERIC(10,2) | Precio base del algoritmo |
| tipo_servicio | ENUM | Regular/Plus/Coordinado/Alimentador/Ejecutivo |
| created_at | DATETIME | |

### `viajes`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK autoincrement | |
| ruta_id | FK → rutas.id | |
| fecha_salida | DATETIME | Fecha y hora programada |
| capacidad | INTEGER | Default: 45 |
| nivel_demanda | ENUM | valle/normal/alta/temporada |
| estado | ENUM | programado/en_curso/completado/cancelado |
| created_at | DATETIME | |

### `boletos`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK autoincrement | |
| viaje_id | FK → viajes.id | |
| precio_pagado_mxn | NUMERIC(10,2) | Precio final cobrado |
| multiplicador_aplicado | NUMERIC(6,4) | M = P / T_base |
| clase_tarifaria | ENUM | E/S/P/X |
| segmento_pasajero | ENUM | ocio/negocios |
| factores_desglose | JSON | {f_ocu, f_ant, f_dem, f_seg, f_lix} |
| fecha_compra_simulada | DATETIME | Momento de la compra simulada |
| dias_anticipacion | INTEGER | Días desde compra hasta salida |
| estado | ENUM | activo/cancelado/buyback |
| modelo_usado | ENUM | aviacion/flixbus/hibrido |
| escenario_id | FK → escenarios.id (nullable) | |
| created_at | DATETIME | |

### `servicios_boleto`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK autoincrement | |
| boleto_id | FK → boletos.id | |
| servicio_id | FK → servicios_adicionales.id | |
| precio_pagado_mxn | NUMERIC(10,2) | Precio del servicio en el momento de compra |
| tier | ENUM | base/superior |
| created_at | DATETIME | |

### `servicios_adicionales` (catálogo, seed)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | VARCHAR(10) PK | "SA1"–"SA5" |
| nombre | VARCHAR(200) | Nombre del servicio |
| descripcion | TEXT | Descripción larga |
| precio_base_mxn | NUMERIC(10,2) | |
| precio_superior_mxn | NUMERIC(10,2) | Tier premium |
| adopcion_ocio_pct | NUMERIC(5,4) | % adoptará en segmento ocio |
| adopcion_negocios_pct | NUMERIC(5,4) | % adoptará en segmento negocios |

### `escenarios`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK autoincrement | |
| nombre | VARCHAR(200) | Nombre del escenario guardado |
| descripcion | TEXT nullable | |
| modelo_principal | ENUM | aviacion/flixbus/hibrido |
| ruta_id | FK → rutas.id | |
| parametros_iniciales | JSON | Config inicial del escenario |
| ingreso_total_mxn | NUMERIC(12,2) | Computed al guardar |
| num_boletos | INTEGER | Computed al guardar |
| created_at | DATETIME | |

## Índices recomendados

```sql
CREATE INDEX idx_viajes_ruta_fecha ON viajes(ruta_id, fecha_salida);
CREATE INDEX idx_boletos_viaje ON boletos(viaje_id);
CREATE INDEX idx_boletos_escenario ON boletos(escenario_id);
CREATE INDEX idx_servicios_boleto ON servicios_boleto(boleto_id);
```

Los índices se gestionan vía Alembic en producción.
