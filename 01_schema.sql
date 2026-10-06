-- =====================================================================
-- 01_schema.sql — Sistema de Liquidación de Nómina (PostgreSQL 16)
-- Ejecutar PRIMERO. Luego 02_seed.sql.
-- Dinero: NUMERIC (COP). Nunca FLOAT.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- bcrypt: crypt(), gen_salt()
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- EXCLUDE: vigencias sin solaparse

-- =====================================================================
-- [T1] CATÁLOGOS  (RF-01, RF-02, RF-05)
-- Dependencias: ninguna
-- =====================================================================

-- Rol = permisos de acceso (RBAC)
CREATE TABLE roles (
    id          SMALLSERIAL PRIMARY KEY,
    codigo      VARCHAR(20) NOT NULL UNIQUE CHECK (codigo IN ('GERENTE','ADMIN','OPERARIO')),
    descripcion TEXT
);

-- Perfil = clasificación laboral del empleado (hereda tarifas)
CREATE TABLE perfiles (
    id      SMALLSERIAL PRIMARY KEY,
    codigo  VARCHAR(30) NOT NULL UNIQUE,
    nombre  VARCHAR(80) NOT NULL,
    activo  BOOLEAN     NOT NULL DEFAULT TRUE
);

-- RN-03 / RN-04: multiplicadores configurables
CREATE TABLE tipos_hora (
    id            SMALLSERIAL PRIMARY KEY,
    codigo        VARCHAR(10)  NOT NULL UNIQUE,
    nombre        VARCHAR(60)  NOT NULL,
    multiplicador NUMERIC(5,3) NOT NULL CHECK (multiplicador > 0),
    activo        BOOLEAN      NOT NULL DEFAULT TRUE
);

-- Jornadas de trabajo (fuente de datos: registro de horas)
CREATE TABLE jornadas (
    id          SMALLSERIAL PRIMARY KEY,
    codigo      VARCHAR(10) NOT NULL UNIQUE,
    nombre      VARCHAR(40) NOT NULL,
    hora_inicio TIME        NOT NULL,
    hora_fin    TIME        NOT NULL      -- puede cruzar medianoche
);

-- =====================================================================
-- [T2] EMPLEADOS Y USUARIOS  (RF-04, RF-06, RF-07)
-- Dependencias: T1 (perfiles, roles)
-- =====================================================================

CREATE TABLE empleados (
    id             SERIAL PRIMARY KEY,
    documento      VARCHAR(20)   NOT NULL UNIQUE,
    nombres        VARCHAR(80)   NOT NULL,
    apellidos      VARCHAR(80)   NOT NULL,
    salario_base   NUMERIC(14,2) NOT NULL CHECK (salario_base > 0),
    num_hijos      SMALLINT      NOT NULL DEFAULT 0 CHECK (num_hijos >= 0),
    perfil_id      SMALLINT      NOT NULL REFERENCES perfiles(id),
    fecha_ingreso  DATE          NOT NULL DEFAULT CURRENT_DATE,
    activo         BOOLEAN       NOT NULL DEFAULT TRUE
);

-- 1 empleado = 1 usuario de acceso
CREATE TABLE usuarios (
    id             SERIAL PRIMARY KEY,
    empleado_id    INT          NOT NULL UNIQUE REFERENCES empleados(id),
    email          VARCHAR(120) NOT NULL UNIQUE,
    password_hash  TEXT         NOT NULL,          -- bcrypt, nunca texto plano
    rol_id         SMALLINT     NOT NULL REFERENCES roles(id),
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,
    ultimo_acceso  TIMESTAMPTZ
);

-- =====================================================================
-- [T3] REGLAS CONFIGURABLES CON HISTORIAL  (RF-03, RF-08, O5)
-- Dependencias: T1, T2 (usuarios, perfiles, empleados)
-- =====================================================================

