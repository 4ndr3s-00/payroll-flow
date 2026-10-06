-- =====================================================================
-- 02_seed.sql — Datos simulados (DEV / PRUEBAS, no usar en producción)
-- Requiere: 01_schema.sql
-- Determinista: setseed() fija el azar → mismos datos en cada ejecución.
-- Contraseña de TODOS los usuarios: Cambiar123*
--   gerente@empresa.test | admin01..04@empresa.test | operario01..80@empresa.test
-- =====================================================================

BEGIN;
SELECT setseed(0.42);

-- ---------------------------------------------------------------------
-- [S1] Catálogos
-- Depende de: roles, perfiles, tipos_hora, jornadas
-- ---------------------------------------------------------------------
INSERT INTO roles (codigo, descripcion) VALUES
    ('GERENTE',  'Aprueba/rechaza liquidaciones y ve reportes'),
    ('ADMIN',    'Configura reglas, gestiona empleados y ejecuta liquidación'),
    ('OPERARIO', 'Registra horas y consulta su volante');

INSERT INTO perfiles (codigo, nombre) VALUES
    ('GERENTE',        'Gerencia'),
    ('ADMINISTRATIVO', 'Personal administrativo'),
    ('OPERADOR',       'Operador');

-- Multiplicadores típicos en Colombia: validar con contador/abogado
INSERT INTO tipos_hora (codigo, nombre, multiplicador) VALUES
    ('ORD', 'Ordinaria', 1.000),
    ('NOC', 'Nocturna',  1.350),
    ('EXT', 'Extra',     1.250),
    ('FES', 'Festiva',   1.750);

-- Supuesto: el documento dice "9pm-5pm"; se interpreta 21:00-05:00
INSERT INTO jornadas (codigo, nombre, hora_inicio, hora_fin) VALUES
    ('DIURNA',   'Jornada diurna',   '08:00', '16:00'),
    ('NOCTURNA', 'Jornada nocturna', '21:00', '05:00');

-- ---------------------------------------------------------------------
-- [S2] Empleados: id 1 = gerente, 2-5 = admins, 6-85 = operarios
-- Depende de: S1 (perfiles). El ORDER BY garantiza los ids.
-- ---------------------------------------------------------------------
INSERT INTO empleados (documento, nombres, apellidos, salario_base, num_hijos, perfil_id, fecha_ingreso)
SELECT
    (1000000000 + s.g)::text,
    (s.nm)[1 + floor(s.r1 * 20)::int],
    (s.ap)[1 + floor(s.r2 * 20)::int] || ' ' || (s.ap)[1 + floor(s.r3 * 20)::int],
    CASE WHEN s.g = 1 THEN 12000000                                   -- gerente
         WHEN s.g <= 5 THEN 3500000 + 250000 * floor(s.r4 * 7)        -- admins
         ELSE               1800000 +  50000 * floor(s.r4 * 17)       -- operarios 1.8M-2.6M
    END,
    CASE WHEN s.r5 < 0.30 THEN 0 WHEN s.r5 < 0.55 THEN 1
         WHEN s.r5 < 0.75 THEN 2 WHEN s.r5 < 0.90 THEN 3
         WHEN s.r5 < 0.97 THEN 4 ELSE 5 END,
    (SELECT id FROM perfiles WHERE codigo =
        CASE WHEN s.g = 1 THEN 'GERENTE' WHEN s.g <= 5 THEN 'ADMINISTRATIVO' ELSE 'OPERADOR' END),
    DATE '2020-01-01' + floor(s.r4 * s.r1 * 2000)::int
FROM (
    SELECT g, random() r1, random() r2, random() r3, random() r4, random() r5,
           ARRAY['Juan','Carlos','Andrés','Luis','Jorge','Camilo','Santiago','Mateo','Sebastián','Daniel',
                 'María','Laura','Paola','Camila','Valentina','Daniela','Sofía','Natalia','Andrea','Carolina'] AS nm,
           ARRAY['García','Rodríguez','Martínez','López','González','Pérez','Sánchez','Ramírez','Torres','Díaz',
                 'Vargas','Castro','Rojas','Moreno','Jiménez','Herrera','Mejía','Ortiz','Cabrera','Pacheco'] AS ap
    FROM generate_series(1, 85) g
) s
ORDER BY s.g;

-- Caso del ejemplo validado (CA-02): salario 2.000.000 y 4 hijos → neto 2.440.000
UPDATE empleados SET salario_base = 2000000, num_hijos = 4 WHERE documento = '1000000006';

