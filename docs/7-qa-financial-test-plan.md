# 🧪 Plan de Pruebas Financieras y Matriz de Validación QA

Este documento sirve como guía para el equipo de **Analítica de Datos** y control de calidad (QA) para el aseguramiento matemático, de reglas de negocio y consistencia operativa de **PayrollFlow**.

---

## 1. Estrategia de Pruebas
Dado que se trata de un sistema financiero, las pruebas garantizan:
1. **Determinismo:** Mismos datos de entrada producen exactamente los mismos resultados numéricos.
2. **Precisión Decimal:** Sin pérdidas ni ganancias ficticias de centavos por redondeos imprecisos (`Decimal` en Python y `NUMERIC(14,2)` en PostgreSQL).
3. **Casos Borde Estrictos:** Comportamiento ante valores límite (0 horas, 0 hijos, más de 3 hijos, sueldos altos).
4. **Validaciones Temporales (RN-08):** Inmutabilidad del pasado cerrado y bloqueo contra anticipación indebida de horas futuras.

---

## 2. Matriz de Casos de Prueba Financieros (Test Fixtures)

| ID | Escenario | Horas | Tarifa/h | Hijos | ARL (%) | Salario Base | Subsidio Hijos | Salud (4%) | Pensión (4%) | ARL | Total Deduc. | Neto Esperado |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **TC-01** | Operario estándar (4 hijos) | 200 | $10,000 | 4 | 0.522% | $2,000,000 | $600,000 | $80,000 | $80,000 | $10,440 | $170,440 | **$2,429,560** |
| **TC-02** | Técnico sin hijos | 160 | $12,500 | 0 | 0.522% | $2,000,000 | $0 | $80,000 | $80,000 | $10,440 | $170,440 | **$1,829,560** |
| **TC-03** | Especialista con 1 hijo | 180 | $20,000 | 1 | 1.044% | $3,600,000 | $250,000 | $144,000 | $144,000 | $37,584 | $325,584 | **$3,524,416** |
| **TC-04** | Operario con 2 hijos | 192 | $8,500 | 2 | 0.522% | $1,632,000 | $400,000 | $65,280 | $65,280 | $8,519 | $139,079 | **$1,892,921** |
| **TC-05** | Colaborador con 3 hijos (exactos) | 160 | $15,000 | 3 | 0.522% | $2,400,000 | $600,000 | $96,000 | $96,000 | $12,528 | $204,528 | **$2,795,472** |
| **TC-06** | Horas Cero (Incapacidad o permiso) | 0 | $15,000 | 2 | 0.522% | $0 | $400,000 | $0 | $0 | $0 | $0 | **$400,000** |

---

## 3. Matriz de Validación de Novedades de Horas (RN-08)

| ID | Escenario | Fecha Reportada | Resultado Esperado | Código HTTP |
| :---: | :--- | :--- | :--- | :---: |
| **TC-07** | Intento de registro en fecha futura | `CURRENT_DATE + 1` día | Rechazado: *"No se pueden registrar horas para fechas futuras."* | `400 Bad Request` |
| **TC-08** | Intento de registro en mes anterior | Último día del mes anterior | Rechazado: *"No se pueden registrar horas de meses anteriores. Solo se permite el mes actual."* | `400 Bad Request` |
| **TC-09** | Registro en fecha válida del mes actual | `CURRENT_DATE` o días transcurridos del mes | Aceptado: Novedad guardada en estado `PENDIENTE` | `200 OK` |
| **TC-10** | Consulta de volante de pago | Operario autenticado | Generación de PDF con desglose matemático verificado | `200 OK (application/pdf)` |

---

## 4. Ejecución del Suite Automatizado

La suite de pruebas contiene **21 pruebas automatizadas** ejecutadas con `pytest`:

```powershell
python -m pytest tests/ -v
```

### Inventario de Pruebas:
1. `tests/test_calculator.py::test_ca02_ejemplo_validado`
2. `tests/test_calculator.py::test_rn01_bonificaciones_escalas`
3. `tests/test_calculator.py::test_rn03_horas_multiplicador`
4. `tests/test_calculator.py::test_rn05_neto_formula_consistency`
5. `tests/test_calculator.py::test_tc01_operario_estandar_cuatro_hijos`
6. `tests/test_calculator.py::test_tc02_tecnico_sin_hijos`
7. `tests/test_calculator.py::test_tc03_especialista_un_hijo`
8. `tests/test_calculator.py::test_tc04_operario_dos_hijos`
9. `tests/test_calculator.py::test_tc05_colaborador_tres_hijos_exactos`
10. `tests/test_calculator.py::test_tc06_horas_cero_incapacidad`
11. `tests/test_api.py::test_health_check`
12. `tests/test_api.py::test_auth_login_all_roles`
13. `tests/test_api.py::test_auth_invalid_credentials`
14. `tests/test_api.py::test_rbac_restrictions`
15. `tests/test_api.py::test_full_liquidation_cycle_and_ca02`
16. `tests/test_api.py::test_simulate_single_payroll_contract`
17. `tests/test_api.py::test_export_pdf_consolidado_con_header_y_query_token`
18. `tests/test_api.py::test_export_csv_con_query_token`
19. `tests/test_api.py::test_descargar_volante_empleado_admin_gerente`
20. `tests/test_api.py::test_pdf_inline_mode_and_jesus_cantillo`
21. `tests/test_api.py::test_registro_horas_rechaza_fechas_futuras_y_meses_anteriores`