-- RN-02: % de deducción (salud, pensión). Sin solapamiento de vigencias.
CREATE TABLE config_deducciones (
    id             SERIAL PRIMARY KEY,
    concepto       VARCHAR(10)  NOT NULL CHECK (concepto IN ('SALUD','PENSION')),
    porcentaje     NUMERIC(5,2) NOT NULL CHECK (porcentaje BETWEEN 0 AND 100),
    vigente_desde  DATE         NOT NULL,
    vigente_hasta  DATE,
    creado_por     INT          REFERENCES usuarios(id),
    creado_en      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde),
    EXCLUDE USING gist (
        concepto WITH =,
        daterange(vigente_desde, vigente_hasta, '[]') WITH &&
    )
);

-- RN-01: bonificación por hijos por rango (no acumulable: aplica UN rango)
CREATE TABLE config_bonificacion_hijos (
    id             SERIAL PRIMARY KEY,
    min_hijos      SMALLINT      NOT NULL CHECK (min_hijos >= 1),
    max_hijos      SMALLINT,                       -- NULL = sin tope (>=)
    valor          NUMERIC(14,2) NOT NULL CHECK (valor >= 0),
    vigente_desde  DATE          NOT NULL,
    vigente_hasta  DATE,
    creado_por     INT           REFERENCES usuarios(id),
    CHECK (max_hijos IS NULL OR max_hijos >= min_hijos),
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde),
    UNIQUE (min_hijos, vigente_desde)
);

-- Costo patronal: lo que la empresa paga ADEMÁS del devengado (costo real)
--   APORTE     = pagos obligatorios a terceros (salud, pensión, ARL, caja)
--   PRESTACION = provisiones al empleado (prima, cesantías, vacaciones)
-- aplica_sobre: base de cálculo (decisión del contador: ¿la bonificación es salarial?)
CREATE TABLE config_aportes_patronales (
    id             SERIAL PRIMARY KEY,
    codigo         VARCHAR(20)  NOT NULL,
    nombre         VARCHAR(60)  NOT NULL,
    categoria      VARCHAR(10)  NOT NULL CHECK (categoria IN ('APORTE','PRESTACION')),
    porcentaje     NUMERIC(5,2) NOT NULL CHECK (porcentaje BETWEEN 0 AND 100),
    aplica_sobre   VARCHAR(20)  NOT NULL DEFAULT 'DEVENGADO'
                   CHECK (aplica_sobre IN ('DEVENGADO','DEVENGADO_BONIF')),
    vigente_desde  DATE         NOT NULL,
    vigente_hasta  DATE,
    creado_por     INT          REFERENCES usuarios(id),
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde),
    EXCLUDE USING gist (
        codigo WITH =,
        daterange(vigente_desde, vigente_hasta, '[]') WITH &&
    )
);

-- RF-08: tarifa base por hora. Herencia: EMPLEADO > PERFIL > GLOBAL
CREATE TABLE tarifas (
    id             SERIAL PRIMARY KEY,
    alcance        VARCHAR(10)   NOT NULL CHECK (alcance IN ('GLOBAL','PERFIL','EMPLEADO')),
    perfil_id      SMALLINT      REFERENCES perfiles(id),
    empleado_id    INT           REFERENCES empleados(id),
    tarifa_base    NUMERIC(12,2) NOT NULL CHECK (tarifa_base > 0),
    vigente_desde  DATE          NOT NULL,
    vigente_hasta  DATE,
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde),
    -- El alcance dicta qué FK debe venir llena
    CONSTRAINT ck_tarifa_alcance CHECK (
        (alcance = 'GLOBAL'   AND perfil_id IS NULL     AND empleado_id IS NULL) OR
        (alcance = 'PERFIL'   AND perfil_id IS NOT NULL AND empleado_id IS NULL) OR
        (alcance = 'EMPLEADO' AND empleado_id IS NOT NULL AND perfil_id IS NULL)
    )
);

-- =====================================================================
-- [T4] REGISTRO DE HORAS  (RF-09, RF-10)
-- Dependencias: T1 (tipos_hora, jornadas), T2 (empleados, usuarios)
-- =====================================================================

