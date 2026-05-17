import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TierServicio(str, enum.Enum):
    base = "base"
    superior = "superior"


class ServicioAdicional(Base):
    """Catálogo de servicios adicionales disponibles (seed data)."""

    __tablename__ = "servicios_adicionales"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    precio_base_mxn: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    precio_superior_mxn: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    adopcion_ocio_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    adopcion_negocios_pct: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.0
    )

    servicios_boleto: Mapped[list["ServicioBoleto"]] = relationship(
        "ServicioBoleto", back_populates="servicio"
    )

    def __repr__(self) -> str:
        return f"<ServicioAdicional {self.id}: {self.nombre}>"


class ServicioBoleto(Base):
    """Relación boleto ↔ servicio adicional (con precio y tier)."""

    __tablename__ = "servicios_boleto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    boleto_id: Mapped[int] = mapped_column(Integer, ForeignKey("boletos.id"), nullable=False)
    servicio_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("servicios_adicionales.id"), nullable=False
    )
    precio_pagado_mxn: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tier: Mapped[TierServicio] = mapped_column(
        Enum(TierServicio), nullable=False, default=TierServicio.base
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    boleto: Mapped["Boleto"] = relationship("Boleto", back_populates="servicios")  # noqa: F821
    servicio: Mapped["ServicioAdicional"] = relationship(
        "ServicioAdicional", back_populates="servicios_boleto"
    )

    def __repr__(self) -> str:
        return f"<ServicioBoleto boleto={self.boleto_id} srv={self.servicio_id} ${self.precio_pagado_mxn}>"
