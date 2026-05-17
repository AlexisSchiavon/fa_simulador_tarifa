import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ModeloPrincipal(str, enum.Enum):
    aviacion = "aviacion"
    flixbus = "flixbus"
    hibrido = "hibrido"


class Escenario(Base):
    __tablename__ = "escenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    modelo_principal: Mapped[ModeloPrincipal] = mapped_column(
        Enum(ModeloPrincipal), nullable=False, default=ModeloPrincipal.hibrido
    )
    ruta_id: Mapped[str] = mapped_column(String(10), ForeignKey("rutas.id"), nullable=False)
    parametros_iniciales: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    ingreso_total_mxn: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    num_boletos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    ruta: Mapped["Ruta"] = relationship("Ruta", back_populates="escenarios")  # noqa: F821
    boletos: Mapped[list["Boleto"]] = relationship("Boleto", back_populates="escenario")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Escenario {self.id}: {self.nombre}>"
