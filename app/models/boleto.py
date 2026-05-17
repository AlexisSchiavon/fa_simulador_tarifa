import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClaseTarifaria(str, enum.Enum):
    E = "E"  # Económica  0.65–1.00×
    S = "S"  # Estándar   1.00–1.35×
    P = "P"  # Plus       1.35–2.00×
    X = "X"  # Ejecutiva  2.00–3.50×


class SegmentoPasajero(str, enum.Enum):
    ocio = "ocio"
    negocios = "negocios"


class EstadoBoleto(str, enum.Enum):
    activo = "activo"
    cancelado = "cancelado"
    buyback = "buyback"


class ModeloUsado(str, enum.Enum):
    aviacion = "aviacion"
    flixbus = "flixbus"
    hibrido = "hibrido"


class Boleto(Base):
    __tablename__ = "boletos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    viaje_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("viajes.id"), nullable=True)
    precio_pagado_mxn: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    multiplicador_aplicado: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    clase_tarifaria: Mapped[ClaseTarifaria] = mapped_column(Enum(ClaseTarifaria), nullable=False)
    segmento_pasajero: Mapped[SegmentoPasajero] = mapped_column(
        Enum(SegmentoPasajero), nullable=False, default=SegmentoPasajero.ocio
    )
    factores_desglose: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fecha_compra_simulada: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dias_anticipacion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[EstadoBoleto] = mapped_column(
        Enum(EstadoBoleto), nullable=False, default=EstadoBoleto.activo
    )
    modelo_usado: Mapped[ModeloUsado] = mapped_column(
        Enum(ModeloUsado), nullable=False, default=ModeloUsado.hibrido
    )
    escenario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("escenarios.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    viaje: Mapped["Viaje | None"] = relationship("Viaje", back_populates="boletos")  # noqa: F821
    escenario: Mapped["Escenario | None"] = relationship("Escenario", back_populates="boletos")  # noqa: F821
    servicios: Mapped[list["ServicioBoleto"]] = relationship(  # noqa: F821
        "ServicioBoleto", back_populates="boleto", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Boleto {self.id}: ${self.precio_pagado_mxn} clase={self.clase_tarifaria}>"
