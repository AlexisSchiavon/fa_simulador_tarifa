# Concepto Hyperred — FA como Orquestador del Viaje Completo

## ¿Qué es Hyperred?

Hyperred es el marco estratégico bajo el cual Flecha Amarilla evoluciona de
ser una empresa de transporte de punto A a punto B, a convertirse en el
**orquestador de la experiencia de viaje completa** de sus pasajeros.

El nombre hace referencia a una red hipermediada: FA en el centro,
conectando ecosistemas de valor antes, durante y después del viaje.

---

## Problema que Resuelve

FA opera actualmente con tarifa fija por OD (par Origen-Destino), sin
diferenciación de precio según:
- Momento de compra (anticipación)
- Nivel de ocupación del servicio
- Tipo de demanda (estacional, evento especial)
- Perfil del pasajero (precio-sensible vs. urgente)
- Valor agregado del servicio (clase de asiento, servicios adicionales)

Esto genera ineficiencia de ingresos por dos vías:
1. **Dinero dejado sobre la mesa**: pasajeros que pagarían más en días de
   alta demanda pagan la misma tarifa que en días de baja ocupación.
2. **Asientos vacíos evitables**: no hay mecanismo para "mover" precio
   cuando el bus parte con capacidad ociosa.

---

## El Modelo Híbrido como Habilitador

El algoritmo de tarificación dinámica híbrida (Aviación + Flixbus) resuelve
el problema de la ineficiencia de ingresos. Pero la visión Hyperred va más
allá: el precio dinámico del boleto es solo la capa base.

**Capas de valor Hyperred:**

```
Capa 1: Tarificación dinámica (este sandbox)
         ↓
Capa 2: Servicios premium en el autobús (SA1–SA5)
         ↓
Capa 3: Servicios en destino (taxi, hotel, tours)
         ↓
Capa 4: Ecosistema de movilidad multimodal
         (FA conectada con última milla, ferroviario, etc.)
```

---

## Servicios Adicionales Identificados (Taller Hyperred, Abril 2026)

Los 5 servicios incluidos en el sandbox tienen sustento empírico:
fueron identificados y validados en el taller Hyperred GFA de abril 2026,
donde se midió disposición a pagar real de usuarios FA del corredor León-Qro.

**Hallazgos clave del taller:**
- La zona mujer/menores tiene la mayor adopción entre segmento ocio (50%)
- El taxi garantizado es el servicio más valorado por viajeros de negocios (58%)
- Zona Ejecutiva genera el mayor ticket adicional por pasajero en segmento Plus
- El traslado de mascotas tiene baja adopción pero precio premium (WTP $243–$486)

---

## Impacto Proyectado (Corredor León–Querétaro)

Comparando modelo actual (tarifa fija) vs. Híbrido FA con servicios:

| Métrica | Tarifa Fija | Híbrido FA | Mejora |
|---------|-------------|------------|--------|
| Ingreso por bus lleno (R1, demanda normal) | $17,100 | ~$24,000–$28,000 | +40–65% |
| Ingreso por bus lleno + servicios | $17,100 | ~$28,000–$35,000 | +65–105% |
| Ingreso con ocupación 70% + f_lix | $11,970 | ~$14,500 | +21% |

*Estimaciones basadas en el simulador con patrones típicos de venta.*

---

## Roadmap Estratégico Hyperred

### Fase 0 (actual): Prueba de concepto
- Sandbox de tarificación dinámica (este proyecto)
- Demostración a stakeholders GFA

### Fase 1: Piloto técnico
- Integración con sistemas de venta de FA (TPV, app)
- Implementación en 1–2 rutas piloto
- ML para predicción de demanda (reemplaza f_dem manual)

### Fase 2: Escala regional
- Roll-out a corredor completo León–Querétaro
- Servicios adicionales (SA1–SA5) en autobuses seleccionados
- Dashboard operativo para revenue management

### Fase 3: Ecosistema Hyperred
- API pública para integradores (Uber, Didi, hoteles)
- Programa de fidelización de pasajeros
- Coordinación multimodal con otros operadores

---

*GENIE S.C. × Lumixia · Proyecto Hyperred 25061 · 2026*
