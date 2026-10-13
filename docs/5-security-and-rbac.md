# 🔒 Seguridad, Control de Acceso (RBAC) y Auditoría

En un sistema financiero de nómina, la confidencialidad salarial y la segregación de funciones son requisitos indispensables. Este documento formaliza la arquitectura de seguridad basada en **JWT (JSON Web Tokens)** con encriptación **bcrypt**, middleware de roles en **FastAPI** e inmutabilidad en **PostgreSQL 16**.

---

## 1. Definición de Roles del Sistema (RBAC)

1. **👑 `GERENTE` (Aprobador Ejecutivo):**
   - Acceso exclusivo al Dashboard Estratégico y analíticas financieras consolidadas.
   - Autoridad para **Aprobar** (`PATCH /api/liquidaciones/{id}/aprobar`) o **Rechazar** (`PATCH /api/liquidaciones/{id}/rechazar`) con motivo formal las liquidaciones de nómina.
   - Consulta de la bitácora de auditoría en vivo (`GET /api/reportes/auditoria`).
   - Exportación de informes consolidados de nómina en PDF y CSV.
   - *Restricción:* No puede modificar tarifas horarias ni crear empleados para prevenir conflictos de interés.

2. **💼 `ADMIN` (Operador de Nómina y RRHH):**
   - Parametrización de perfiles laborales, tarifas base y reglas temporales.
   - Gestión integral del catálogo de colaboradores (altas, modificaciones, número de hijos).
   - Aprobación masiva o individual de novedades de horas reportadas.
   - Disparo del motor de liquidación batch (`POST /api/liquidaciones`).
   - Anulación justificada de liquidaciones para reliquidación (`PATCH /api/liquidaciones/{id}/anular`).
   - *Restricción:* No puede auto-aprobar definitivamente una liquidación para desembolso financiero.

3. **👷 `OPERARIO` (Colaborador / Empleado):**
   - Acceso al autoservicio de colaborador.
   - Registro de novedades de horas trabajadas en $\le$ 3 clics con control de calendario limitado al mes actual (**RN-08**).
   - Visualización y descarga individual de sus desprendibles de pago en PDF.
   - *Restricción estricta:* Bloqueado de consultar liquidaciones globales, tarifas de otros cargos o datos de compañeros.

---

## 2. Matriz de Permisos por Endpoint

| Endpoint / Módulo | Operario | Admin | Gerente |
| :--- | :---: | :---: | :---: |
| `POST /api/auth/login` | ✅ Público | ✅ Público | ✅ Público |
| `GET /api/auth/me` | ✅ Propio | ✅ Propio | ✅ Propio |
| `POST /api/horas/registro` | ✅ Propio (RN-08) | ✅ Sí | ❌ |
| `GET /api/horas/mis-horas` | ✅ Propio | ✅ Propio | ✅ Propio |
| `GET /api/horas/pendientes` | ❌ | ✅ Sí | ❌ |
| `POST /api/horas/aprobar-lote` | ❌ | ✅ Sí | ❌ |
| `POST /api/liquidaciones` | ❌ | ✅ Sí | ❌ |
| `PATCH /api/liquidaciones/{id}/anular`| ❌ | ✅ Sí | ❌ |
| `PATCH /api/liquidaciones/{id}/aprobar`| ❌ | ❌ | ✅ Exclusivo |
| `PATCH /api/liquidaciones/{id}/rechazar`| ❌ | ❌ | ✅ Exclusivo |
| `GET /api/reportes/resumen-ejecutivo` | ❌ | ❌ | ✅ Sí |
| `GET /api/reportes/auditoria` | ❌ | ❌ | ✅ Sí |
| `GET /api/reportes/colilla/{id}/pdf` | ✅ Propia | ✅ Sí | ✅ Sí |

---

## 3. Seguridad de Autenticación y Criptografía

* **Almacenamiento de Contraseñas:** Encriptadas mediante `bcrypt` (`passlib.context.CryptContext` en Python / extensión `pgcrypto` en PostgreSQL). Ninguna contraseña se almacena en texto plano.
* **Tokens de Acceso JWT:** Firmados criptográficamente mediante algoritmo HMAC-SHA256 (`HS256`) con clave secreta y tiempo de expiración configurable.
* **Panel Rápido de Credenciales:** La interfaz de desarrollo incorpora etiquetas `<code>` de 1 clic que facilitan la alternancia entre perfiles (`gerente@empresa.test`, `admin01@empresa.test`, `operario01@empresa.test`, `jesucantillo30@gmail.com`) sin comprometer el aislamiento en backend.

---

## 4. Inmutabilidad y Auditoría Forense (`audit_log`)

Cada acción crítica del sistema dispara un registro transaccional en la tabla `audit_log`:
* **Creación de liquidación:** Registra ID de usuario administrador, periodo liquidado y montos totales iniciales.
* **Aprobación o rechazo:** Registra ID del gerente, marca temporal UTC y motivo formal en caso de rechazo.
* **Anulación:** Registra ID del administrador, justificación de reliquidación y congelamiento del registro anulado.
* **Triggers de inmutabilidad (`fn_solo_insertar`):** Los detalles de liquidaciones aprobadas y los registros de auditoría no pueden ser modificados ni eliminados (`DELETE` y `UPDATE` restringidos a nivel de base de datos).
