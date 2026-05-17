"""
Tests exhaustivos del motor de tarificación dinámica híbrida.
Cobertura: todos los factores, los 3 modelos, clamps y edge cases.
"""
import pytest

from app.core.pricing_engine import (
    PRICE_CEILING_MULTIPLIER,
    PRICE_FLOOR_MULTIPLIER,
    calcular_f_ant,
    calcular_f_dem,
    calcular_f_lix,
    calcular_f_ocu,
    calcular_f_seg,
    calcular_precio,
    clasificar_boleto,
)


# ── Tests de f_ocu ────────────────────────────────────────────────────────────

class TestFOcu:
    def test_bus_vacio(self):
        """Ocupación 0%: factor mínimo cercano a 0.85."""
        assert calcular_f_ocu(0.0) == pytest.approx(0.85, rel=1e-4)

    def test_bus_40_porciento(self):
        """Límite exacto del tramo 1→2: debe ser 1.00."""
        assert calcular_f_ocu(0.40) == pytest.approx(1.00, rel=1e-4)

    def test_bus_55_porciento(self):
        """Ocupación en tramo normal [0.4, 0.7): entre 1.00 y 1.30."""
        f = calcular_f_ocu(0.55)
        assert 1.00 < f < 1.30

    def test_bus_70_porciento(self):
        """Límite exacto del tramo 2→3: debe ser 1.30."""
        assert calcular_f_ocu(0.70) == pytest.approx(1.30, rel=1e-4)

    def test_bus_80_porciento(self):
        """Ocupación alta [0.7, 0.9): entre 1.30 y 1.65."""
        f = calcular_f_ocu(0.80)
        assert 1.30 < f < 1.65

    def test_bus_90_porciento(self):
        """Límite exacto del tramo 3→4: debe ser 1.65."""
        assert calcular_f_ocu(0.90) == pytest.approx(1.65, rel=1e-4)

    def test_bus_lleno(self):
        """Ocupación 100%: factor máximo 2.00."""
        assert calcular_f_ocu(1.00) == pytest.approx(2.00, rel=1e-4)

    def test_ocupacion_negativa_clampeada(self):
        """Ocupación negativa debe tratarse como 0."""
        assert calcular_f_ocu(-0.5) == pytest.approx(calcular_f_ocu(0.0), rel=1e-4)

    def test_ocupacion_mayor_uno_clampeada(self):
        """Ocupación > 1.0 debe tratarse como 1.0."""
        assert calcular_f_ocu(1.5) == pytest.approx(calcular_f_ocu(1.0), rel=1e-4)


# ── Tests de f_ant ────────────────────────────────────────────────────────────

class TestFAnt:
    def test_muy_anticipado_90_dias(self):
        """Compra 90 días antes: descuento early bird máximo (~0.95)."""
        f = calcular_f_ant(90)
        assert f == pytest.approx(0.95, rel=1e-3)

    def test_anticipacion_31_dias(self):
        """Justo pasando el umbral de 30 días: descuento leve."""
        f = calcular_f_ant(31)
        assert 0.80 < f < 1.00

    def test_zona_neutra_15_dias(self):
        """Entre 8 y 30 días: factor neutro = 1.00."""
        assert calcular_f_ant(15) == pytest.approx(1.00, rel=1e-6)

    def test_zona_neutra_8_dias(self):
        """Exactamente 8 días: límite inferior de la zona neutra = 1.00."""
        assert calcular_f_ant(8) == pytest.approx(1.00, rel=1e-6)

    def test_compra_tardia_5_dias(self):
        """5 días: empieza la penalización — entre 1.15 y 1.40."""
        f = calcular_f_ant(5)
        assert 1.15 <= f <= 1.40

    def test_compra_tardia_2_dias(self):
        """A=2 está al tope del tramo [2,8): 1.15 + ((8-2)/6)×0.25 = 1.40."""
        assert calcular_f_ant(2) == pytest.approx(1.40, rel=1e-4)

    def test_ultimo_momento_1_dia(self):
        """1 día: zona muy tardía (< 2 días), entre 1.65 y 1.80."""
        f = calcular_f_ant(1)
        assert 1.65 <= f <= 1.80

    def test_mismo_dia(self):
        """0 días: penalización máxima = 1.80."""
        assert calcular_f_ant(0) == pytest.approx(1.80, rel=1e-4)

    def test_anticipacion_negativa_como_cero(self):
        """Anticipación negativa equivale a 0 días."""
        assert calcular_f_ant(-5) == pytest.approx(calcular_f_ant(0), rel=1e-6)

    def test_monotona_en_zona_baja(self):
        """A menor anticipación (A < 8), mayor penalización."""
        assert calcular_f_ant(6) > calcular_f_ant(7)
        assert calcular_f_ant(1) > calcular_f_ant(2)


