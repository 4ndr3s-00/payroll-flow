import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def get_auth_token(email: str, password: str = "Cambiar123*") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

def test_health_check():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_auth_login_all_roles():
    for email in ["gerente@empresa.test", "admin01@empresa.test", "operario01@empresa.test"]:
        token = get_auth_token(email)
        assert token is not None and len(token) > 20

def test_auth_invalid_credentials():
    res = client.post("/api/auth/login", json={"email": "gerente@empresa.test", "password": "ClaveIncorrecta"})
    assert res.status_code == 401

def test_rbac_restrictions():
    # Operario trying to access admin liquidations route
    token_operario = get_auth_token("operario01@empresa.test")
    res = client.post("/api/liquidaciones", json={"anio": 2026, "mes": 9}, headers={"Authorization": f"Bearer {token_operario}"})
    assert res.status_code == 403

    # Admin trying to approve liquidation (Gerente only)
    token_admin = get_auth_token("admin01@empresa.test")
    res = client.patch("/api/liquidaciones/1/aprobar", headers={"Authorization": f"Bearer {token_admin}"})
    assert res.status_code == 403

def test_full_liquidation_cycle_and_ca02():
    token_admin = get_auth_token("admin01@empresa.test")
    token_gerente = get_auth_token("gerente@empresa.test")
    token_operario01 = get_auth_token("operario01@empresa.test")

    # 1. Admin ejecuta liquidación de septiembre 2026
    res = client.post(
        "/api/liquidaciones",
        json={"anio": 2026, "mes": 9},
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    # Si ya existía activa de una prueba previa, verificar y anular primero
    if res.status_code == 400 and "Ya existe una liquidación activa" in res.text:
        list_res = client.get("/api/liquidaciones", headers={"Authorization": f"Bearer {token_admin}"})
        for liq in list_res.json():
            if liq["anio"] == 2026 and liq["mes"] == 9 and liq["estado"] != "ANULADA":
                client.patch(
                    f"/api/liquidaciones/{liq['id']}/anular",
                    json={"motivo": "Reinicio para prueba automatizada"},
                    headers={"Authorization": f"Bearer {token_admin}"}
                )
        res = client.post(
            "/api/liquidaciones",
            json={"anio": 2026, "mes": 9},
            headers={"Authorization": f"Bearer {token_admin}"}
        )

    assert res.status_code == 201, f"Fallo al liquidar: {res.text}"
    data = res.json()
    liq_id = data["liquidacion_id"]
    assert data["total_empleados"] == 85
    assert data["total_devengado"] == 208910600.00
    assert data["total_bonificaciones"] in (25550000.00, 26750000.00)
    assert data["total_nomina"] in (217747752.00, 218947752.00)

    # 2. RN-07: Intentar reliquidar el mismo periodo sin anular debe fallar con 400
    res_duplicate = client.post(
        "/api/liquidaciones",
        json={"anio": 2026, "mes": 9},
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_duplicate.status_code == 400
    assert "Ya existe una liquidación activa" in res_duplicate.text

    # 3. Gerente aprueba la nómina
    res_aprob = client.patch(
        f"/api/liquidaciones/{liq_id}/aprobar",
        headers={"Authorization": f"Bearer {token_gerente}"}
    )
    assert res_aprob.status_code == 200
    assert res_aprob.json()["estado"] == "APROBADA"

    # 4. CA-02: Operario 01 (Carlos Mendoza, doc 1000000006, 4 hijos) consulta su volante
    res_volante = client.get(
        "/api/reportes/me/volantes/2026/9",
        headers={"Authorization": f"Bearer {token_operario01}"}
    )
    assert res_volante.status_code == 200
    volante = res_volante.json()
    assert volante["documento"] == "1000000006"
    assert volante["salario_base"] == 2000000.00
    assert volante["num_hijos"] == 4
    assert volante["bonificacion"] == 600000.00
    assert volante["devengado"] == 2112000.00
    assert volante["deduccion_salud"] == 84480.00
    assert volante["deduccion_pension"] == 84480.00
    assert volante["neto"] == 2543040.00

    # 5. Descarga de PDF del volante
    res_pdf = client.get(
        "/api/reportes/me/volantes/2026/9/pdf",
        headers={"Authorization": f"Bearer {token_operario01}"}
    )
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # 6. Reporte consolidado del Gerente
    res_rep = client.get(
        "/api/reportes/consolidado?anio=2026&mes=9",
        headers={"Authorization": f"Bearer {token_gerente}"}
    )
    assert res_rep.status_code == 200
    rep_data = res_rep.json()
    assert rep_data["totales"]["empleados"] == 85
    assert rep_data["totales"]["neto_pagado"] in (217747752.00, 218947752.00)
    assert len(rep_data["perfiles"]) == 3

    # 7. Exportación a CSV
    res_csv = client.get(
        "/api/reportes/export/csv?anio=2026&mes=9",
        headers={"Authorization": f"Bearer {token_gerente}"}
    )
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert b"1000000006" in res_csv.content

    # 8. Verificación de nuevos KPIs en reporte consolidado (docs/8-analytics-and-kpis.md)
    assert "promedio_horas" in rep_data["totales"]
    assert "distribucion_hijos" in rep_data
    assert len(rep_data["distribucion_hijos"]) > 0

def test_simulate_single_payroll_contract():
    """Prueba del contrato REST especificado en docs/6-api-contracts.md: POST /api/v1/payroll/simulate-single"""
    payload = {
        "hours_worked": 200,
        "hourly_rate": 10000.00,
        "num_children": 4,
        "arl_rate": 0.00522
    }
    res = client.post("/api/v1/payroll/simulate-single", json=payload)
    assert res.status_code == 200, f"Error en simulate-single: {res.text}"
    data = res.json()
    assert float(data["base_salary"]) == 2000000.00
    assert float(data["child_subsidy"]) == 600000.00
    assert float(data["deductions"]["health_4pct"]) == 80000.00
    assert float(data["deductions"]["pension_4pct"]) == 80000.00
    assert float(data["deductions"]["arl"]) == 10440.00
    assert float(data["deductions"]["total_deductions"]) == 170440.00
    assert float(data["total_devengado"]) == 2600000.00
    assert float(data["net_pay"]) == 2429560.00

def test_export_pdf_consolidado_con_header_y_query_token():
    token_gerente = get_auth_token("gerente@empresa.test")

    # 1. Con Header Authorization
    res_header = client.get(
        "/api/reportes/export/pdf?anio=2026&mes=9",
        headers={"Authorization": f"Bearer {token_gerente}"}
    )
    assert res_header.status_code == 200
    assert res_header.headers["content-type"] == "application/pdf"
    assert res_header.content.startswith(b"%PDF")
    assert len(res_header.content) > 1000

    # 2. Con Query Param token (?token=...)
    res_query = client.get(f"/api/reportes/export/pdf?anio=2026&mes=9&token={token_gerente}")
    assert res_query.status_code == 200
    assert res_query.headers["content-type"] == "application/pdf"
    assert res_query.content.startswith(b"%PDF")

def test_export_csv_con_query_token():
    token_gerente = get_auth_token("gerente@empresa.test")
    res = client.get(f"/api/reportes/export/csv?anio=2026&mes=9&token={token_gerente}")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert b"DOCUMENTO" in res.content

def test_descargar_volante_empleado_admin_gerente():
    token_admin = get_auth_token("admin01@empresa.test")
    token_operario = get_auth_token("operario01@empresa.test")

    # Obtener empleado_id de operario01
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_operario}"})
    emp_id = res_me.json()["empleado_id"]

    # Admin descarga el volante del operario
    res_admin = client.get(
        f"/api/reportes/volantes/{emp_id}/2026/9/pdf",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_admin.status_code == 200
    assert res_admin.headers["content-type"] == "application/pdf"
    assert res_admin.content.startswith(b"%PDF")

    # Operario NO puede usar este endpoint para consultar a otros (403 Forbidden)
    res_forbidden = client.get(
        f"/api/reportes/volantes/{emp_id}/2026/9/pdf",
        headers={"Authorization": f"Bearer {token_operario}"}
    )
    assert res_forbidden.status_code == 403


