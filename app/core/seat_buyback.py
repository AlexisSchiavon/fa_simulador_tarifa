"""Lógica de Seat Buyback — recompra de asientos con compensación al pasajero."""
from __future__ import annotations

import random
from dataclasses import dataclass

BUYBACK_MULTIPLIER = 1.5      # compensación = precio_pagado × 1.5
BUYBACK_BONUS_MXN = 200.0     # bono fijo adicional
ACCEPT_PROB_OCIO = 0.70       # pasajeros de ocio aceptan con más frecuencia
ACCEPT_PROB_NEGOCIOS = 0.30   # pasajeros de negocios raramente aceptan


@dataclass
class OfertaBuyback:
    boleto_id: int
    precio_pagado: float
    segmento: str
    compensacion: float
    acepta: bool


def calcular_compensacion(precio_pagado: float) -> float:
    """Calcula la compensación ofrecida al pasajero.

    Returns:
        precio_pagado × 1.5 + $200 bono.
    """
    return round(precio_pagado * BUYBACK_MULTIPLIER + BUYBACK_BONUS_MXN, 2)


def simular_respuesta(segmento: str, seed: int | None = None) -> bool:
    """Simula si el pasajero acepta o rechaza la oferta de buyback.

    Args:
        segmento: "ocio" | "negocios".
        seed: semilla para reproducibilidad en tests.

    Returns:
        True si el pasajero acepta.
    """
    rng = random.Random(seed)
    prob = ACCEPT_PROB_OCIO if segmento == "ocio" else ACCEPT_PROB_NEGOCIOS
    return rng.random() < prob


def procesar_buyback(
    boleto_id: int,
    precio_pagado: float,
    segmento: str,
    seed: int | None = None,
) -> OfertaBuyback:
    """Procesa una oferta de buyback para un boleto Clase E.

    Args:
        boleto_id: ID del boleto a recomprar.
        precio_pagado: precio original pagado por el pasajero.
        segmento: "ocio" | "negocios".
        seed: semilla aleatoria para reproducibilidad.

    Returns:
        OfertaBuyback con resultado de la simulación.
    """
    compensacion = calcular_compensacion(precio_pagado)
    acepta = simular_respuesta(segmento, seed=seed)
    return OfertaBuyback(
        boleto_id=boleto_id,
        precio_pagado=precio_pagado,
        segmento=segmento,
        compensacion=compensacion,
        acepta=acepta,
    )


def es_candidato_buyback(clase_tarifaria: str, ocupacion: float) -> bool:
    """Determina si un boleto es candidato para buyback.

    Criterios: clase E (económica) y viaje con ocupación > 70%.

    Args:
        clase_tarifaria: "E", "S", "P", o "X".
        ocupacion: fracción de asientos ocupados (0.0–1.0).

    Returns:
        True si cumple los criterios.
    """
    return clase_tarifaria == "E" and ocupacion > 0.70