# ── Tests de f_dem ────────────────────────────────────────────────────────────

class TestFDem:
    def test_valle(self):
        assert calcular_f_dem("valle") == pytest.approx(0.90)

    def test_normal(self):
        assert calcular_f_dem("normal") == pytest.approx(1.00)

    def test_alta(self):
        assert calcular_f_dem("alta") == pytest.approx(1.20)

    def test_temporada(self):
        assert calcular_f_dem("temporada") == pytest.approx(1.45)

    def test_nivel_invalido(self):
        with pytest.raises(ValueError, match="Nivel de demanda inválido"):
            calcular_f_dem("festivo")


# ── Tests de f_seg ────────────────────────────────────────────────────────────

class TestFSeg:
    def test_ocio(self):
        assert calcular_f_seg("ocio") == pytest.approx(0.95)

    def test_negocios(self):
        assert calcular_f_seg("negocios") == pytest.approx(1.25)

    def test_segmento_invalido(self):
        with pytest.raises(ValueError, match="Segmento inválido"):
            calcular_f_seg("estudiante")


# ── Tests de f_lix ────────────────────────────────────────────────────────────

class TestFLix:
    def test_activo_mismo_dia_bus_vacio(self):
        """Mismo día, bus poco ocupado: f_lix = 0.72."""
        assert calcular_f_lix(0, 0.30) == pytest.approx(0.72)

    def test_activo_agresivo(self):
        """Modelo Flixbus puro usa 0.65."""
        assert calcular_f_lix(0, 0.30, agresivo=True) == pytest.approx(0.65)

    def test_inactivo_mismo_dia_bus_lleno(self):
        """Mismo día pero ocupación >= 60%: f_lix = 1.00."""
        assert calcular_f_lix(0, 0.65) == pytest.approx(1.00)

    def test_inactivo_un_dia_antes(self):
        """1 día antes (no es 'mismo día'): f_lix = 1.00."""
        assert calcular_f_lix(1, 0.30) == pytest.approx(1.00)

    def test_limite_ocupacion_exacta(self):
        """Ocupación exactamente 60%: NO se activa f_lix (condición estricta < 0.60)."""
        assert calcular_f_lix(0, 0.60) == pytest.approx(1.00)

    def test_inactivo_anticipado(self):
        """Compra anticipada: f_lix siempre inactivo."""
        assert calcular_f_lix(15, 0.20) == pytest.approx(1.00)


# ── Tests de clasificar_boleto ────────────────────────────────────────────────

class TestClasificarBoleto:
    def test_clase_e(self):
        assert clasificar_boleto(0.70) == "E"
        assert clasificar_boleto(0.99) == "E"

    def test_clase_s_limite_inferior(self):
        assert clasificar_boleto(1.00) == "S"

    def test_clase_s(self):
        assert clasificar_boleto(1.20) == "S"

    def test_clase_p_limite_inferior(self):
        assert clasificar_boleto(1.35) == "P"

    def test_clase_p(self):
        assert clasificar_boleto(1.80) == "P"

    def test_clase_x_limite_inferior(self):
        assert clasificar_boleto(2.00) == "X"

    def test_clase_x(self):
        assert clasificar_boleto(3.00) == "X"

    def test_multiplcador_bajo_clampea_a_e(self):
        """Multiplicadores por debajo del piso se mapean a Clase E."""
        assert clasificar_boleto(0.50) == "E"


# ── Tests de calcular_precio (integración del motor) ─────────────────────────

