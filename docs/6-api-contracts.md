# 🔌 Contratos de API (Especificación RESTful OpenAPI / JSON)

Este documento define las especificaciones formales de los contratos de comunicación de la API de **PayrollFlow** construida sobre **FastAPI**.

Documentación interactiva disponible en tiempo de ejecución:
* Swagger UI: `http://localhost:8000/docs` o `http://127.0.0.1:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

---

## 1. Módulo de Autenticación (`/api/auth`)

### 1.1. Iniciar Sesión
Autentica al usuario mediante correo electrónico y contraseña (hasheada con bcrypt).

* **Endpoint:** `POST /api/auth/login`
* **Request Body:**
  ```json
  {
    "email": "gerente@empresa.test",
    "password": "Cambiar123*"
  }
  ```
* **Response `200 OK`:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "usuario": {
      "id": 1,
      "email": "gerente@empresa.test",
      "rol": "GERENTE",
      "nombres": "Ana",
      "apellidos": "Gómez",
      "empleado_id": 1
    }
  }
  ```
* **Response `401 Unauthorized`:**
  ```json
  {
    "detail": "Credenciales inválidas"
  }
  ```

### 1.2. Obtener Perfil Actual
* **Endpoint:** `GET /api/auth/me`
* **Headers:** `Authorization: Bearer <JWT>`
* **Response `200 OK`:** Retorna el perfil y rol del usuario autenticado.

---

## 2. Novedades y Horas Laboradas (`/api/horas`)

### 2.1. Registro de Horas (Colaborador / Operario)
Permite al colaborador reportar sus horas laboradas con validación temporal estricta (**RN-08**).

* **Endpoint:** `POST /api/horas/registro`
* **Headers:** `Authorization: Bearer <JWT>`
* **Request Body:**
  ```json
  {
    "empleado_id": 6,
    "tipo_hora_id": 1,
    "fecha": "2026-10-13",
    "horas": 8.0,
    "observacion": "Turno ordinario diurno"
  }
  ```
* **Reglas de Validación Temporal (RN-08):**
  * La `fecha` no puede ser superior a la fecha actual (`fecha <= date.today()`).
  * La `fecha` no puede pertenecer a un mes anterior (`fecha >= date(hoy.year, hoy.month, 1)`).
* **Response `200 OK`:**
  ```json
  {
    "id": 145,
    "empleado_id": 6,
    "tipo_hora_id": 1,
    "fecha": "2026-10-13",
    "horas": 8.0,
    "estado": "PENDIENTE",
    "mensaje": "Horas registradas exitosamente"
  }
  ```
* **Response `400 Bad Request` (Fecha Futura):**
  ```json
  {
    "detail": "No se pueden registrar horas para fechas futuras."
  }
  ```
* **Response `400 Bad Request` (Mes Anterior):**
  ```json
  {
    "detail": "No se pueden registrar horas de meses anteriores. Solo se permite el mes actual."
  }
  ```

### 2.2. Consultar Horas del Empleado Autenticado
* **Endpoint:** `GET /api/horas/mis-horas`
* **Headers:** `Authorization: Bearer <OPERARIO_JWT>`
* **Response `200 OK`:** Lista de novedades de horas reportadas por el operario en sesión con sus estados (`PENDIENTE`, `APROBADA`, `RECHAZADA`).

### 2.3. Novedades Pendientes por Aprobar (Admin)
* **Endpoint:** `GET /api/horas/pendientes`
* **Headers:** `Authorization: Bearer <ADMIN_JWT>`
* **Response `200 OK`:** Lista consolidada de horas pendientes de revisión en la empresa.

### 2.4. Aprobación Masiva de Horas (Admin)
* **Endpoint:** `POST /api/horas/aprobar-lote`
* **Headers:** `Authorization: Bearer <ADMIN_JWT>`
* **Request Body:**
  ```json
  {
    "ids": [140, 141, 142],
    "estado": "APROBADA"
  }
  ```
