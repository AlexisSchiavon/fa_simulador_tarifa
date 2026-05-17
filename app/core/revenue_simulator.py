"""
Simulador de ingresos — genera secuencias de venta realistas para comparación
y para el modo presentación.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.core.pricing_engine import (
    ResultadoPrecio,
    calcular_precio,
)


@dataclass
class EventoVenta:
    """Representa una venta individual dentro de una simulación."""

    num: int
    dias_anticipacion: int
    segmento: str
    nivel_demanda: str
    resultado: ResultadoPrecio
    ingreso_servicios: float = 0.0

    @property
    def ingreso_total(self) -> float:
        return self.resultado.precio + self.ingreso_servicios


@dataclass
class ResultadoSimulacion:
    """Resultado completo de simular N ventas en un viaje."""

    modelo: str
    ruta_id: str
    tarifa_base: float
    capacidad: int
    eventos: list[EventoVenta] = field(default_factory=list)

    @property
    def num_boletos(self) -> int:
        return len(self.eventos)

    @property
    def ingreso_boletos(self) -> float:
        return sum(e.resultado.precio for e in self.eventos)

    @property
    def ingreso_servicios(self) -> float:
        return sum(e.ingreso_servicios for e in self.eventos)

    @property
    def ingreso_total(self) -> float:
        return self.ingreso_boletos + self.ingreso_servicios

    @property
    def precio_promedio(self) -> float:
        if not self.eventos:
            return 0.0
        return self.ingreso_boletos / len(self.eventos)

    @property
    def precio_minimo(self) -> float:
        if not self.eventos:
            return 0.0
        return min(e.resultado.precio for e in self.eventos)

    @property
    def precio_maximo(self) -> float:
        if not self.eventos:
            return 0.0
        return max(e.resultado.precio for e in self.eventos)

    @property
    def serie_precios(self) -> list[float]:
        return [e.resultado.precio for e in self.eventos]

    def as_dict(self) -> dict:
        return {
            "modelo": self.modelo,
            "ingreso_total": round(self.ingreso_total, 2),
            "ingreso_boletos": round(self.ingreso_boletos, 2),
            "ingreso_servicios": round(self.ingreso_servicios, 2),
            "precio_promedio": round(self.precio_promedio, 2),
            "precio_minimo": round(self.precio_minimo, 2),
            "precio_maximo": round(self.precio_maximo, 2),
            "num_boletos": self.num_boletos,
            "serie_precios": [round(p, 2) for p in self.serie_precios],
        }


def _patron_anticipacion_realista(
    num_boletos: int,
    dias_hasta_salida: int,
    rng: random.Random,
) -> list[int]:
    """Genera una distribución realista de días de anticipación para N compras.

    Modelo inspirado en datos FA: la mayoría compra entre 1 y 14 días antes,
    con una cola de compradores muy anticipados y compradores de último momento.
    """
    dias = []
    max_dias = min(dias_hasta_salida, 90)
    for _ in range(num_boletos):
        # 15% compra mismo día o un día antes
        r = rng.random()
        if r < 0.08:
            d = 0
        elif r < 0.18:
            d = 1
        elif r < 0.45:
            d = rng.randint(2, 7)
        elif r < 0.75:
            d = rng.randint(8, 20)
        elif r < 0.90:
            d = rng.randint(21, 40)
        else:
            d = rng.randint(41, max_dias) if max_dias > 40 else rng.randint(21, max_dias)
        dias.append(min(d, max_dias))
    # Ordenar de mayor a menor anticipación (simulamos ventas en orden temporal)
    dias.sort(reverse=True)
    return dias


def _patron_segmentos(num_boletos: int, rng: random.Random) -> list[str]:
    """Genera mezcla realista ocio/negocios (70/30)."""
    return [
        "negocios" if rng.random() < 0.30 else "ocio"
        for _ in range(num_boletos)
    ]


def simular_ventas(
    tarifa_base: float,
    ruta_id: str,
    capacidad: int,
    modelo: str,
    num_boletos: int,
    nivel_demanda: str = "normal",
    dias_hasta_salida: int = 30,
    adopcion_servicios: dict[str, float] | None = None,
    precios_servicios: dict[str, float] | None = None,
    seed: int | None = None,
) -> ResultadoSimulacion:
    """Simula la venta de N boletos con patrones realistas.

    Args:
        tarifa_base: precio base de la ruta.
        ruta_id: identificador de la ruta.
        capacidad: total de asientos del autobús.
        modelo: "hibrido" | "aviacion" | "flixbus".
        num_boletos: cuántos boletos vender.
        nivel_demanda: nivel de demanda del viaje.
        dias_hasta_salida: días desde el inicio de la simulación hasta la salida.
        adopcion_servicios: {servicio_id: prob} de adopción por boleto.
        precios_servicios: {servicio_id: precio_base} de cada servicio.
        seed: semilla aleatoria para reproducibilidad.

    Returns:
        ResultadoSimulacion con todos los eventos de venta.
    """
    rng = random.Random(seed)
    num_boletos = min(num_boletos, capacidad)

    anticipaciones = _patron_anticipacion_realista(num_boletos, dias_hasta_salida, rng)
    segmentos = _patron_segmentos(num_boletos, rng)

    resultado = ResultadoSimulacion(
        modelo=modelo,
        ruta_id=ruta_id,
        tarifa_base=tarifa_base,
        capacidad=capacidad,
    )

    for i, (dias_ant, seg) in enumerate(zip(anticipaciones, segmentos)):
        ocupacion = i / capacidad

        precio_resultado = calcular_precio(
            tarifa_base=tarifa_base,
            ocupacion=ocupacion,
            dias_anticipacion=dias_ant,
            nivel_demanda=nivel_demanda,
            segmento=seg,
            modelo=modelo,
        )

        ingreso_servicios = 0.0
        if adopcion_servicios and precios_servicios:
            for srv_id, prob in adopcion_servicios.items():
                if rng.random() < prob:
                    ingreso_servicios += precios_servicios.get(srv_id, 0.0)

        evento = EventoVenta(
            num=i + 1,
            dias_anticipacion=dias_ant,
            segmento=seg,
            nivel_demanda=nivel_demanda,
            resultado=precio_resultado,
            ingreso_servicios=ingreso_servicios,
        )
        resultado.eventos.append(evento)

    return resultado


def simular_tres_modelos(
    tarifa_base: float,
    ruta_id: str,
    capacidad: int,
    num_boletos: int,
    nivel_demanda: str = "normal",
    dias_hasta_salida: int = 30,
    adopcion_servicios: dict[str, float] | None = None,
    precios_servicios: dict[str, float] | None = None,
    seed: int | None = 42,
) -> dict[str, ResultadoSimulacion]:
    """Simula la misma secuencia de ventas con los 3 modelos en paralelo.

    Usa el mismo seed para que las secuencias de anticipación y segmento sean
    idénticas entre modelos — comparación justa.

    Returns:
        {"aviacion": ..., "flixbus": ..., "hibrido": ...}
    """
    return {
        modelo: simular_ventas(
            tarifa_base=tarifa_base,
            ruta_id=ruta_id,
            capacidad=capacidad,
            modelo=modelo,
            num_boletos=num_boletos,
            nivel_demanda=nivel_demanda,
            dias_hasta_salida=dias_hasta_salida,
            adopcion_servicios=adopcion_servicios,
            precios_servicios=precios_servicios,
            seed=seed,
        )
        for modelo in ("aviacion", "flixbus", "hibrido")
    }