CREATE TABLE registro_horas (
    id              BIGSERIAL PRIMARY KEY,
    empleado_id     INT          NOT NULL REFERENCES empleados(id),
    fecha           DATE         NOT NULL,
    tipo_hora_id    SMALLINT     NOT NULL REFERENCES tipos_hora(id),
    jornada_id      SMALLINT     NOT NULL REFERENCES jornadas(id),
    horas           NUMERIC(4,2) NOT NULL CHECK (horas > 0 AND horas <= 24),
    estado          VARCHAR(10)  NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','APROBADA','RECHAZADA')),
    registrado_por  INT          NOT NULL REFERENCES usuarios(id),
    registrado_en   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    aprobado_por    INT          REFERENCES usuarios(id),
    aprobado_en     TIMESTAMPTZ,
    UNIQUE (empleado_id, fecha, tipo_hora_id),
    CHECK (estado = 'PENDIENTE' OR aprobado_por IS NOT NULL)
);
CREATE INDEX ix_horas_emp_fecha ON registro_horas (empleado_id, fecha);
CREATE INDEX ix_horas_fecha_est ON registro_horas (fecha, estado);

-- =====================================================================
-- [T5] LIQUIDACIÓN  (RF-11..RF-14, RN-05..RN-07, O3)
-- Dependencias: T2 (usuarios, empleados), T1 (tipos_hora)
-- =====================================================================

-- Cabecera: 1 corrida por periodo
CREATE TABLE liquidaciones (
    id                SERIAL PRIMARY KEY,
    anio              SMALLINT      NOT NULL CHECK (anio BETWEEN 2000 AND 2100),
    mes               SMALLINT      NOT NULL CHECK (mes BETWEEN 1 AND 12),
    estado            VARCHAR(10)   NOT NULL DEFAULT 'LIQUIDADA'
                      CHECK (estado IN ('LIQUIDADA','APROBADA','RECHAZADA','ANULADA')),
    total_nomina      NUMERIC(16,2) NOT NULL DEFAULT 0,        -- RN-06
    reglas_aplicadas  JSONB         NOT NULL,                  -- snapshot de % y tarifas (O3)
    ejecutada_por     INT           NOT NULL REFERENCES usuarios(id),
    ejecutada_en      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    resuelta_por      INT           REFERENCES usuarios(id),   -- gerente: aprobó/rechazó
    resuelta_en       TIMESTAMPTZ,
    motivo_rechazo    TEXT,
    anulada_por       INT           REFERENCES usuarios(id),
    anulada_en        TIMESTAMPTZ,
    motivo_anulacion  TEXT,
    CHECK (estado <> 'ANULADA' OR (anulada_por IS NOT NULL AND motivo_anulacion IS NOT NULL)),
    CHECK (estado NOT IN ('APROBADA','RECHAZADA') OR resuelta_por IS NOT NULL)
);

-- RN-07: solo UNA liquidación no anulada por periodo
CREATE UNIQUE INDEX ux_liquidacion_periodo_activa
    ON liquidaciones (anio, mes) WHERE estado <> 'ANULADA';

