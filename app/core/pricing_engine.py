"""
Motor de tarificación dinámica híbrida — Hyperred FA.

Este módulo es PURO: no tiene dependencias de base de datos ni de FastAPI.
Recibe valores escalares y retorna resultados estructurados.
Esto facilita testing unitario exhaustivo y reusabilidad en simulaciones batch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ── Constantes del algoritmo ──────────────────────────────────────────────────

PRICE_FLOOR_MULTIPLIER = 0.65
PRICE_CEILING_MULTIPLIER = 3.50

DEMAND_FACTORS: dict[str, float] = {
    "valle": 0.90,
    "normal": 1.00,
    "alta": 1.20,
    "temporada": 1.45,
}

SEGMENT_FACTORS: dict[str, float] = {
    "ocio": 0.95,
    "negocios": 1.25,
}

# Límites de clases tarifarias por multiplicador
CLASE_THRESHOLDS = [
    ("E", 0.65, 1.00),   # Económica
    ("S", 1.00, 1.35),   # Estándar
    ("P", 1.35, 2.00),   # Plus
    ("X", 2.00, 3.50),   # Ejecutiva
]

Modelo = Literal["hibrido", "aviacion", "flixbus", "ado", "japi"]
NivelDemanda = Literal["valle", "normal", "alta", "temporada"]
Segmento = Literal["ocio", "negocios"]


# ── Tipos de retorno ──────────────────────────────────────────────────────────

@dataclass
class FactoresDesglose:
    """Desglose de cada factor multiplicador aplicado."""

    f_ocu: float
    f_ant: float
    f_dem: float
    f_seg: float
    f_lix: float

    def as_dict(self) -> dict[str, float]:
        return {
            "f_ocu": round(self.f_ocu, 4),
            "f_ant": round(self.f_ant, 4),
            "f_dem": round(self.f_dem, 4),
            "f_seg": round(self.f_seg, 4),
            "f_lix": round(self.f_lix, 4),
        }


@dataclass
class ResultadoPrecio:
    """Resultado completo del cálculo de precio."""

    precio: float
    multiplicador: float
    clase: str
    factores: FactoresDesglose
    tarifa_base: float
    modelo: Modelo
    clamped: bool = False

    @property
    def precio_sin_servicios(self) -> float:
        return self.precio

    def as_dict(self) -> dict:
        return {
            "precio": round(self.precio, 2),
            "multiplicador": round(self.multiplicador, 4),
            "clase": self.clase,
            "factores": self.factores.as_dict(),
            "tarifa_base": self.tarifa_base,
            "modelo": self.modelo,
            "clamped": self.clamped,
        }


# ── Funciones de cada factor ──────────────────────────────────────────────────

def calcular_f_ocu(ocupacion: float) -> float:
    """Factor de ocupación — sube el precio conforme se llena el bus.

    Args:
        ocupacion: fracción de asientos ocupados, en [0.0, 1.0].

    Returns:
        Multiplicador f_ocu en [0.85, 2.00].
    """
    o = max(0.0, min(1.0, ocupacion))
    if o < 0.4:
        return 0.85 + (o / 0.4) * 0.15
    if o < 0.7:
        return 1.00 + ((o - 0.4) / 0.3) * 0.30
    if o < 0.9:
        return 1.30 + ((o - 0.7) / 0.2) * 0.35
    return 1.65 + ((o - 0.9) / 0.1) * 0.35


def calcular_f_ant(dias_anticipacion: int) -> float:
    """Factor de anticipación — premia compra temprana, penaliza tardía.

    Args:
        dias_anticipacion: días desde la compra hasta la fecha de salida.

    Returns:
        Multiplicador f_ant en [0.80, 1.80].
    """
    a = max(0, dias_anticipacion)
    if a > 30:
        return 0.80 + min((a - 30) / 60, 1.0) * 0.15
    if a >= 8:
        return 1.00
    if a >= 2:
        return 1.15 + ((8 - a) / 6) * 0.25
    # 0 ≤ a < 2
    return 1.65 + ((2 - a) / 2) * 0.15


def calcular_f_dem(nivel_demanda: str) -> float:
    """Factor de demanda histórica.

    Args:
        nivel_demanda: "valle" | "normal" | "alta" | "temporada".

    Returns:
        Multiplicador f_dem según tabla FA.

    Raises:
        ValueError: si el nivel no es válido.
    """
    if nivel_demanda not in DEMAND_FACTORS:
        raise ValueError(
            f"Nivel de demanda inválido: '{nivel_demanda}'. "
            f"Válidos: {list(DEMAND_FACTORS.keys())}"
        )
    return DEMAND_FACTORS[nivel_demanda]


def calcular_f_seg(segmento: str) -> float:
    """Factor de segmento — diferencia ocio vs. negocios.

    Args:
        segmento: "ocio" | "negocios".

    Returns:
        Multiplicador f_seg.

    Raises:
        ValueError: si el segmento no es válido.
    """
    if segmento not in SEGMENT_FACTORS:
        raise ValueError(
            f"Segmento inválido: '{segmento}'. "
            f"Válidos: {list(SEGMENT_FACTORS.keys())}"
        )
    return SEGMENT_FACTORS[segmento]


def calcular_f_lix(dias_anticipacion: int, ocupacion: float, agresivo: bool = False) -> float:
    """Descuento de último momento al estilo Flixbus.

    Activo solo cuando: mismo día (A == 0) Y ocupación < 60%.
    Cuando está activo, f_ant debe anularse (= 1.0).

    Args:
        dias_anticipacion: días hasta la salida.
        ocupacion: fracción de asientos ocupados.
        agresivo: si True, usa 0.65 (modelo Flixbus puro); si False, 0.72 (híbrido).

    Returns:
        0.72 (o 0.65 si agresivo) si condiciones se cumplen, 1.00 si no.
    """
    if dias_anticipacion == 0 and ocupacion < 0.60:
        return 0.65 if agresivo else 0.72
    return 1.00


def clasificar_boleto(multiplicador: float) -> str:
    """Asigna clase tarifaria según el multiplicador final.

    Args:
        multiplicador: P / T_base (puede estar fuera de [0.65, 3.50] antes del clamp).

    Returns:
        "E", "S", "P", o "X".
    """
    m = max(PRICE_FLOOR_MULTIPLIER, multiplicador)
    for clase, lo, hi in CLASE_THRESHOLDS:
        if m < hi:
            return clase
    return "X"  # >= 2.00 (o en el límite exacto de 3.50)


# ── Motor principal ───────────────────────────────────────────────────────────

def calcular_precio(
    tarifa_base: float,
    ocupacion: float,
    dias_anticipacion: int,
    nivel_demanda: str = "normal",
    segmento: str = "ocio",
    modelo: Modelo = "hibrido",
    inventario_clases: dict | None = None,
) -> ResultadoPrecio:
    """Calcula el precio dinámico según el modelo seleccionado.

    Fórmula híbrida completa:
        P = T_base × f_ocu × f_ant × f_dem × f_seg × f_lix
        con clamp a [T_base × 0.65, T_base × 3.50]

    Args:
        tarifa_base: precio base de la ruta (MXN).
        ocupacion: fracción de asientos ocupados, en [0.0, 1.0].
        dias_anticipacion: días desde la compra hasta la salida.
        nivel_demanda: "valle" | "normal" | "alta" | "temporada".
        segmento: "ocio" | "negocios".
        modelo: "hibrido" | "aviacion" | "flixbus".

    Returns:
        ResultadoPrecio con precio, multiplicador, clase y desglose de factores.
    """
    if tarifa_base <= 0:
        raise ValueError(f"tarifa_base debe ser positiva, recibido: {tarifa_base}")

    f_ocu = calcular_f_ocu(ocupacion)
    f_ant_raw = calcular_f_ant(dias_anticipacion)
    f_dem = calcular_f_dem(nivel_demanda)
    f_seg = calcular_f_seg(segmento)
    f_lix = calcular_f_lix(dias_anticipacion, ocupacion, agresivo=False)

    if modelo == "hibrido":
        # Override: si f_lix activo, f_ant se anula
        f_ant = 1.00 if f_lix < 1.00 else f_ant_raw
        multiplicador = f_ocu * f_ant * f_dem * f_seg * f_lix

    elif modelo == "aviacion":
        # Solo ocupación + anticipación + demanda; sin f_seg ni f_lix
        f_ant = f_ant_raw
        f_dem_av = f_dem
        f_seg = 1.00
        f_lix = 1.00
        multiplicador = f_ocu * f_ant * f_dem_av

    elif modelo == "flixbus":
        # Solo ocupación + f_lix agresivo; sin anticipación ni demanda
        f_ant = 1.00
        f_dem = 1.00
        f_seg = 1.00
        f_lix = calcular_f_lix(dias_anticipacion, ocupacion, agresivo=True)
        multiplicador = f_ocu * f_lix

    elif modelo == "ado":
        # Anticipación + demanda + markup de marca; sin f_ocu, f_seg, f_lix
        f_ocu = 1.00
        f_ant = f_ant_raw
        f_seg = 1.00
        f_lix = 1.00
        multiplicador = f_ant * f_dem * 1.05

    elif modelo == "japi":
        # Precio fijo "barato por diseño"; sin ningún factor dinámico
        f_ocu = 1.00
        f_ant = 1.00
        f_dem = 1.00
        f_seg = 1.00
        f_lix = 1.00
        multiplicador = 0.72

    else:
        raise ValueError(f"Modelo desconocido: '{modelo}'. Válidos: hibrido, aviacion, flixbus, ado, japi")

    precio_raw = tarifa_base * multiplicador
    p_min = tarifa_base * PRICE_FLOOR_MULTIPLIER
    p_max = tarifa_base * (2.20 if modelo == "ado" else PRICE_CEILING_MULTIPLIER)

    clamped = precio_raw < p_min or precio_raw > p_max
    precio_final = max(p_min, min(p_max, precio_raw))
    multiplicador_final = precio_final / tarifa_base

    factores = FactoresDesglose(
        f_ocu=f_ocu,
        f_ant=f_ant,
        f_dem=f_dem,
        f_seg=f_seg,
        f_lix=f_lix,
    )

    clase = clasificar_boleto(multiplicador_final)

    if inventario_clases is not None:
        _ORDEN = ["E", "S", "P", "X"]
        _MIN_MULT = {"S": 1.00, "P": 1.35, "X": 2.00}
        idx = _ORDEN.index(clase)
        while idx < len(_ORDEN) - 1 and inventario_clases.get(_ORDEN[idx], 1) == 0:
            idx += 1
        target = _ORDEN[idx]
        if target != clase:
            if inventario_clases.get(target, 1) == 0:  # X también agotada
                precio_final = round(tarifa_base * PRICE_CEILING_MULTIPLIER, 2)
                multiplicador_final = PRICE_CEILING_MULTIPLIER
            else:
                multiplicador_final = _MIN_MULT[target]
                precio_final = round(tarifa_base * multiplicador_final, 2)
            clase = target
            clamped = True

    return ResultadoPrecio(
        precio=round(precio_final, 2),
        multiplicador=round(multiplicador_final, 4),
        clase=clase,
        factores=factores,
        tarifa_base=tarifa_base,
        modelo=modelo,
        clamped=clamped,
    )