-- ---------------------------------------------------------------------
-- [S3] Usuarios (bcrypt calculado UNA sola vez)
-- Depende de: S1 (roles), S2 (empleados)
-- ---------------------------------------------------------------------
INSERT INTO usuarios (empleado_id, email, password_hash, rol_id)
SELECT e.id,
       CASE WHEN e.id = 1  THEN 'gerente@empresa.test'
            WHEN e.id <= 5 THEN 'admin'    || lpad((e.id - 1)::text, 2, '0') || '@empresa.test'
            ELSE                'operario' || lpad((e.id - 5)::text, 2, '0') || '@empresa.test' END,
       pw.h,
       (SELECT id FROM roles WHERE codigo =
           CASE WHEN e.id = 1 THEN 'GERENTE' WHEN e.id <= 5 THEN 'ADMIN' ELSE 'OPERARIO' END)
FROM empleados e
CROSS JOIN (SELECT crypt('Cambiar123*', gen_salt('bf', 10)) AS h) pw
ORDER BY e.id;

-- ---------------------------------------------------------------------
-- [S4] Reglas de negocio configurables (RN-01, RN-02, RF-08)
-- Depende de: S1, S2, S3 (creado_por = admin01)
-- ---------------------------------------------------------------------
INSERT INTO config_deducciones (concepto, porcentaje, vigente_desde, creado_por)
SELECT c, 4.00, DATE '2024-01-01', (SELECT id FROM usuarios WHERE email = 'admin01@empresa.test')
FROM unnest(ARRAY['SALUD','PENSION']) c;

INSERT INTO config_bonificacion_hijos (min_hijos, max_hijos, valor, vigente_desde, creado_por)
SELECT m, x, v, DATE '2024-01-01', (SELECT id FROM usuarios WHERE email = 'admin01@empresa.test')
FROM (VALUES (1, 1, 250000), (2, 2, 400000), (3, NULL, 600000)) AS b(m, x, v);

-- Costo patronal (APORTE) y provisiones (PRESTACION)
-- Valores de REFERENCIA: validar con contador antes de producción
INSERT INTO config_aportes_patronales (codigo, nombre, categoria, porcentaje, aplica_sobre, vigente_desde, creado_por)
SELECT a.c, a.n, a.k, a.p, 'DEVENGADO', DATE '2024-01-01',
       (SELECT id FROM usuarios WHERE email = 'admin01@empresa.test')
FROM (VALUES
    ('SALUD_EMP',   'Salud (empleador)',          'APORTE',      8.50),
    ('PENSION_EMP', 'Pensión (empleador)',        'APORTE',     12.00),
    ('ARL',         'ARL riesgo I',               'APORTE',      0.52),
    ('CAJA',        'Caja de compensación',       'APORTE',      4.00),
    ('PRIMA',       'Prima de servicios',         'PRESTACION',  8.33),
    ('CESANTIAS',   'Cesantías',                  'PRESTACION',  8.33),
    ('INT_CESANT',  'Intereses sobre cesantías',  'PRESTACION',  1.00),
    ('VACACIONES',  'Vacaciones',                 'PRESTACION',  4.17)
) AS a(c, n, k, p);

-- Tarifa base/hora: GLOBAL < PERFIL < EMPLEADO
INSERT INTO tarifas (alcance, perfil_id, empleado_id, tarifa_base, vigente_desde)
VALUES ('GLOBAL', NULL, NULL, 9000, '2024-01-01');

INSERT INTO tarifas (alcance, perfil_id, tarifa_base, vigente_desde)
SELECT 'PERFIL', p.id,
       CASE p.codigo WHEN 'OPERADOR' THEN 11000 WHEN 'ADMINISTRATIVO' THEN 22000 ELSE 68000 END,
       DATE '2024-01-01'
FROM perfiles p;

-- Override por empleado: 3 primeros operarios con tarifa propia
INSERT INTO tarifas (alcance, empleado_id, tarifa_base, vigente_desde)
SELECT 'EMPLEADO', id, 12000, DATE '2024-01-01' FROM empleados WHERE id IN (6, 7, 8);

-- ---------------------------------------------------------------------
-- [S5] Horas aprobadas de SEPTIEMBRE 2026 (periodo listo para liquidar)
-- Depende de: S1, S2, S3
-- ---------------------------------------------------------------------
-- Base: cada empleado × cada día. Nocturnos: operarios con id múltiplo de 4.
CREATE TEMP TABLE tmp_base AS
SELECT e.id AS empleado_id, u.id AS usuario_id, d::date AS fecha,
       extract(isodow FROM d)::int AS dow,
       (e.id > 5 AND e.id % 4 = 0) AS nocturno
