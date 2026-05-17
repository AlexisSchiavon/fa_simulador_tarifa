from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Viaje

router = APIRouter()


@router.get("/")
def listar_viajes(
    ruta_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Lista viajes, opcionalmente filtrados por ruta."""
    q = db.query(Viaje).options(selectinload(Viaje.ruta), selectinload(Viaje.boletos))
    if ruta_id:
        q = q.filter(Viaje.ruta_id == ruta_id)
    q = q.filter(Viaje.fecha_salida >= datetime.now()).order_by(Viaje.fecha_salida).limit(60)
    viajes = q.all()
    return [_viaje_dict(v) for v in viajes]


@router.get("/{viaje_id}")
def obtener_viaje(viaje_id: int, db: Session = Depends(get_db)):
    """Obtiene un viaje con detalle de ocupación."""
    viaje = (
        db.query(Viaje)
        .options(selectinload(Viaje.ruta), selectinload(Viaje.boletos))
        .filter(Viaje.id == viaje_id)
        .first()
    )
    if not viaje:
        raise HTTPException(status_code=404, detail=f"Viaje {viaje_id} no encontrado")
    return _viaje_dict(viaje)


def _viaje_dict(v: Viaje) -> dict:
    boletos_activos = [b for b in v.boletos if b.estado == "activo"]
    return {
        "id": v.id,
        "ruta_id": v.ruta_id,
        "ruta": f"{v.ruta.origen} → {v.ruta.destino}" if v.ruta else None,
        "fecha_salida": v.fecha_salida.isoformat(),
        "capacidad": v.capacidad,
        "boletos_vendidos": len(boletos_activos),
        "asientos_libres": v.capacidad - len(boletos_activos),
        "ocupacion_pct": round(len(boletos_activos) / v.capacidad * 100, 1),
        "nivel_demanda": v.nivel_demanda.value,
        "estado": v.estado.value,
    }