class TestCalcularPrecio:
    TARIFA = 380.0  # R1: León → Querétaro

    def test_resultado_hibrido_basico(self):
        """Precio híbrido con parámetros neutros retorna algo razonable."""
        r = calcular_precio(self.TARIFA, 0.50, 15, "normal", "ocio", "hibrido")
        assert r.precio > 0
        assert r.clase in ("E", "S", "P", "X")
        assert r.modelo == "hibrido"
        # f_ocu(0.50) = 1.00 + ((0.50-0.40)/0.30)×0.30 = 1.10; f_ant=1.0, f_dem=1.0, f_seg=0.95
        assert r.multiplicador == pytest.approx(1.10 * 1.00 * 1.00 * 0.95, rel=0.01)

    def test_override_f_ant_cuando_f_lix_activo(self):
        """Cuando f_lix se activa, f_ant debe ser 1.00 en el híbrido."""
        r = calcular_precio(self.TARIFA, 0.30, 0, "normal", "ocio", "hibrido")
        assert r.factores.f_lix == pytest.approx(0.72)
        assert r.factores.f_ant == pytest.approx(1.00), "f_ant debe anularse cuando f_lix activo"

    def test_modelo_aviacion_sin_f_seg_ni_f_lix(self):
        """Aviación puro: f_seg y f_lix deben ser 1.0."""
        r = calcular_precio(self.TARIFA, 0.50, 5, "alta", "negocios", "aviacion")
        assert r.factores.f_seg == pytest.approx(1.00)
        assert r.factores.f_lix == pytest.approx(1.00)
        assert r.modelo == "aviacion"

    def test_modelo_flixbus_solo_ocu_y_lix(self):
        """Flixbus puro: f_ant, f_dem, f_seg deben ser 1.0."""
        r = calcular_precio(self.TARIFA, 0.50, 15, "alta", "negocios", "flixbus")
        assert r.factores.f_ant == pytest.approx(1.00)
        assert r.factores.f_dem == pytest.approx(1.00)
        assert r.factores.f_seg == pytest.approx(1.00)

    def test_clamp_precio_minimo(self):
        """f_lix activo con f_ocu bajo puede llegar al piso P_min = T_base × 0.65."""
        r = calcular_precio(self.TARIFA, 0.05, 0, "valle", "ocio", "hibrido")
        p_min = self.TARIFA * PRICE_FLOOR_MULTIPLIER
        assert r.precio >= p_min - 0.01
        if r.clamped:
            assert r.precio == pytest.approx(p_min, rel=1e-3)

    def test_clamp_precio_maximo(self):
        """Bus lleno + demanda temporada + negocios no debe superar P_max."""
        r = calcular_precio(self.TARIFA, 1.00, 1, "temporada", "negocios", "hibrido")
        p_max = self.TARIFA * PRICE_CEILING_MULTIPLIER
        assert r.precio <= p_max + 0.01

    def test_hibrido_mayor_que_flixbus_compra_anticipada(self):
        """Para compra anticipada con demanda alta, híbrido supera a Flixbus."""
        r_h = calcular_precio(self.TARIFA, 0.80, 1, "alta", "negocios", "hibrido")
        r_f = calcular_precio(self.TARIFA, 0.80, 1, "alta", "negocios", "flixbus")
        assert r_h.precio >= r_f.precio, "Híbrido debe capturar más ingreso en alta demanda"

    def test_desglose_suma_coherente(self):
        """El multiplicador debe ser el producto de todos los factores activos."""
        r = calcular_precio(self.TARIFA, 0.60, 10, "normal", "ocio", "hibrido")
        f = r.factores
        mult_esperado = f.f_ocu * f.f_ant * f.f_dem * f.f_seg * f.f_lix
        assert r.multiplicador == pytest.approx(mult_esperado, rel=1e-3)

    def test_tarifa_base_invalida(self):
        with pytest.raises(ValueError, match="tarifa_base debe ser positiva"):
            calcular_precio(0.0, 0.50, 15)

    def test_modelo_invalido(self):
        with pytest.raises(ValueError, match="Modelo desconocido"):
            calcular_precio(self.TARIFA, 0.50, 15, modelo="magico")

    def test_tres_modelos_mismos_inputs_distintos_resultados(self):
        """Los 3 modelos con los mismos inputs deben generar precios distintos."""
        tarifa = 380.0
        kwargs = dict(ocupacion=0.60, dias_anticipacion=5, nivel_demanda="alta", segmento="negocios")
        r_h = calcular_precio(tarifa, **kwargs, modelo="hibrido")
        r_a = calcular_precio(tarifa, **kwargs, modelo="aviacion")
        r_f = calcular_precio(tarifa, **kwargs, modelo="flixbus")
        precios = {r_h.precio, r_a.precio, r_f.precio}
        assert len(precios) == 3, "Los 3 modelos deben producir precios distintos"

    def test_precio_aumenta_con_ocupacion(self):
        """A mayor ocupación, el precio debe subir (ceteris paribus)."""
        precios = [
            calcular_precio(self.TARIFA, ocu, 15, "normal", "ocio", "hibrido").precio
            for ocu in [0.0, 0.3, 0.6, 0.8, 0.95]
        ]
        assert precios == sorted(precios), "Precio debe aumentar monotónicamente con la ocupación"

    def test_precio_negocios_mayor_que_ocio(self):
        """Segmento negocios debe pagar más que ocio (ceteris paribus)."""
        r_neg = calcular_precio(self.TARIFA, 0.50, 10, "normal", "negocios", "hibrido")
        r_ocio = calcular_precio(self.TARIFA, 0.50, 10, "normal", "ocio", "hibrido")
        assert r_neg.precio > r_ocio.precio

    def test_temporada_vs_valle(self):
        """Temporada debe generar precio significativamente mayor que valle."""
        r_temp = calcular_precio(self.TARIFA, 0.50, 10, "temporada", "ocio", "hibrido")
        r_valle = calcular_precio(self.TARIFA, 0.50, 10, "valle", "ocio", "hibrido")
        assert r_temp.precio > r_valle.precio
        assert r_temp.precio / r_valle.precio == pytest.approx(1.45 / 0.90, rel=0.01)
