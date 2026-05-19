"""Schemas Pydantic para los endpoints del simulador y comparador."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Modelo = Literal["hibrido", "aviacion", "flixbus", "ado", "japi"]
NivelDemanda = Literal["valle", "normal", "alta", "temporada"]
Segmento = Literal["ocio", "negocios"]


# ── Request schemas ───────────────────────────────────────────────────────────

class CalcularPrecioRequest(BaseModel):
    tarifa_base: float = Field(gt=0, description="Precio base de la ruta (MXN)")
    ocupacion: float = Field(ge=0.0, le=1.0, description="Fracción de asientos ocupados")
    dias_anticipacion: int = Field(ge=0, description="Días desde la compra hasta la salida")
    nivel_demanda: NivelDemanda = "normal"
    segmento: Segmento = "ocio"
    modelo: Modelo = "hibrido"


class VenderBoletoRequest(BaseModel):
    ruta_id: str = Field(min_length=1, max_length=10)
    tarifa_base: float = Field(gt=0)
    ocupacion: float = Field(ge=0.0, le=1.0)
    dias_anticipacion: int = Field(ge=0)
    nivel_demanda: NivelDemanda = "normal"
    segmento: Segmento = "ocio"
    modelo: Modelo = "hibrido"
    servicios_ids: list[str] = Field(default_factory=list)
    viaje_id: int | None = None
    escenario_id: int | None = None


class BoletoHistorialItem(BaseModel):
    """Un boleto del historial del simulador frontend."""
    num: int
    clase: str
    segmento: str
    precio: float
    total: float
    dias: int
    factores: dict[str, float] = Field(default_factory=dict)
    multiplicador: float = 1.0
    servicios_ids: list[str] = Field(default_factory=list)
    ingreso_servicios: float = 0.0


class GuardarEscenarioRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    ruta_id: str
    modelo: Modelo = "hibrido"
    historial: list[BoletoHistorialItem] = Field(default_factory=list)


class GenerarComparacionRequest(BaseModel):
    ruta_id: str
    tarifa_base: float = Field(gt=0)
    num_boletos: int = Field(ge=1, le=45, default=20)
    nivel_demanda: NivelDemanda = "normal"
    dias_hasta_salida: int = Field(ge=0, default=30)
    seed: int | None = None


# ── Response schemas ──────────────────────────────────────────────────────────

class FactoresDesgloseResponse(BaseModel):
    f_ocu: float
    f_ant: float
    f_dem: float
    f_seg: float
    f_lix: float


class PrecioResponse(BaseModel):
    precio: float
    multiplicador: float
    clase: str
    factores: FactoresDesgloseResponse
    tarifa_base: float
    modelo: str
    clamped: bool


class VentaBoletoResponse(BaseModel):
    precio: float
    multiplicador: float
    clase: str
    factores: dict[str, float]
    segmento: str
    dias_anticipacion: int
    ingreso_servicios: float
    servicios_aplicados: list[str]
    boleto_id: int | None = None


class EscenarioResumen(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    modelo_principal: str
    ruta_id: str
    ingreso_total_mxn: float
    num_boletos: int
    created_at: str


class ModeloComparacionResponse(BaseModel):
    modelo: str
    ingreso_total: float
    ingreso_boletos: float
    ingreso_servicios: float
    precio_promedio: float
    precio_minimo: float
    precio_maximo: float
    num_boletos: int
    serie_precios: list[float]


class ComparacionCompleta(BaseModel):
    aviacion: ModeloComparacionResponse
    flixbus: ModeloComparacionResponse
    japi: ModeloComparacionResponse
    ado: ModeloComparacionResponse
    hibrido: ModeloComparacionResponse
