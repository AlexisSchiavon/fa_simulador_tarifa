"""Endpoints del simulador de tarificación dinámica."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.pricing_engine import calcular_precio
from app.database import get_db
from app.models import (
    Boleto,
    ClaseTarifaria,
    Escenario,
    EstadoBoleto,
    ModeloPrincipal,
    ModeloUsado,
    SegmentoPasajero,
    ServicioAdicional,
    ServicioBoleto,
    TierServicio,
    Viaje,
)
from app.schemas.simulador import (
    EscenarioResumen,
    GuardarEscenarioRequest,
    PrecioResponse,
    VenderBoletoRequest,
    VentaBoletoResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/calcular", response_model=PrecioResponse)
def calcular_precio_endpoint(
    tarifa_base: float = Query(gt=0),
    ocupacion: float = Query(ge=0.0, le=1.0),
    dias_anticipacion: int = Query(ge=0),
    nivel_demanda: str = Query(default="normal"),
    segmento: str = Query(default="ocio"),
    modelo: str = Query(default="hibrido"),
):
    """Calcula el precio dinámico sin persistir (solo consulta)."""
    try:
        resultado = calcular_precio(
            tarifa_base=tarifa_base,
            ocupacion=ocupacion,
            dias_anticipacion=dias_anticipacion,
            nivel_demanda=nivel_demanda,
            segmento=segmento,
            modelo=modelo,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "precio": resultado.precio,
        "multiplicador": resultado.multiplicador,
        "clase": resultado.clase,
        "factores": resultado.factores.as_dict(),
        "tarifa_base": resultado.tarifa_base,
        "modelo": resultado.modelo,
        "clamped": resultado.clamped,
    }


@router.post("/vender", response_model=VentaBoletoResponse)
def vender_boleto(payload: VenderBoletoRequest, db: Session = Depends(get_db)):
    """Vende un boleto: calcula precio, persiste en BD y retorna el resultado."""
    try:
        resultado = calcular_precio(
            tarifa_base=payload.tarifa_base,
            ocupacion=payload.ocupacion,
            dias_anticipacion=payload.dias_anticipacion,
            nivel_demanda=payload.nivel_demanda,
            segmento=payload.segmento,
            modelo=payload.modelo,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Calcular ingreso de servicios adicionales seleccionados
    ingreso_servicios = 0.0
    servicios_aplicados: list[str] = []

    if payload.servicios_ids:
        servicios = (
            db.query(ServicioAdicional)
            .filter(ServicioAdicional.id.in_(payload.servicios_ids))
            .all()
        )
        for srv in servicios:
            ingreso_servicios += float(srv.precio_base_mxn)
            servicios_aplicados.append(srv.id)

    # Persistir boleto si se asocia a un viaje
    boleto_id = None
    if payload.viaje_id:
        viaje = db.query(Viaje).filter(Viaje.id == payload.viaje_id).first()
        if not viaje:
            raise HTTPException(status_code=404, detail=f"Viaje {payload.viaje_id} no encontrado")

        boleto = Boleto(
            viaje_id=payload.viaje_id,
            precio_pagado_mxn=resultado.precio,
            multiplicador_aplicado=resultado.multiplicador,
            clase_tarifaria=ClaseTarifaria(resultado.clase),
            segmento_pasajero=SegmentoPasajero(payload.segmento),
            factores_desglose=resultado.factores.as_dict(),
            fecha_compra_simulada=datetime.now(),
            dias_anticipacion=payload.dias_anticipacion,
            estado=EstadoBoleto.activo,
            modelo_usado=ModeloUsado(payload.modelo),
            escenario_id=payload.escenario_id,
        )
        db.add(boleto)
        db.flush()

        for srv_id in servicios_aplicados:
            srv_obj = next((s for s in db.query(ServicioAdicional).filter(ServicioAdicional.id == srv_id).all()), None)
            if srv_obj:
                sb = ServicioBoleto(
                    boleto_id=boleto.id,
                    servicio_id=srv_id,
                    precio_pagado_mxn=float(srv_obj.precio_base_mxn),
                    tier=TierServicio.base,
                )
                db.add(sb)

        db.commit()
        boleto_id = boleto.id
        logger.info(
            f"Boleto #{boleto_id} vendido: ${resultado.precio:.2f} clase={resultado.clase} "
            f"viaje={payload.viaje_id}"
        )

    return {
        "precio": resultado.precio,
        "multiplicador": resultado.multiplicador,
        "clase": resultado.clase,
        "factores": resultado.factores.as_dict(),
        "segmento": payload.segmento,
        "dias_anticipacion": payload.dias_anticipacion,
        "ingreso_servicios": ingreso_servicios,
        "servicios_aplicados": servicios_aplicados,
        "boleto_id": boleto_id,
    }


@router.get("/servicios")
def listar_servicios(db: Session = Depends(get_db)):
    """Lista el catálogo de servicios adicionales."""
    servicios = db.query(ServicioAdicional).all()
    return [
        {
            "id": s.id,
            "nombre": s.nombre,
            "descripcion": s.descripcion,
            "precio_base_mxn": float(s.precio_base_mxn),
            "precio_superior_mxn": float(s.precio_superior_mxn),
            "adopcion_ocio_pct": float(s.adopcion_ocio_pct),
            "adopcion_negocios_pct": float(s.adopcion_negocios_pct),
        }
        for s in servicios
    ]


@router.get("/escenarios", response_model=list[EscenarioResumen])
def listar_escenarios(db: Session = Depends(get_db)):
    """Lista todos los escenarios guardados."""
    escenarios = db.query(Escenario).order_by(Escenario.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "nombre": e.nombre,
            "descripcion": e.descripcion,
            "modelo_principal": e.modelo_principal.value,
            "ruta_id": e.ruta_id,
            "ingreso_total_mxn": float(e.ingreso_total_mxn),
            "num_boletos": e.num_boletos,
            "created_at": e.created_at.isoformat(),
        }
        for e in escenarios
    ]


@router.post("/guardar-escenario", response_model=EscenarioResumen)
def guardar_escenario(payload: GuardarEscenarioRequest, db: Session = Depends(get_db)):
    """Guarda un escenario y persiste todos sus boletos en la BD."""
    ingreso_boletos = sum(h.precio for h in payload.historial)
    ingreso_servicios = sum(h.ingreso_servicios for h in payload.historial)
    ingreso_total = ingreso_boletos + ingreso_servicios
    num_boletos = len(payload.historial)

    escenario = Escenario(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        modelo_principal=ModeloPrincipal(payload.modelo),
        ruta_id=payload.ruta_id,
        parametros_iniciales={
            "modelo": payload.modelo,
            "ruta_id": payload.ruta_id,
        },
        ingreso_total_mxn=ingreso_total,
        num_boletos=num_boletos,
    )
    db.add(escenario)
    db.flush()  # obtener escenario.id antes de commit

    # Persistir cada boleto del historial
    for item in payload.historial:
        boleto = Boleto(
            viaje_id=None,
            precio_pagado_mxn=item.precio,
            multiplicador_aplicado=item.multiplicador,
            clase_tarifaria=ClaseTarifaria(item.clase),
            segmento_pasajero=SegmentoPasajero(item.segmento),
            factores_desglose=item.factores,
            fecha_compra_simulada=datetime.now(),
            dias_anticipacion=item.dias,
            estado=EstadoBoleto.activo,
            modelo_usado=ModeloUsado(payload.modelo),
            escenario_id=escenario.id,
        )
        db.add(boleto)
        db.flush()

        # Persistir servicios del boleto si los hay
        if item.servicios_ids and item.ingreso_servicios > 0:
            precio_por_srv = item.ingreso_servicios / len(item.servicios_ids)
            for srv_id in item.servicios_ids:
                sb = ServicioBoleto(
                    boleto_id=boleto.id,
                    servicio_id=srv_id,
                    precio_pagado_mxn=round(precio_por_srv, 2),
                    tier=TierServicio.base,
                )
                db.add(sb)

    db.commit()
    db.refresh(escenario)
    logger.info(
        f"Escenario guardado: '{escenario.nombre}' (id={escenario.id}) "
        f"— {num_boletos} boletos · ${ingreso_total:.2f}"
    )
    return {
        "id": escenario.id,
        "nombre": escenario.nombre,
        "descripcion": escenario.descripcion,
        "modelo_principal": escenario.modelo_principal.value,
        "ruta_id": escenario.ruta_id,
        "ingreso_total_mxn": float(escenario.ingreso_total_mxn),
        "num_boletos": escenario.num_boletos,
        "created_at": escenario.created_at.isoformat(),
    }


@router.delete("/escenarios/{escenario_id}")
def eliminar_escenario(escenario_id: int, db: Session = Depends(get_db)):
    """Elimina un escenario guardado."""
    esc = db.query(Escenario).filter(Escenario.id == escenario_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail=f"Escenario {escenario_id} no encontrado")
    db.delete(esc)
    db.commit()
    return {"ok": True, "eliminado": escenario_id}
