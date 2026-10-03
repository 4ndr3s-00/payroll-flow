# 🔌 Contratos de API (Especificación REST / JSON)

Este documento define los contratos de comunicación entre el frontend (React + Vite) y el servicio de automatización en Python (FastAPI), permitiendo el desarrollo desacoplado.

---

## 1. Disparar Corrida de Liquidación
Ejecuta el cálculo batch de nómina para un mes y año dados.

* **Endpoint:** `POST /api/v1/payroll/calculate`
* **Headers:**
  ```http
  Authorization: Bearer <SUPABASE_JWT_TOKEN>
  Content-Type: application/json
  ```
* **Request Body:**
  ```json
  {
    "period_year": 2026,
    "period_month": 10,
    "dry_run": false
  }
  ```
* **Response `201 Created`:**
  ```json
  {
    "payroll_run_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "period_year": 2026,
    "period_month": 10,
    "status": "BORRADOR",
    "summary": {
      "total_employees_processed": 45,
      "total_base_salary": 98500000.00,
      "total_subsidies": 14200000.00,
      "total_deductions": 8392200.00,
      "total_net_payout": 104307800.00
    },
    "created_at": "2026-10-03T10:00:00Z"
  }
  ```

---

## 2. Simulación / Cálculo Individual Rápido
Permite a la interfaz probar el impacto del cambio de horas o tarifa sin persistir en base de datos.

* **Endpoint:** `POST /api/v1/payroll/simulate-single`
* **Request Body:**
  ```json
  {
    "hours_worked": 200,
    "hourly_rate": 10000.00,
    "num_children": 4,
    "arl_rate": 0.00522
  }
  ```
* **Response `200 OK`:**
  ```json
  {
    "base_salary": 2000000.00,
    "child_subsidy": 600000.00,
    "deductions": {
      "health_4pct": 80000.00,
      "pension_4pct": 80000.00,
      "arl": 10440.00,
      "total_deductions": 170440.00
    },
    "total_devengado": 2600000.00,
    "net_pay": 2429560.00
  }
  ```

---

## 3. Aprobación de Nómina (Exclusivo Gerente)
* **Endpoint:** `PATCH /api/v1/payroll/{payroll_run_id}/approve`
* **Headers:** `Authorization: Bearer <GERENTE_JWT>`
* **Response `200 OK`:**
  ```json
  {
    "payroll_run_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "APROBADO",
    "approved_by": "e67a0304-6ea4-4775-9ce2-9029e843c08f",
    "approved_at": "2026-10-03T10:15:30Z"
  }
  ```
