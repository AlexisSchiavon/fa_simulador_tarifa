import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NivelDemanda(str, enum.Enum):
    valle = "valle"
    normal = "normal"
    alta = "alta"
    temporada = "temporada"


class EstadoViaje(str, enum.Enum):
    programado = "programado"
    en_curso = "en_curso"
    completado = "completado"
    cancelado = "cancelado"


class Viaje(Base):
    __tablename__ = "viajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ruta_id: Mapped[str] = mapped_column(String(10), ForeignKey("rutas.id"), nullable=False)
    fecha_salida: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    nivel_demanda: Mapped[NivelDemanda] = mapped_column(
        Enum(NivelDemanda), nullable=False, default=NivelDemanda.normal
    )
    estado: Mapped[EstadoViaje] = mapped_column(
        Enum(EstadoViaje), nullable=False, default=EstadoViaje.programado
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    ruta: Mapped["Ruta"] = relationship("Ruta", back_populates="viajes")  # noqa: F821
    boletos: Mapped[list["Boleto"]] = relationship("Boleto", back_populates="viaje")  # noqa: F821

    @property
    def boletos_activos(self) -> list:
        return [b for b in self.boletos if b.estado == "activo"]

    @property
    def ocupacion(self) -> float:
        activos = len([b for b in self.boletos if b.estado == "activo"])
        return activos / self.capacidad if self.capacidad > 0 else 0.0

    def __repr__(self) -> str:
        return f"<Viaje {self.id}: ruta={self.ruta_id} salida={self.fecha_salida}>"
