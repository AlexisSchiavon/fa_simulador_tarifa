"""
Datos iniciales del sandbox Hyperred FA.
Se ejecuta al arrancar si la BD está vacía.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    NivelDemanda,
    Ruta,
    ServicioAdicional,
    TipoServicio,
    Viaje,
)

logger = logging.getLogger(__name__)

RUTAS_SEED = [
    {
        "id": "R1",
        "origen": "León",
        "destino": "Querétaro",
        "distancia_km": 160,
        "tarifa_base_mxn": 380.00,
        "tipo_servicio": TipoServicio.plus,
    },
    {
        "id": "R2",
        "origen": "León",
        "destino": "Irapuato",
        "distancia_km": 50,
        "tarifa_base_mxn": 140.00,
        "tipo_servicio": TipoServicio.regular,
    },
    {
        "id": "R3",
        "origen": "Irapuato",
        "destino": "Querétaro",
        "distancia_km": 110,
        "tarifa_base_mxn": 280.00,
        "tipo_servicio": TipoServicio.plus,
    },
    {
        "id": "R4",
        "origen": "León",
        "destino": "Silao",
        "distancia_km": 30,
        "tarifa_base_mxn": 90.00,
        "tipo_servicio": TipoServicio.alimentador,
    },
    {
        "id": "R5",
        "origen": "Silao",
        "destino": "Querétaro",
        "distancia_km": 130,
        "tarifa_base_mxn": 320.00,
        "tipo_servicio": TipoServicio.plus,
    },
]

SERVICIOS_SEED = [
    {
        "id": "SA1",
        "nombre": "Zona Ejecutiva",
        "descripcion": "Asiento ergonómico, mesa plegable, enchufe individual y WiFi 20+ Mbps",
        "precio_base_mxn": 134.00,
        "precio_superior_mxn": 269.00,
        "adopcion_ocio_pct": 0.22,
        "adopcion_negocios_pct": 0.58,
    },
    {
        "id": "SA2",
        "nombre": "Zona Reservada Mujer / Menores",
        "descripcion": "Sección delantera monitoreada, solo para mujeres y menores acompañados",
        "precio_base_mxn": 127.00,
        "precio_superior_mxn": 255.00,
        "adopcion_ocio_pct": 0.50,
        "adopcion_negocios_pct": 0.51,
    },
    {
        "id": "SA3",
        "nombre": "Taxi Garantizado en Destino",
        "descripcion": "Uber/Didi reservado y confirmado antes de abordar. Sin esperas.",
        "precio_base_mxn": 160.00,
        "precio_superior_mxn": 319.00,
        "adopcion_ocio_pct": 0.18,
        "adopcion_negocios_pct": 0.58,
    },
    {
        "id": "SA4",
        "nombre": "Traslado de Mascota",
        "descripcion": "Jaula climatizada con monitoreo en tiempo real y notificaciones vía app",
        "precio_base_mxn": 243.00,
        "precio_superior_mxn": 486.00,
        "adopcion_ocio_pct": 0.04,
        "adopcion_negocios_pct": 0.20,
    },
    {
        "id": "SA5",
        "nombre": "Casillero Electrónico",
        "descripcion": "Casillero numerado con apertura por código QR vía app",
        "precio_base_mxn": 85.00,
        "precio_superior_mxn": 170.00,
        "adopcion_ocio_pct": 0.10,
        "adopcion_negocios_pct": 0.25,
    },
]


def _generar_viajes(rutas: list[Ruta], base_date: datetime) -> list[dict]:
    """Genera viajes para los próximos 30 días (horarios típicos FA)."""
    horarios = ["06:00", "08:30", "11:00", "14:00", "17:00", "19:30"]
    niveles_demanda = [
        NivelDemanda.normal,
        NivelDemanda.normal,
        NivelDemanda.alta,
        NivelDemanda.normal,
        NivelDemanda.alta,
        NivelDemanda.normal,
    ]
    viajes = []
    for ruta in rutas:
        for day_offset in range(1, 31):
            fecha = base_date + timedelta(days=day_offset)
            # Fin de semana: más viajes y demanda alta
            if fecha.weekday() >= 5:
                horarios_dia = horarios
                niveles_dia = [NivelDemanda.alta] * len(horarios)
            else:
                horarios_dia = horarios
                niveles_dia = niveles_demanda

            # Solo crear 2 viajes por día para no saturar el seed
            for i in [0, 3]:
                h, m = map(int, horarios_dia[i].split(":"))
                fecha_salida = fecha.replace(hour=h, minute=m, second=0, microsecond=0)
                viajes.append(
                    {
                        "ruta_id": ruta.id,
                        "fecha_salida": fecha_salida,
                        "capacidad": 45,
                        "nivel_demanda": niveles_dia[i],
                    }
                )
    return viajes


def run_seed(db: Session) -> None:
    """Ejecuta el seed si las tablas están vacías."""
    if db.query(Ruta).count() > 0:
        logger.debug("Seed ya ejecutado, omitiendo.")
        return

    logger.info("Ejecutando seed de datos iniciales...")

    # Rutas
    rutas_creadas = []
    for datos in RUTAS_SEED:
        ruta = Ruta(**datos)
        db.add(ruta)
        rutas_creadas.append(ruta)
    db.flush()

    # Servicios adicionales
    for datos in SERVICIOS_SEED:
        srv = ServicioAdicional(**datos)
        db.add(srv)
    db.flush()

    # Viajes (próximos 30 días)
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    viajes_data = _generar_viajes(rutas_creadas, base_date)
    for v_data in viajes_data:
        viaje = Viaje(**v_data)
        db.add(viaje)

    db.commit()
    logger.info(
        f"Seed completado: {len(rutas_creadas)} rutas, "
        f"{len(SERVICIOS_SEED)} servicios, "
        f"{len(viajes_data)} viajes."
    )