-- Resumen por empleado (snapshot: no depende de cambios futuros)
CREATE TABLE liquidacion_detalle (
    id                  SERIAL PRIMARY KEY,
    liquidacion_id      INT           NOT NULL REFERENCES liquidaciones(id),
    empleado_id         INT           NOT NULL REFERENCES empleados(id),
    perfil_id           SMALLINT      NOT NULL REFERENCES perfiles(id),  -- snapshot: el histórico no se mueve
    salario_base        NUMERIC(14,2) NOT NULL,
    num_hijos           SMALLINT      NOT NULL,
    horas_totales       NUMERIC(8,2)  NOT NULL DEFAULT 0,
    devengado           NUMERIC(14,2) NOT NULL,
    bonificacion        NUMERIC(14,2) NOT NULL DEFAULT 0,
    pct_salud           NUMERIC(5,2)  NOT NULL,
    pct_pension         NUMERIC(5,2)  NOT NULL,
    deduccion_salud     NUMERIC(14,2) NOT NULL,
    deduccion_pension   NUMERIC(14,2) NOT NULL,
    neto                NUMERIC(14,2) NOT NULL,
    aportes_patronales  NUMERIC(14,2) NOT NULL DEFAULT 0,   -- salud, pensión, ARL, caja
    prestaciones        NUMERIC(14,2) NOT NULL DEFAULT 0,   -- prima, cesantías, vacaciones
    costo_empresa       NUMERIC(14,2) NOT NULL,             -- lo que de verdad gasta la empresa
    UNIQUE (liquidacion_id, empleado_id),
    -- RN-05 garantizada por la BD
    CONSTRAINT ck_rn05_neto CHECK (neto = devengado + bonificacion - deduccion_salud - deduccion_pension),
    -- Las deducciones del empleado NO suman: ya están dentro del devengado
    CONSTRAINT ck_costo_empresa CHECK (costo_empresa = devengado + bonificacion + aportes_patronales + prestaciones)
);

-- Desglose por concepto (RF-12): horas por tipo, bonificación, deducciones
CREATE TABLE liquidacion_conceptos (
    id              BIGSERIAL PRIMARY KEY,
    detalle_id      INT           NOT NULL REFERENCES liquidacion_detalle(id),
    tipo            VARCHAR(20)   NOT NULL CHECK (tipo IN ('DEVENGADO','BONIFICACION','DEDUCCION','APORTE_PATRONAL','PRESTACION')),
    concepto        VARCHAR(60)   NOT NULL,
    tipo_hora_id    SMALLINT      REFERENCES tipos_hora(id),
    cantidad        NUMERIC(8,2)  NOT NULL DEFAULT 1,
    valor_unitario  NUMERIC(14,2) NOT NULL,
    valor_total     NUMERIC(14,2) NOT NULL
);

-- =====================================================================
-- [T6] AUDITORÍA  (RF-17, O3)
-- Dependencias: T2 (usuarios)
-- =====================================================================

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INT          REFERENCES usuarios(id),
    accion      VARCHAR(40)  NOT NULL,         -- LOGIN, LIQUIDAR, APROBAR, ANULAR...
    entidad     VARCHAR(40)  NOT NULL,
    entidad_id  VARCHAR(40),
    datos       JSONB,
    ip          INET,
    creado_en   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_entidad ON audit_log (entidad, entidad_id);
CREATE INDEX ix_audit_fecha   ON audit_log (creado_en);

-- =====================================================================
-- [T7] FUNCIONES DE REGLAS  (usadas por el motor de cálculo y por la semilla)
-- Dependencias: T3 (config_*, tarifas), T2 (empleados)
-- =====================================================================

-- RN-01: bonificación vigente según # de hijos (0 si no aplica)
CREATE FUNCTION fn_bonificacion_hijos(p_hijos INT, p_fecha DATE DEFAULT CURRENT_DATE)
RETURNS NUMERIC AS $$
    SELECT COALESCE((
        SELECT valor FROM config_bonificacion_hijos
        WHERE p_hijos BETWEEN min_hijos AND COALESCE(max_hijos, 2147483647)
          AND vigente_desde <= p_fecha
          AND (vigente_hasta IS NULL OR vigente_hasta >= p_fecha)
        ORDER BY vigente_desde DESC LIMIT 1
    ), 0);
$$ LANGUAGE sql STABLE;

-- RN-02: % vigente de SALUD o PENSION
CREATE FUNCTION fn_pct_deduccion(p_concepto VARCHAR, p_fecha DATE DEFAULT CURRENT_DATE)
RETURNS NUMERIC AS $$
    SELECT porcentaje FROM config_deducciones
    WHERE concepto = p_concepto
      AND vigente_desde <= p_fecha
      AND (vigente_hasta IS NULL OR vigente_hasta >= p_fecha)
    ORDER BY vigente_desde DESC LIMIT 1;
