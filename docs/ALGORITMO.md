# Algoritmo de Tarificación Dinámica Híbrida — Hyperred FA

## Fórmula Principal

```
P(t) = T_base × f_ocu(O) × f_ant(A) × f_dem(D) × f_seg(S) × f_lix(A,O)
```

**Restricciones absolutas (clamp final):**
- `P_min = T_base × 0.65` (piso — solo activable vía f_lix)
- `P_max = T_base × 3.50` (techo duro)

---

## Factor f_ocu — Ocupación

**Inspiración:** Revenue Management de aviación comercial.

El precio sube conforme se reduce la disponibilidad. A mayor ocupación,
mayor escasez de asientos → mayor precio marginal.

```
O ∈ [0.0, 0.4):  f_ocu = 0.85 + (O / 0.4) × 0.15        → [0.85, 1.00]
O ∈ [0.4, 0.7):  f_ocu = 1.00 + ((O - 0.4) / 0.3) × 0.30 → [1.00, 1.30]
O ∈ [0.7, 0.9):  f_ocu = 1.30 + ((O - 0.7) / 0.2) × 0.35 → [1.30, 1.65]
O ∈ [0.9, 1.0]:  f_ocu = 1.65 + ((O - 0.9) / 0.1) × 0.35 → [1.65, 2.00]
```

**Interpretación por tramos:**
- 0–40% ocupación: bus casi vacío, leve descuento de atracción (−15% base)
- 40–70%: tramo de precio "normal" que sube gradualmente (+30%)
- 70–90%: aceleración del precio al acercarse a la venta total (+35% adicional)
- 90–100%: últimos asientos, precio premium máximo (2×)

---

## Factor f_ant — Anticipación

**Inspiración:** Gestión de inventario de aerolíneas (Early Bird vs. Walk-up).

Premia la compra anticipada y penaliza la compra de último momento.

```
A > 30:        f_ant = 0.80 + ((A - 30) / 60) × 0.15  → [0.80, 0.95]
A ∈ [8, 30]:   f_ant = 1.00                            → 1.00 (neutro)
A ∈ [2, 8):    f_ant = 1.15 + ((8 - A) / 6) × 0.25   → [1.15, 1.40]
A < 2:         f_ant = 1.65 + ((2 - A) / 2) × 0.15   → [1.65, 1.80]
```

donde A = días hasta la fecha de salida.

**Nota de diseño:** La curva de A > 30 tiene pendiente suave porque FA tiene
baja penetración de compra muy anticipada. El escalón más importante es el
tramo A < 2 que refleja demanda inelástica de pasajeros urgentes.

---

## Factor f_dem — Demanda Histórica

**Inspiración:** Modelos de revenue management con estacionalidad.

Basado en el análisis del repositorio FA (archivos de ocupación histórica).

| Nivel | f_dem | Contexto |
|-------|-------|----------|
| `valle` | 0.90 | Temporada baja, días laborales de mitad de semana |
| `normal` | 1.00 | Operación ordinaria |
| `alta` | 1.20 | Viernes/domingo, temporada vacacional media |
| `temporada` | 1.45 | Semana Santa, Navidad, eventos masivos |

---

## Factor f_seg — Segmento del Pasajero

**Inspiración:** Segmentación de aerolíneas (leisure vs. business).

| Segmento | f_seg | Característica |
|----------|-------|----------------|
| `ocio` | 0.95 | Precio-sensible; compra con anticipación |
| `negocios` | 1.25 | Urgente; menor sensibilidad al precio |

---

## Factor f_lix — Descuento Último Momento

**Inspiración directa:** Algoritmo de Flixbus para reducir desperdicios de
capacidad cuando el bus parte con asientos vacíos.

```
Si A == 0 (mismo día, < 4h) Y O < 0.60:  f_lix = 0.72
En cualquier otro caso:                   f_lix = 1.00 (inactivo)
```

**Regla crítica de override:** cuando `f_lix` está activo, `f_ant = 1.00`.
Razón: no tiene sentido aplicar la penalidad de última hora (`f_ant` alto)
simultáneamente con el descuento de último momento (`f_lix` bajo). El
descuento de Flixbus domina.

---

## Clases Tarifarias

Se derivan del multiplicador total `M = f_ocu × f_ant × f_dem × f_seg × f_lix`:

| Clase | Multiplicador | % Inventario | Color |
|-------|--------------|--------------|-------|
| E — Económica | 0.65 – 1.00× | 30% | Azul `#378ADD` |
| S — Estándar | 1.00 – 1.35× | 40% | Verde `#639922` |
| P — Plus | 1.35 – 2.00× | 20% | Ámbar `#BA7517` |
| X — Ejecutiva | 2.00 – 3.50× | 10% | Coral `#D85A30` |

El porcentaje de inventario es orientativo; en la implementación actual no
hay control de inventario por clase (se reserva para v2 con overbooking real).

---

## Modelos Comparativos

### Modelo Aviación Puro
```
P_av = T_base × f_ocu × f_ant × f_dem
```
Sin segmentación de pasajero y sin descuento Flixbus.

### Modelo Flixbus Puro
```
P_flix = T_base × f_ocu × f_lix'
donde f_lix' = 0.65 si activo (más agresivo que el híbrido)
```
Foco único en ocupación como driver de precio.

### Modelo Híbrido FA
Fórmula completa con los 5 factores. Combina:
- La sofisticación de la anticipación (aviación)
- La agresividad en ocupación (Flixbus)
- La segmentación de pasajero (aerolíneas)
- El descuento inteligente de última hora (Flixbus)
- La corrección por demanda histórica (FA propio)

---

## Seat Buyback

Cuando `O > 70%` y existen boletos Clase E activos:

1. El sistema ofrece al pasajero: `compensación = precio_pagado × 1.5 + $200`
2. Probabilidad de aceptación simulada:
   - Segmento ocio: 70%
   - Segmento negocios: 30%
3. Si acepta: el asiento se libera y puede revenderse a Clase X (precio máximo)
4. Si rechaza: no hay cambio

---

## Servicios Adicionales (Hyperred)

Add-ons basados en la tabla de disposición a pagar real del taller Hyperred
GFA (abril 2026):

| ID | Servicio | Precio Base | Precio Superior | Adopción Ocio | Adopción Neg. |
|----|----------|-------------|-----------------|---------------|---------------|
| SA1 | Zona Ejecutiva | $134 | $269 | 22% | 58% |
| SA2 | Zona Mujer/Menores | $127 | $255 | 50% | 51% |
| SA3 | Taxi Garantizado | $160 | $319 | 18% | 58% |
| SA4 | Traslado Mascota | $243 | $486 | 4% | 20% |
| SA5 | Casillero Electrónico | $85 | $170 | 10% | 25% |

El ingreso de servicios se suma al ingreso del boleto para el cálculo del
RPK (Revenue Per Kilometer) y el ingreso total del viaje.