* **Response `200 OK`:**
  ```json
  {
    "procesados": 3,
    "nuevo_estado": "APROBADA"
  }
  ```

---

## 3. Motor de Liquidación de Nómina (`/api/liquidaciones`)

### 3.1. Ejecución Batch de Liquidación (Admin)
Calcula la nómina completa de todos los empleados activos para el periodo indicado en una sola transacción atómica.

* **Endpoint:** `POST /api/liquidaciones`
* **Headers:** `Authorization: Bearer <ADMIN_JWT>`
* **Request Body:**
  ```json
  {
    "anio": 2026,
    "mes": 10
  }
  ```
* **Response `200 OK`:**
  ```json
  {
    "id": 12,
    "anio": 2026,
    "mes": 10,
    "estado": "LIQUIDADA",
    "total_devengado": 172000000.00,
    "total_bonificaciones": 32400000.00,
    "total_deducciones": 13760000.00,
    "total_neto": 190640000.00,
    "total_empleados": 86,
    "creado_en": "2026-10-13T10:00:00Z"
  }
  ```
* **Response `400 Bad Request`:**
  ```json
  {
    "detail": "Ya existe una liquidación activa para el período 2026-10. Anúlela primero si desea reliquidar."
  }
  ```

### 3.2. Aprobación Oficial de Nómina (Exclusivo Gerente)
* **Endpoint:** `PATCH /api/liquidaciones/{id}/aprobar`
* **Headers:** `Authorization: Bearer <GERENTE_JWT>`
* **Response `200 OK`:** Estado cambia a `APROBADA` y se guarda registro inmutable en `audit_log`.

### 3.3. Rechazo de Nómina (Exclusivo Gerente)
* **Endpoint:** `PATCH /api/liquidaciones/{id}/rechazar`
* **Headers:** `Authorization: Bearer <GERENTE_JWT>`
* **Request Body:**
  ```json
  {
    "motivo": "Revisar novedades de horas extras reportadas en planta."
  }
  ```

### 3.4. Anulación Formal para Reliquidación (Admin)
* **Endpoint:** `PATCH /api/liquidaciones/{id}/anular`
* **Headers:** `Authorization: Bearer <ADMIN_JWT>`
* **Request Body:**
  ```json
  {
    "motivo": "Ajuste de bonificaciones y reingreso de novedades."
  }
  ```

---

## 4. Reportes, Desprendibles y Exportación (`/api/reportes`)

### 4.1. Resumen Ejecutivo (Dashboard Gerente)
* **Endpoint:** `GET /api/reportes/resumen-ejecutivo`
* **Headers:** `Authorization: Bearer <GERENTE_JWT>`
* **Response `200 OK`:** KPIs ejecutivos, masa salarial, costo empresarial y distribución por perfil.

### 4.2. Volante / Desprendible Individual en PDF
* **Endpoint:** `GET /api/reportes/colilla/{detalle_id}/pdf`
* **Query Params:** `token` (opcional si se consulta desde enlace directo) e `inline=true/false`.
* **Response `200 OK`:** Archivo binario con MIME type `application/pdf`.

### 4.3. Consolidado en PDF y CSV
* **Endpoint PDF:** `GET /api/reportes/consolidado/pdf?periodo_id={id}`
* **Endpoint CSV:** `GET /api/reportes/consolidado/csv?periodo_id={id}`

---

## 5. Endpoints de Compatibilidad v1 (`/api/v1/payroll`)

Para asegurar interoperabilidad con clientes externos y tests de integración rápidos:
* `POST /api/v1/payroll/calculate`: Corrida de nómina batch con formato PRD inicial.
* `POST /api/v1/payroll/simulate-single`: Simulación unitaria de salario sin persistencia en base de datos.
* `PATCH /api/v1/payroll/{id}/approve`: Aprobación gerencial formato v1.