$$ LANGUAGE sql STABLE;

-- RF-08: tarifa base vigente con herencia EMPLEADO > PERFIL > GLOBAL
CREATE FUNCTION fn_tarifa_vigente(p_empleado INT, p_fecha DATE)
RETURNS NUMERIC AS $$
    SELECT t.tarifa_base
    FROM tarifas t
    JOIN empleados e ON e.id = p_empleado
    WHERE t.vigente_desde <= p_fecha
      AND (t.vigente_hasta IS NULL OR t.vigente_hasta >= p_fecha)
      AND (   (t.alcance = 'EMPLEADO' AND t.empleado_id = e.id)
           OR (t.alcance = 'PERFIL'   AND t.perfil_id   = e.perfil_id)
           OR  t.alcance = 'GLOBAL')
    ORDER BY CASE t.alcance WHEN 'EMPLEADO' THEN 1 WHEN 'PERFIL' THEN 2 ELSE 3 END,
             t.vigente_desde DESC
    LIMIT 1;
$$ LANGUAGE sql STABLE;

-- RN-03: horas aprobadas valorizadas (tarifa_base × multiplicador × horas)
-- Depende de: fn_tarifa_vigente, registro_horas, tipos_hora
CREATE VIEW v_horas_valorizadas AS
SELECT rh.empleado_id,
       rh.fecha,
       th.codigo        AS tipo_hora,
       rh.horas,
       t.tarifa         AS tarifa_base,
       th.multiplicador,
       ROUND(rh.horas * t.tarifa * th.multiplicador, 2) AS valor
FROM registro_horas rh
JOIN tipos_hora th ON th.id = rh.tipo_hora_id
CROSS JOIN LATERAL (SELECT fn_tarifa_vigente(rh.empleado_id, rh.fecha) AS tarifa) t
WHERE rh.estado = 'APROBADA';

-- =====================================================================
-- [T8] INMUTABILIDAD  (RN-07, CA-04)
-- Liquidación y auditoría son de solo inserción. Anular = UPDATE en cabecera.
-- =====================================================================

CREATE FUNCTION fn_solo_insertar() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % es de solo inserción (auditoría)', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_detalle_inmutable   BEFORE UPDATE OR DELETE ON liquidacion_detalle
    FOR EACH ROW EXECUTE FUNCTION fn_solo_insertar();
CREATE TRIGGER trg_conceptos_inmutable BEFORE UPDATE OR DELETE ON liquidacion_conceptos
    FOR EACH ROW EXECUTE FUNCTION fn_solo_insertar();
CREATE TRIGGER trg_audit_inmutable     BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION fn_solo_insertar();

-- =====================================================================
-- [T9] VISTA DE GASTO REAL PARA EL GERENTE  (O3, RF-15)
-- Solo liquidaciones APROBADAS. Lee snapshots, nunca recalcula.
-- Dependencias: T5 (liquidaciones, detalle), T1 (perfiles)
-- =====================================================================

CREATE VIEW v_costo_nomina_aprobada AS
SELECT l.anio,
       l.mes,
       d.perfil_id,
       p.codigo                                       AS perfil,
       COUNT(*)                                       AS empleados,
       SUM(d.devengado)                               AS devengado,
       SUM(d.bonificacion)                            AS bonificaciones,
       SUM(d.deduccion_salud + d.deduccion_pension)   AS deducciones_empleado,
       SUM(d.neto)                                    AS neto_pagado_empleados,
       SUM(d.aportes_patronales)                      AS aportes_patronales,
       SUM(d.prestaciones)                            AS prestaciones,
       SUM(d.costo_empresa)                           AS costo_total_empresa
FROM liquidaciones l
JOIN liquidacion_detalle d ON d.liquidacion_id = l.id
JOIN perfiles p            ON p.id = d.perfil_id
WHERE l.estado = 'APROBADA'
GROUP BY l.anio, l.mes, d.perfil_id, p.codigo;
