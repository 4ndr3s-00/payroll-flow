# 🧪 Plan de Pruebas Financieras y Matriz de Validación QA

Este documento sirve como guía para el equipo de **Analítica de Datos** encargado del aseguramiento de calidad (QA) y validación matemática de las liquidaciones de nómina.

---

## 1. Estrategia de Pruebas
Dado que se trata de un sistema financiero, las pruebas deben garantizar:
1. **Determinismo:** Mismos datos de entrada producen exactamente los mismos resultados numéricos.
2. **Precisión Decimal:** Sin pérdidas ni ganancias ficticias de centavos por redondeos imprecisos.
3. **Casos Borde Estrictos:** Comportamiento ante valores límite (0 horas, 0 hijos, más de 3 hijos, sueldos altos).

---

## 2. Matriz de Casos de Prueba (Test Fixtures)

| ID | Escenario | Horas | Tarifa/h | Hijos | ARL (%) | Salario Base | Subsidio Hijos | Salud (4%) | Pensión (4%) | ARL | Total Deduc. | Neto Esperado |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **TC-01** | Operario estándar (4 hijos) | 200 | $10,000 | 4 | 0.522% | $2,000,000 | $600,000 | $80,000 | $80,000 | $10,440 | $170,440 | **$2,429,560** |
| **TC-02** | Técnico sin hijos | 160 | $12,500 | 0 | 0.522% | $2,000,000 | $0 | $80,000 | $80,000 | $10,440 | $170,440 | **$1,829,560** |
| **TC-03** | Especialista con 1 hijo | 180 | $20,000 | 1 | 1.044% | $3,600,000 | $250,000 | $144,000 | $144,000 | $37,584 | $325,584 | **$3,524,416** |
| **TC-04** | Operario con 2 hijos | 192 | $8,500 | 2 | 0.522% | $1,632,000 | $400,000 | $65,280 | $65,280 | $8,519 | $139,079 | **$1,892,921** |
| **TC-05** | Colaborador con 3 hijos (exactos) | 160 | $15,000 | 3 | 0.522% | $2,400,000 | $600,000 | $96,000 | $96,000 | $12,528 | $204,528 | **$2,795,472** |
| **TC-06** | Horas Cero (Incapacidad o permiso) | 0 | $15,000 | 2 | 0.522% | $0 | $400,000 | $0 | $0 | $0 | $0 | **$400,000** |

---

## 3. Script de Prueba Rápida en Python (para el equipo de datos)

El equipo de analítica puede ejecutar y extender este test suite con `pytest`:

```python
import pytest

def calculate_payroll_item(hours: float, rate: float, children: int, arl_rate: float):
    base_salary = round(hours * rate, 2)
    
    # Subsidio por hijos
    if children == 0:
        subsidy = 0.0
    elif children == 1:
        subsidy = 250000.0
    elif children == 2:
        subsidy = 400000.0
    else:
        subsidy = 600000.0
        
    health = round(base_salary * 0.04, 2)
    pension = round(base_salary * 0.04, 2)
    arl = round(base_salary * arl_rate, 2)
    
    total_deductions = round(health + pension + arl, 2)
    net_pay = round(base_salary + subsidy - total_deductions, 2)
    
    return {
        "base_salary": base_salary,
        "subsidy": subsidy,
        "health": health,
        "pension": pension,
        "arl": arl,
        "total_deductions": total_deductions,
        "net_pay": net_pay
    }

def test_tc01_operario_cuatro_hijos():
    res = calculate_payroll_item(200, 10000, 4, 0.00522)
    assert res["base_salary"] == 2000000.00
    assert res["subsidy"] == 600000.00
    assert res["health"] == 80000.00
    assert res["pension"] == 80000.00
    assert res["arl"] == 10440.00
    assert res["net_pay"] == 2429560.00
```
