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


# ==============================================================================
# QA Financial Test Matrix (docs/7-qa-financial-test-plan.md)
# ==============================================================================
from backend.services.calculation import simular_calculo_individual

def test_tc01_operario_estandar_cuatro_hijos():
    """TC-01: Operario estándar (4 hijos) -> 200h, 10.000, 4 hijos, ARL 0.522% -> Neto 2.429.560"""
    res = simular_calculo_individual(hours_worked=200, hourly_rate=10000, num_children=4, arl_rate=0.00522)
    assert res["base_salary"] == Decimal('2000000.00')
    assert res["child_subsidy"] == Decimal('600000.00')
    assert res["deductions"]["health_4pct"] == Decimal('80000.00')
    assert res["deductions"]["pension_4pct"] == Decimal('80000.00')
    assert res["deductions"]["arl"] == Decimal('10440.00')
    assert res["deductions"]["total_deductions"] == Decimal('170440.00')
    assert res["total_devengado"] == Decimal('2600000.00')
    assert res["net_pay"] == Decimal('2429560.00')

def test_tc02_tecnico_sin_hijos():
    """TC-02: Técnico sin hijos -> 160h, 12.500, 0 hijos, ARL 0.522% -> Neto 1.829.560"""
    res = simular_calculo_individual(hours_worked=160, hourly_rate=12500, num_children=0, arl_rate=0.00522)
    assert res["base_salary"] == Decimal('2000000.00')
    assert res["child_subsidy"] == Decimal('0.00')
    assert res["deductions"]["health_4pct"] == Decimal('80000.00')
    assert res["deductions"]["pension_4pct"] == Decimal('80000.00')
    assert res["deductions"]["arl"] == Decimal('10440.00')
    assert res["deductions"]["total_deductions"] == Decimal('170440.00')
    assert res["total_devengado"] == Decimal('2000000.00')
    assert res["net_pay"] == Decimal('1829560.00')

def test_tc03_especialista_un_hijo():
    """TC-03: Especialista con 1 hijo -> 180h, 20.000, 1 hijo, ARL 1.044% -> Neto 3.524.416"""
    res = simular_calculo_individual(hours_worked=180, hourly_rate=20000, num_children=1, arl_rate=0.01044)
    assert res["base_salary"] == Decimal('3600000.00')
    assert res["child_subsidy"] == Decimal('250000.00')
    assert res["deductions"]["health_4pct"] == Decimal('144000.00')
    assert res["deductions"]["pension_4pct"] == Decimal('144000.00')
    assert res["deductions"]["arl"] == Decimal('37584.00')
    assert res["deductions"]["total_deductions"] == Decimal('325584.00')
    assert res["total_devengado"] == Decimal('3850000.00')
    assert res["net_pay"] == Decimal('3524416.00')

def test_tc04_operario_dos_hijos():
    """TC-04: Operario con 2 hijos -> 192h, 8.500, 2 hijos, ARL 0.522% -> Neto ~1.892.921"""
    res = simular_calculo_individual(hours_worked=192, hourly_rate=8500, num_children=2, arl_rate=0.00522)
    assert res["base_salary"] == Decimal('1632000.00')
    assert res["child_subsidy"] == Decimal('400000.00')
    assert res["deductions"]["health_4pct"] == Decimal('65280.00')
    assert res["deductions"]["pension_4pct"] == Decimal('65280.00')
    assert round(res["deductions"]["arl"]) == Decimal('8519')
    assert round(res["deductions"]["total_deductions"]) == Decimal('139079')
    assert round(res["net_pay"]) == Decimal('1892921')

def test_tc05_colaborador_tres_hijos_exactos():
    """TC-05: Colaborador con 3 hijos (exactos) -> 160h, 15.000, 3 hijos, ARL 0.522% -> Neto 2.795.472"""
    res = simular_calculo_individual(hours_worked=160, hourly_rate=15000, num_children=3, arl_rate=0.00522)
    assert res["base_salary"] == Decimal('2400000.00')
    assert res["child_subsidy"] == Decimal('600000.00')
    assert res["deductions"]["health_4pct"] == Decimal('96000.00')
    assert res["deductions"]["pension_4pct"] == Decimal('96000.00')
    assert res["deductions"]["arl"] == Decimal('12528.00')
    assert res["deductions"]["total_deductions"] == Decimal('204528.00')
    assert res["total_devengado"] == Decimal('3000000.00')
    assert res["net_pay"] == Decimal('2795472.00')

def test_tc06_horas_cero_incapacidad():
    """TC-06: Horas Cero (Incapacidad o permiso) -> 0h, 15.000, 2 hijos, ARL 0.522% -> Neto 400.000"""
    res = simular_calculo_individual(hours_worked=0, hourly_rate=15000, num_children=2, arl_rate=0.00522)
    assert res["base_salary"] == Decimal('0.00')
    assert res["child_subsidy"] == Decimal('400000.00')
    assert res["deductions"]["health_4pct"] == Decimal('0.00')
    assert res["deductions"]["pension_4pct"] == Decimal('0.00')
    assert res["deductions"]["arl"] == Decimal('0.00')
    assert res["deductions"]["total_deductions"] == Decimal('0.00')
    assert res["total_devengado"] == Decimal('400000.00')
    assert res["net_pay"] == Decimal('400000.00')

