"""Endpoints del comparador de modelos — Aviación / Flixbus / Híbrido FA."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.pricing_engine import DEMAND_FACTORS, calcular_precio
from app.core.revenue_simulator import simular_tres_modelos
from app.database import get_db
from app.models import Boleto, Escenario, Ruta, ServicioAdicional, ServicioBoleto
from app.schemas.simulador import ComparacionCompleta, GenerarComparacionRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Lookup inverso: valor f_dem → nombre del nivel de demanda
_F_DEM_REVERSE: dict[float, str] = {v: k for k, v in DEMAND_FACTORS.items()}

BUS_CAPACIDAD = 45


def _f_dem_a_nivel(f_dem: float) -> str:
    """Convierte un valor de f_dem guardado en factores_desglose al nombre de nivel."""
    # Busca la coincidencia más cercana para tolerancia de redondeo
    closest = min(_F_DEM_REVERSE.keys(), key=lambda x: abs(x - f_dem))
    return _F_DEM_REVERSE[closest]


def _serializar_comparacion(resultados: dict) -> dict:
    return {
        modelo: {
            "modelo": modelo,
            "ingreso_total": round(r.ingreso_boletos, 2),
            "ingreso_boletos": round(r.ingreso_boletos, 2),
            "ingreso_servicios": round(r.ingreso_servicios, 2),
            "precio_promedio": round(r.precio_promedio, 2),
            "precio_minimo": round(r.precio_minimo, 2),
            "precio_maximo": round(r.precio_maximo, 2),
            "num_boletos": r.num_boletos,
            "serie_precios": r.serie_precios,
        }
        for modelo, r in resultados.items()
    }


@router.post("/generar", response_model=ComparacionCompleta)
def generar_comparacion(payload: GenerarComparacionRequest, db: Session = Depends(get_db)):
    """Simula la misma secuencia aleatoria de N ventas con los 3 modelos."""
    servicios = db.query(ServicioAdicional).all()
    adopcion = {s.id: float(s.adopcion_ocio_pct) for s in servicios}
    precios_srv = {s.id: float(s.precio_base_mxn) for s in servicios}
    seed = payload.seed if payload.seed is not None else 42

    try:
        resultados = simular_tres_modelos(
            tarifa_base=payload.tarifa_base,
            ruta_id=payload.ruta_id,
            capacidad=BUS_CAPACIDAD,
            num_boletos=payload.num_boletos,
            nivel_demanda=payload.nivel_demanda,
            dias_hasta_salida=payload.dias_hasta_salida,
            adopcion_servicios=adopcion,
            precios_servicios=precios_srv,
            seed=seed,
        )
    except Exception as e:
        logger.error(f"Error generando comparación aleatoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return _serializar_comparacion(resultados)


@router.get("/escenario/{escenario_id}", response_model=ComparacionCompleta)
def comparar_desde_escenario(escenario_id: int, db: Session = Depends(get_db)):
    """Carga un escenario guardado y replays sus boletos reales en los 3 modelos.

    Reconstruye exactamente la misma secuencia de compras (días de anticipación,
    segmento, nivel de demanda, posición en el bus) y la ejecuta en paralelo
    contra Aviación puro, Flixbus puro e Híbrido FA — comparación justa.
    """
    escenario = (
        db.query(Escenario)
        .options(selectinload(Escenario.boletos), selectinload(Escenario.ruta))
        .filter(Escenario.id == escenario_id)
        .first()
    )
    if not escenario:
        raise HTTPException(status_code=404, detail=f"Escenario {escenario_id} no encontrado")

    boletos = [b for b in escenario.boletos if b.estado == "activo"]
    if not boletos:
        raise HTTPException(
            status_code=422,
            detail="El escenario no tiene boletos guardados para comparar",
        )

    # Obtener tarifa base desde la ruta
    ruta = db.query(Ruta).filter(Ruta.id == escenario.ruta_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail=f"Ruta {escenario.ruta_id} no encontrada")
    tarifa_base = float(ruta.tarifa_base_mxn)

    # Reconstruir la secuencia de inputs desde los factores_desglose de cada boleto
    # Cada boleto aporta: (dias_anticipacion, segmento, nivel_demanda, ocupacion_en_momento_de_compra)
    secuencia: list[dict] = []
    for i, boleto in enumerate(boletos):
        factores = boleto.factores_desglose or {}
        f_dem = factores.get("f_dem", 1.0)
        nivel_demanda = _f_dem_a_nivel(f_dem)
        ocupacion = i / BUS_CAPACIDAD  # posición ordinal en el bus

        secuencia.append({
            "dias_anticipacion": boleto.dias_anticipacion,
            "segmento": boleto.segmento_pasajero.value,
            "nivel_demanda": nivel_demanda,
            "ocupacion": ocupacion,
        })

    # Ingreso real por servicios adicionales del escenario (solo aplica al Híbrido FA)
    ids_boletos = [b.id for b in boletos]
    ingreso_servicios_real: float = db.query(
        func.coalesce(func.sum(ServicioBoleto.precio_pagado_mxn), 0.0)
    ).filter(ServicioBoleto.boleto_id.in_(ids_boletos)).scalar() or 0.0
    ingreso_servicios_real = round(float(ingreso_servicios_real), 2)

    # Ejecutar la misma secuencia en los 3 modelos
    resultados_raw: dict[str, dict] = {}
    for modelo in ("aviacion", "flixbus", "hibrido"):
        precios: list[float] = []
        ingreso_boletos = 0.0

        for entrada in secuencia:
            r = calcular_precio(
                tarifa_base=tarifa_base,
                ocupacion=entrada["ocupacion"],
                dias_anticipacion=entrada["dias_anticipacion"],
                nivel_demanda=entrada["nivel_demanda"],
                segmento=entrada["segmento"],
                modelo=modelo,
            )
            precios.append(r.precio)
            ingreso_boletos += r.precio

        # Solo el Híbrido FA acumula el ingreso real de servicios adicionales.
        # Aviación y Flixbus muestran $0 — eso es intencional: ilustra que esos
        # modelos no contemplan revenue de add-ons.
        ingreso_servicios = ingreso_servicios_real if modelo == "hibrido" else 0.0

        resultados_raw[modelo] = {
            "modelo": modelo,
            "ingreso_total": round(ingreso_boletos, 2),
            "ingreso_boletos": round(ingreso_boletos, 2),
            "ingreso_servicios": ingreso_servicios,
            "precio_promedio": round(ingreso_boletos / len(precios), 2) if precios else 0.0,
            "precio_minimo": round(min(precios), 2) if precios else 0.0,
            "precio_maximo": round(max(precios), 2) if precios else 0.0,
            "num_boletos": len(precios),
            "serie_precios": [round(p, 2) for p in precios],
        }

    logger.info(
        f"Comparación desde escenario {escenario_id} '{escenario.nombre}' "
        f"— {len(boletos)} boletos · ${ingreso_servicios_real:.2f} en servicios"
    )
    return resultados_raw


@router.get("/escenarios-disponibles")
def listar_escenarios_comparables(db: Session = Depends(get_db)):
    """Lista escenarios que tienen boletos guardados (aptos para comparar)."""
    from sqlalchemy import func

    rows = (
        db.query(Escenario, func.count(Boleto.id).label("num_boletos_reales"))
        .join(Boleto, Boleto.escenario_id == Escenario.id)
        .filter(Boleto.estado == "activo")
        .group_by(Escenario.id)
        .order_by(Escenario.created_at.desc())
        .all()
    )

    return [
        {
            "id": esc.id,
            "nombre": esc.nombre,
            "ruta_id": esc.ruta_id,
            "modelo_principal": esc.modelo_principal.value,
            "num_boletos": esc.num_boletos,
            "num_boletos_reales": num_reales,
            "ingreso_total_mxn": float(esc.ingreso_total_mxn),
            "created_at": esc.created_at.isoformat(),
        }
        for esc, num_reales in rows
    ]
