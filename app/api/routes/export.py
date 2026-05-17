"""Endpoints de exportación a Excel."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Boleto, Escenario, ServicioAdicional
from app.services.excel_export import generar_excel_escenario

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/escenario/{escenario_id}")
def exportar_escenario(escenario_id: int, db: Session = Depends(get_db)):
    """Genera y descarga un .xlsx completo del escenario."""
    escenario = db.query(Escenario).filter(Escenario.id == escenario_id).first()
    if not escenario:
        raise HTTPException(status_code=404, detail=f"Escenario {escenario_id} no encontrado")

    boletos = (
        db.query(Boleto)
        .options(selectinload(Boleto.servicios))
        .filter(Boleto.escenario_id == escenario_id)
        .order_by(Boleto.fecha_compra_simulada)
        .all()
    )

    servicios_cat = db.query(ServicioAdicional).all()

    esc_dict = {
        "nombre": escenario.nombre,
        "modelo_principal": escenario.modelo_principal.value,
        "ruta_id": escenario.ruta_id,
        "created_at": escenario.created_at.isoformat(),
    }

    boletos_dict = [
        {
            "precio_pagado_mxn": float(b.precio_pagado_mxn),
            "multiplicador_aplicado": float(b.multiplicador_aplicado),
            "clase_tarifaria": b.clase_tarifaria.value,
            "segmento_pasajero": b.segmento_pasajero.value,
            "factores_desglose": b.factores_desglose,
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
        for b in boletos
    ]

    servicios_cat_dict = [
        {"id": s.id, "nombre": s.nombre}
        for s in servicios_cat
    ]

    xlsx_bytes = generar_excel_escenario(
        escenario=esc_dict,
        boletos=boletos_dict,
        servicios_catalogo=servicios_cat_dict,
    )

    filename = f"hyperred_escenario_{escenario_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    logger.info(f"Exportando escenario {escenario_id} → {filename}")

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/comparacion")
def exportar_comparacion(
    ruta_id: str,
    tarifa_base: float,
    num_boletos: int = 20,
    nivel_demanda: str = "normal",
    db: Session = Depends(get_db),
):
    """Genera y descarga un .xlsx de la comparación de los 3 modelos."""
    from app.core.revenue_simulator import simular_tres_modelos
    servicios = db.query(ServicioAdicional).all()
    adopcion = {s.id: float(s.adopcion_ocio_pct) for s in servicios}
    precios_srv = {s.id: float(s.precio_base_mxn) for s in servicios}

    resultados = simular_tres_modelos(
        tarifa_base=tarifa_base,
        ruta_id=ruta_id,
        capacidad=45,
        num_boletos=num_boletos,
        nivel_demanda=nivel_demanda,
        adopcion_servicios=adopcion,
        precios_servicios=precios_srv,
        seed=42,
    )

    comparacion = {modelo: r.as_dict() for modelo, r in resultados.items()}
    escenario_dummy = {"nombre": f"Comparación {ruta_id}", "modelo_principal": "hibrido", "ruta_id": ruta_id}

    xlsx_bytes = generar_excel_escenario(
        escenario=escenario_dummy,
        boletos=[],
        servicios_catalogo=[{"id": s.id, "nombre": s.nombre} for s in servicios],
        comparacion=comparacion,
    )

    filename = f"hyperred_comparacion_{ruta_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
