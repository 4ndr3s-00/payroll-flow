# 🏛️ Documento de Diseño de Arquitectura (C4 Model & ADRs)

## 1. Visión General
La arquitectura de **PayrollFlow** sigue un patrón desacoplado y orientado a servicios ligeros:
* **Frontend Web Responsivo:** Single Page Application (SPA) construida en HTML5, Vanilla JavaScript moderno y Tailwind CSS, servida directamente por el backend para evitar problemas de CORS y garantizar baja latencia.
* **Backend API & Motor de Cálculo:** Servicio RESTful en FastAPI (Python 3.11+) con precisión aritmética estricta mediante `Decimal` y generación nativa de documentos PDF con ReportLab.
* **Capa de Datos:** PostgreSQL 16 (desplegado localmente o mediante Docker Compose en el puerto 5435) con esquemas DDL (`01_schema.sql`) y semilla inicializada (`02_seed.sql`) para 86 colaboradores.

---

## 2. Diagrama de Arquitectura de Contenedores

```mermaid
flowchart TB
    subgraph Actores["Usuarios del Sistema"]
        GER["Gerente Financiero\n(Aprobación, Auditoría, KPIs)"]
        ADM["Administrador RRHH\n(Novedades, Liquidación Batch, Empleados)"]
        OPE["Operario / Colaborador\n(Registro Horas <=3 clics, Volante PDF)"]
    end

    subgraph AppServer["Servidor de Aplicación (Host: 127.0.0.1:8000)"]
        subgraph StaticFrontend["Frontend Web SPA"]
            INDEX["index.html\n(Modal de Login con 1-Click Copy Credenciales)"]
            JS["app.js\n(Control de Calendario RN-08, Vistas por Rol)"]
        end

        subgraph FastAPI["FastAPI REST Backend (Python 3.11+)"]
            AUTH_R["/api/auth (JWT + Bcrypt)"]
            LIQ_R["/api/liquidaciones (Transaccional)"]
            HOR_R["/api/horas (Registro RN-08 y Aprobación Lote)"]
            EMP_R["/api/empleados (Catálogo)"]
            REP_R["/api/reportes (Consolidado, PDF, CSV, Auditoría)"]
            CALC["Motor Financiero (Decimal)"]
            PDF_GEN["ReportLab Engine (Volantes y Reportes)"]
        end
    end

    subgraph DataTier["Base de Datos Relacional (PostgreSQL 16)"]
        T_CAT["Catálogos:\nroles, perfiles, tipos_hora, jornadas"]
        T_EMP["Personal:\nempleados (86), usuarios (86)"]
        T_REG["Reglas:\nconfig_deducciones, config_bonificacion_hijos,\nconfig_aportes_patronales, tarifas"]
        T_HOR["Novedades:\nregistro_horas (Estado, Horas, Fechas)"]
        T_LIQ["Nómina:\nliquidaciones, liquidacion_detalle, liquidacion_conceptos"]
        T_AUD["Auditoría Inmutable:\naudit_log + fn_solo_insertar"]
        V_VIEWS["Vistas:\nv_horas_valorizadas, v_costo_nomina_aprobada"]
    end

    GER -->|Navegador Web / HTTPS| INDEX
    ADM -->|Navegador Web / HTTPS| INDEX
    OPE -->|Navegador Web / HTTPS| INDEX

    INDEX --> JS
    JS -->|Llamadas API REST| FastAPI

    FastAPI --> CALC
    FastAPI --> PDF_GEN
    FastAPI -->|Conexión Psycopg2 / Pool| DataTier
```

---

## 3. Decisiones Arquitectónicas Clave (ADRs)

### ADR-01: PostgreSQL 16 con Precisión NUMERIC y Constraints
* **Contexto:** Las normas contables y requerimientos SENA exigen cero pérdidas o ganancias artificiales de centavos.
* **Decisión:** Usar PostgreSQL 16 con campos `NUMERIC(14,2)` y tipos `Decimal` en Python. Prohibido el uso de flotantes binarios (`FLOAT` / `REAL`).
* **Beneficio:** Consistencia matemática absoluta y cumplimiento del estándar de redondeo bancario.

### ADR-02: Aislamiento por Token JWT y Middleware RBAC
* **Contexto:** Se requiere separación rigurosa de privilegios entre Gerencia, RRHH y Operarios.
* **Decisión:** Implementar autenticación JWT en FastAPI con resolución de roles en cada invocación a endpoints protegidos.
* **Beneficio:** Imposibilidad de que un operario acceda a datos salariales de compañeros o altere tarifas empresariales.

### ADR-03: Configuración de Host Local a 127.0.0.1
* **Contexto:** Al enlazar el servidor a `0.0.0.0` en entornos Windows, los navegadores basados en Chromium (Chrome, Edge) arrojaban el error `ERR_ADDRESS_INVALID (-108)`.
* **Decisión:** Establecer por defecto `host="127.0.0.1"` en `run.py`.
* **Beneficio:** Apertura directa y transparente desde enlaces de VS Code y el navegador sin errores de resolución de red.

### ADR-04: Doble Validación Temporal de Novedades (RN-08)
* **Contexto:** Existía el riesgo de reportar horas en fechas futuras o alterar liquidaciones de meses anteriores ya cerrados.
* **Decisión:** Implementar validación en frontend restringiendo el selector de fecha (`min` al primer día del mes, `max` a hoy) y comprobación inmutable en el router de backend (`horas.py`), respondiendo HTTP 400.
* **Beneficio:** Protección integral contra manipulación de periodos en la base de datos.

---

## 4. Flujo de Datos del Ciclo de Nómina

1. **Paso 1 (Parametrización):** Tarifas por perfil y porcentajes de deducción vigentes residen en `tarifas`, `config_deducciones` y `config_bonificacion_hijos`.
2. **Paso 2 (Reporte de Novedades):** Los operarios reportan horas en el portal ($\le$ 3 clics). El backend valida que la fecha pertenezca al mes en curso y no sea futura.
3. **Paso 3 (Aprobación de Horas):** El Administrador revisa y aprueba masivamente las horas (`POST /api/horas/aprobar-lote`).
4. **Paso 4 (Cálculo Batch de Liquidación):** El Administrador dispara `POST /api/liquidaciones`. El motor transaccional procesa a los 86 colaboradores en una sola transacción SQL atómica.
5. **Paso 5 (Aprobación Gerencial):** El Gerente inspecciona el resumen ejecutivo y ejecuta la aprobación (`PATCH /api/liquidaciones/{id}/aprobar`).
6. **Paso 6 (Publicación y Descarga):** Los operarios acceden a su volante individual y pueden descargarlo en formato PDF.
