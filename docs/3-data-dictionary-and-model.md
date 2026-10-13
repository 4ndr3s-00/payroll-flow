# 🗄️ Diccionario de Datos y Modelo Entidad-Relación (PostgreSQL 16)

Este documento describe la arquitectura relacional y el diccionario de datos de **PayrollFlow** según las especificaciones del archivo DDL `01_schema.sql` y la semilla de datos `02_seed.sql`.

---

## 1. Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : "asigna privilegios"
    PERFILES ||--o{ EMPLEADOS : "clasifica cargo"
    EMPLEADOS ||--|| USUARIOS : "posee cuenta de acceso"
    EMPLEADOS ||--o{ REGISTRO_HORAS : "reporta novedades"
    TIPOS_HORA ||--o{ REGISTRO_HORAS : "clasifica hora"
    LIQUIDACIONES ||--o{ LIQUIDACION_DETALLE : "contiene"
    EMPLEADOS ||--o{ LIQUIDACION_DETALLE : "es liquidado"
    LIQUIDACION_DETALLE ||--o{ LIQUIDACION_CONCEPTOS : "desglosa rubros"
    USUARIOS ||--o{ AUDIT_LOG : "genera eventos"

    ROLES {
        smallint id PK
        varchar codigo UK "GERENTE | ADMIN | OPERARIO"
        text descripcion
    }

    PERFILES {
        smallint id PK
        varchar codigo UK
        varchar nombre
        boolean activo
    }

    EMPLEADOS {
        int id PK
        varchar documento UK "Cédula de ciudadanía"
        varchar nombres
        varchar apellidos
        numeric salario_base "Salario de referencia"
        smallint num_hijos "Cantidad acreditada"
        smallint perfil_id FK
        date fecha_ingreso
        boolean activo
    }

    USUARIOS {
        int id PK
        int empleado_id FK UK
        varchar email UK "Correo para login"
        text password_hash "Bcrypt hash"
        smallint rol_id FK
        boolean activo
        timestamptz ultimo_acceso
    }

    REGISTRO_HORAS {
        int id PK
        int empleado_id FK
        smallint tipo_hora_id FK
        smallint jornada_id FK
        date fecha "Restricción RN-08 (no futuro, mes actual)"
        numeric horas "Cantidad laborada"
        varchar estado "PENDIENTE | APROBADA | RECHAZADA"
        timestamptz creado_en
    }

    LIQUIDACIONES {
        int id PK
        int anio
        int mes
        date fecha_liquidacion
        varchar estado "LIQUIDADA | APROBADA | RECHAZADA | ANULADA"
        numeric total_devengado
        numeric total_bonificaciones
        numeric total_deducciones
        numeric total_neto
        int creado_por FK
        int aprobado_por FK
        timestamptz aprobado_en
        timestamptz creado_en
    }

    LIQUIDACION_DETALLE {
        int id PK
        int liquidacion_id FK
        int empleado_id FK
        numeric salario_base
        numeric total_horas_ordinarias
        numeric total_horas_extras
        numeric devengado_horas
        numeric bonificacion_hijos
        numeric deduccion_salud
        numeric deduccion_pension
        numeric neto_pagar
    }

    AUDIT_LOG {
        bigserial id PK
        varchar tabla
        int registro_id
        varchar accion "INSERT | UPDATE | DELETE"
        int usuario_id FK
        jsonb datos_antes
        jsonb datos_despues
        timestamptz creado_en
    }
```

---

## 2. Diccionario de Tablas Principales

### 2.1. `empleados`
Registra a los 86 colaboradores de la empresa financiera.

| Columna | Tipo | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id` | `SERIAL` | PK | Identificador único secuencial. |
| `documento` | `VARCHAR(20)` | NOT NULL, UNIQUE | Documento de identidad / Cédula. |
| `nombres` | `VARCHAR(80)` | NOT NULL | Nombres del colaborador. |
| `apellidos` | `VARCHAR(80)` | NOT NULL | Apellidos del colaborador. |
| `salario_base` | `NUMERIC(14,2)` | CHECK (> 0) | Asignación salarial base. |
| `num_hijos` | `SMALLINT` | CHECK (>= 0) | Número de hijos para el cálculo de bonificación familiar (**RN-01**). |
| `perfil_id` | `SMALLINT` | FK (`perfiles.id`) | Cargo o perfil laboral asignado. |
| `activo` | `BOOLEAN` | DEFAULT TRUE | Estado operativo del empleado en nómina. |

### 2.2. `usuarios`
Cuentas de acceso asociadas 1:1 a cada empleado.

| Columna | Tipo | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id` | `SERIAL` | PK | Identificador único de usuario. |
| `empleado_id` | `INT` | FK (`empleados.id`), UNIQUE | Vínculo directo al colaborador. |
| `email` | `VARCHAR(120)` | NOT NULL, UNIQUE | Correo de inicio de sesión. |
| `password_hash` | `TEXT` | NOT NULL | Hash criptográfico bcrypt de la contraseña. |
| `rol_id` | `SMALLINT` | FK (`roles.id`) | Rol de seguridad (GERENTE, ADMIN, OPERARIO). |
| `activo` | `BOOLEAN` | DEFAULT TRUE | Habilitación de acceso al sistema. |

### 2.3. `registro_horas`
Novedades de tiempo trabajadas reportadas por colaboradores o cargadas por RRHH.

| Columna | Tipo | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id` | `SERIAL` | PK | Identificador de la novedad. |
| `empleado_id` | `INT` | FK (`empleados.id`) | Colaborador que laboró las horas. |
| `tipo_hora_id` | `SMALLINT` | FK (`tipos_hora.id`) | Ordinaria, Nocturna, Extra, Festiva. |
| `fecha` | `DATE` | NOT NULL | Fecha de ejecución (**RN-08**: no futura, mes actual). |
| `horas` | `NUMERIC(4,2)` | CHECK (> 0) | Horas efectivas reportadas. |
| `estado` | `VARCHAR(20)` | DEFAULT 'PENDIENTE' | `PENDIENTE`, `APROBADA`, `RECHAZADA`. |

### 2.4. `liquidaciones`
Cabecera consolidada de la corrida mensual de nómina.

| Columna | Tipo | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id` | `SERIAL` | PK | Identificador de corrida. |
| `anio` | `INT` | NOT NULL | Año del periodo liquidado. |
| `mes` | `INT` | CHECK (1..12) | Mes del periodo liquidado. |
| `estado` | `VARCHAR(20)` | CHECK in ('LIQUIDADA','APROBADA','RECHAZADA','ANULADA') | Estado del ciclo de vida. |
| `total_devengado` | `NUMERIC(14,2)` | NOT NULL | Sumatoria del devengado de todos los empleados. |
| `total_bonificaciones`| `NUMERIC(14,2)`| NOT NULL | Sumatoria de subsidios por hijos (**RN-01**). |
| `total_deducciones` | `NUMERIC(14,2)` | NOT NULL | Sumatoria de salud y pensión (**RN-02**). |
| `total_neto` | `NUMERIC(14,2)` | NOT NULL | Desembolso total neto de la empresa. |
| `aprobado_por` | `INT` | FK (`usuarios.id`) | Gerente que autorizó la nómina. |

### 2.5. `config_bonificacion_hijos` & `config_deducciones`
Tablas de parametrización dinámica con vigencias temporales para cálculo contable sin modificar código.
