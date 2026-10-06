import pytest
from decimal import Decimal, ROUND_HALF_UP

def quantize_money(val) -> Decimal:
    return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_bonificacion_hijos(num_hijos: int) -> Decimal:
    """RN-01: 1 hijo -> 250.000, 2 hijos -> 400.000, >=3 hijos -> 600.000. No acumulable."""
    if num_hijos <= 0:
        return Decimal('0.00')
    elif num_hijos == 1:
        return Decimal('250000.00')
    elif num_hijos == 2:
        return Decimal('400000.00')
    else:
        return Decimal('600000.00')

def calcular_liquidacion_empleado(
    devengado: Decimal,
    num_hijos: int,
    pct_salud: Decimal = Decimal('4.00'),
    pct_pension: Decimal = Decimal('4.00')
):
    """RN-02 y RN-05: Salud 4%, Pensión 4% sobre devengado, neto = devengado + bonif - ded."""
    devengado = quantize_money(devengado)
    bonificacion = calcular_bonificacion_hijos(num_hijos)
    ded_salud = quantize_money(devengado * pct_salud / Decimal('100.00'))
    ded_pension = quantize_money(devengado * pct_pension / Decimal('100.00'))
    neto = devengado + bonificacion - ded_salud - ded_pension
    return {
        "devengado": devengado,
        "bonificacion": bonificacion,
        "deduccion_salud": ded_salud,
        "deduccion_pension": ded_pension,
        "neto": neto
    }

def test_ca02_ejemplo_validado():
    """CA-02: Salario 2.000.000, 4 hijos -> devengado 2.000.000 + bonif 600.000 - salud 80.000 - pensión 80.000 = 2.440.000 exactos."""
    res = calcular_liquidacion_empleado(
        devengado=Decimal('2000000.00'),
        num_hijos=4,
        pct_salud=Decimal('4.00'),
        pct_pension=Decimal('4.00')
    )
    assert res["devengado"] == Decimal('2000000.00')
    assert res["bonificacion"] == Decimal('600000.00')
    assert res["deduccion_salud"] == Decimal('80000.00')
    assert res["deduccion_pension"] == Decimal('80000.00')
    assert res["neto"] == Decimal('2440000.00'), f"Neto esperado 2440000, obtenido {res['neto']}"

def test_rn01_bonificaciones_escalas():
    """RN-01: Escala no acumulable de bonificación por hijos."""
    assert calcular_bonificacion_hijos(0) == Decimal('0.00')
    assert calcular_bonificacion_hijos(1) == Decimal('250000.00')
    assert calcular_bonificacion_hijos(2) == Decimal('400000.00')
    assert calcular_bonificacion_hijos(3) == Decimal('600000.00')
    assert calcular_bonificacion_hijos(5) == Decimal('600000.00')
    assert calcular_bonificacion_hijos(10) == Decimal('600000.00')

def test_rn03_horas_multiplicador():
    """RN-03 y RN-04: Costo de hora dinámica = tarifa_base * multiplicador * horas."""
    tarifa_base = Decimal('11000.00')
    horas_ordinarias = Decimal('8.00')
    mult_ordinaria = Decimal('1.000')
    valor_ord = quantize_money(horas_ordinarias * tarifa_base * mult_ordinaria)
    assert valor_ord == Decimal('88000.00')

    horas_nocturnas = Decimal('8.00')
    mult_nocturna = Decimal('1.350')
    valor_noc = quantize_money(horas_nocturnas * tarifa_base * mult_nocturna)
    assert valor_noc == Decimal('118800.00')

    horas_extras = Decimal('2.00')
    mult_extra = Decimal('1.250')
    valor_ext = quantize_money(horas_extras * tarifa_base * mult_extra)
    assert valor_ext == Decimal('27500.00')

    horas_festivas = Decimal('8.00')
    mult_festiva = Decimal('1.750')
    valor_fes = quantize_money(horas_festivas * tarifa_base * mult_festiva)
    assert valor_fes == Decimal('154000.00')

def test_rn05_neto_formula_consistency():
    """RN-05: El neto siempre debe satisfacer neto = devengado + bonificacion - salud - pensión."""
    for sal in [Decimal('1800000'), Decimal('2500000'), Decimal('3500000'), Decimal('12000000')]:
        for hijos in [0, 1, 2, 3]:
            r = calcular_liquidacion_empleado(sal, hijos)
            assert r["neto"] == r["devengado"] + r["bonificacion"] - r["deduccion_salud"] - r["deduccion_pension"]
