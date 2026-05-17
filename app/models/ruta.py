import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoServicio(str, enum.Enum):
    regular = "Regular"
    plus = "Plus"
    coordinado = "Coordinado"
    alimentador = "Alimentador"
    ejecutivo = "Ejecutivo"


class Ruta(Base):
    __tablename__ = "rutas"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    origen: Mapped[str] = mapped_column(String(100), nullable=False)
    destino: Mapped[str] = mapped_column(String(100), nullable=False)
    distancia_km: Mapped[int] = mapped_column(Integer, nullable=False)
    tarifa_base_mxn: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tipo_servicio: Mapped[TipoServicio] = mapped_column(
        Enum(TipoServicio), nullable=False, default=TipoServicio.regular
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    viajes: Mapped[list["Viaje"]] = relationship("Viaje", back_populates="ruta")  # noqa: F821
    escenarios: Mapped[list["Escenario"]] = relationship("Escenario", back_populates="ruta")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Ruta {self.id}: {self.origen}→{self.destino}>"
