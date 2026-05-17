from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Boleto

router = APIRouter()


@router.get("/viaje/{viaje_id}")
def boletos_por_viaje(viaje_id: int, db: Session = Depends(get_db)):
    """Lista todos los boletos de un viaje."""
    boletos = (
        db.query(Boleto)
        .options(selectinload(Boleto.servicios))
        .filter(Boleto.viaje_id == viaje_id)
        .order_by(Boleto.fecha_compra_simulada)
        .all()
    )
    return [_boleto_dict(b) for b in boletos]


@router.get("/{boleto_id}")
def obtener_boleto(boleto_id: int, db: Session = Depends(get_db)):
    """Obtiene un boleto por ID."""
    boleto = (
        db.query(Boleto)
        .options(selectinload(Boleto.servicios))
        .filter(Boleto.id == boleto_id)
        .first()
    )
    if not boleto:
        raise HTTPException(status_code=404, detail=f"Boleto {boleto_id} no encontrado")
    return _boleto_dict(boleto)


def _boleto_dict(b: Boleto) -> dict:
    return {
        "id": b.id,
        "viaje_id": b.viaje_id,
        "precio_pagado_mxn": float(b.precio_pagado_mxn),
        "multiplicador_aplicado": float(b.multiplicador_aplicado),
        "clase_tarifaria": b.clase_tarifaria.value,
        "segmento_pasajero": b.segmento_pasajero.value,
        "factores_desglose": b.factores_desglose,
        "fecha_compra_simulada": b.fecha_compra_simulada.isoformat(),
        "dias_anticipacion": b.dias_anticipacion,
        "estado": b.estado.value,
        "modelo_usado": b.modelo_usado.value,
        "servicios": [
            {
                "servicio_id": s.servicio_id,
                "precio_pagado_mxn": float(s.precio_pagado_mxn),
                "tier": s.tier.value,
            }
            for s in b.servicios
        ],
    }
