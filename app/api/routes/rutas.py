from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Boleto, EstadoBoleto, Ruta, Viaje

router = APIRouter()


@router.get("/")
def listar_rutas(db: Session = Depends(get_db)):
    """Lista todas las rutas disponibles."""
    rutas = db.query(Ruta).all()
    return [
        {
            "id": r.id,
            "origen": r.origen,
            "destino": r.destino,
            "distancia_km": r.distancia_km,
            "tarifa_base_mxn": float(r.tarifa_base_mxn),
            "tipo_servicio": r.tipo_servicio.value,
        }
        for r in rutas
    ]


@router.get("/kpis/global")
def kpis_globales(db: Session = Depends(get_db)):
    """KPIs globales para el dashboard."""
    boletos_activos = db.query(Boleto).filter(Boleto.estado == EstadoBoleto.activo).all()

    ingreso_boletos = sum(float(b.precio_pagado_mxn) for b in boletos_activos)
    ingreso_servicios = sum(
        float(sb.precio_pagado_mxn)
        for b in boletos_activos
        for sb in b.servicios
    )

    # Ocupación promedio por viaje (solo viajes con al menos 1 boleto)
    viajes_con_boletos = (
        db.query(Viaje)
        .join(Boleto, Boleto.viaje_id == Viaje.id)
        .filter(Boleto.estado == EstadoBoleto.activo)
        .distinct()
        .all()
    )
    ocupacion_promedio = 0.0
    if viajes_con_boletos:
        ocupaciones = [
            len([b for b in v.boletos if b.estado == EstadoBoleto.activo]) / v.capacidad
            for v in viajes_con_boletos
        ]
        ocupacion_promedio = round(sum(ocupaciones) / len(ocupaciones) * 100, 1)

    return {
        "ingreso_total": round(ingreso_boletos, 2),
        "boletos_vendidos": len(boletos_activos),
        "ocupacion_promedio": ocupacion_promedio,
        "ingreso_servicios": round(ingreso_servicios, 2),
    }


@router.get("/{ruta_id}")
def obtener_ruta(ruta_id: str, db: Session = Depends(get_db)):
    """Obtiene una ruta por ID."""
    ruta = db.query(Ruta).filter(Ruta.id == ruta_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail=f"Ruta {ruta_id} no encontrada")
    return {
        "id": ruta.id,
        "origen": ruta.origen,
        "destino": ruta.destino,
        "distancia_km": ruta.distancia_km,
        "tarifa_base_mxn": float(ruta.tarifa_base_mxn),
        "tipo_servicio": ruta.tipo_servicio.value,
    }