FROM empleados e
JOIN usuarios u ON u.empleado_id = e.id
CROSS JOIN generate_series(DATE '2026-09-01', DATE '2026-09-30', INTERVAL '1 day') d;

-- (a) Lunes a viernes: 8 h ordinarias (diurnas) o nocturnas
INSERT INTO registro_horas
    (empleado_id, fecha, tipo_hora_id, jornada_id, horas, estado, registrado_por, aprobado_por, aprobado_en)
SELECT b.empleado_id, b.fecha,
       (SELECT id FROM tipos_hora WHERE codigo = CASE WHEN b.nocturno THEN 'NOC' ELSE 'ORD' END),
       (SELECT id FROM jornadas   WHERE codigo = CASE WHEN b.nocturno THEN 'NOCTURNA' ELSE 'DIURNA' END),
       8, 'APROBADA', b.usuario_id,
       (SELECT id FROM usuarios WHERE email = 'admin01@empresa.test'),
       TIMESTAMPTZ '2026-10-02 09:00-05'
FROM tmp_base b
WHERE b.dow < 6;

-- (b) Horas extra: ~15% de los días hábiles de operarios, 1 a 3 h
INSERT INTO registro_horas
    (empleado_id, fecha, tipo_hora_id, jornada_id, horas, estado, registrado_por, aprobado_por, aprobado_en)
SELECT b.empleado_id, b.fecha,
       (SELECT id FROM tipos_hora WHERE codigo = 'EXT'),
       (SELECT id FROM jornadas   WHERE codigo = CASE WHEN b.nocturno THEN 'NOCTURNA' ELSE 'DIURNA' END),
       1 + floor(random() * 3), 'APROBADA', b.usuario_id,
       (SELECT id FROM usuarios WHERE email = 'admin01@empresa.test'),
       TIMESTAMPTZ '2026-10-02 09:00-05'
FROM tmp_base b
WHERE b.dow < 6 AND b.empleado_id > 5 AND random() < 0.15;

-- (c) Festivas: operarios con id múltiplo de 5 trabajan 2 domingos
INSERT INTO registro_horas
    (empleado_id, fecha, tipo_hora_id, jornada_id, horas, estado, registrado_por, aprobado_por, aprobado_en)
SELECT b.empleado_id, b.fecha,
       (SELECT id FROM tipos_hora WHERE codigo = 'FES'),
       (SELECT id FROM jornadas   WHERE codigo = 'DIURNA'),
       8, 'APROBADA', b.usuario_id,
       (SELECT id FROM usuarios WHERE email = 'admin01@empresa.test'),
       TIMESTAMPTZ '2026-10-02 09:00-05'
FROM tmp_base b
WHERE b.dow = 7 AND b.empleado_id > 5 AND b.empleado_id % 5 = 0
  AND b.fecha IN (DATE '2026-09-13', DATE '2026-09-27');

DROP TABLE tmp_base;

-- ---------------------------------------------------------------------
-- [S6] Verificación (falla y revierte si algo no cuadra)
-- Depende de: fn_bonificacion_hijos, fn_pct_deduccion (01_schema.sql)
-- ---------------------------------------------------------------------
DO $$
DECLARE v_neto NUMERIC;
BEGIN
    ASSERT (SELECT count(*) FROM empleados) = 85,                          'Se esperaban 85 empleados';
    ASSERT (SELECT count(*) FROM usuarios u JOIN roles r ON r.id = u.rol_id WHERE r.codigo = 'OPERARIO') = 80, 'Operarios != 80';
    ASSERT (SELECT count(*) FROM usuarios u JOIN roles r ON r.id = u.rol_id WHERE r.codigo = 'ADMIN')    = 4,  'Admins != 4';
    ASSERT (SELECT count(*) FROM usuarios u JOIN roles r ON r.id = u.rol_id WHERE r.codigo = 'GERENTE')  = 1,  'Gerentes != 1';
    ASSERT (SELECT count(*) FROM config_aportes_patronales) = 8, 'Se esperaban 8 aportes/prestaciones';

    -- CA-02: 2.000.000 + 600.000 - 80.000 - 80.000 = 2.440.000
    SELECT e.salario_base
           + fn_bonificacion_hijos(e.num_hijos, DATE '2026-09-30')
           - e.salario_base * fn_pct_deduccion('SALUD',   DATE '2026-09-30') / 100
           - e.salario_base * fn_pct_deduccion('PENSION', DATE '2026-09-30') / 100
      INTO v_neto
    FROM empleados e WHERE e.documento = '1000000006';
    ASSERT v_neto = 2440000, format('CA-02 falló: neto = %s', v_neto);
END $$;

COMMIT;
