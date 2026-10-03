# 🔒 Seguridad, Control de Acceso (RBAC) y Políticas RLS

En un sistema financiero de nómina, la confidencialidad salarial y la segregación de funciones son requisitos indispensables. Este documento define la arquitectura de seguridad basada en **Supabase Auth** y **PostgreSQL Row Level Security (RLS)**.

---

## 1. Definición de Roles

1. **`gerente` (Executive / Approver):**
   - Acceso a dashboards agregados, analíticas de nómina, aprobación formal y reportes contables globales.
   - Restricción: No puede alterar directamente tarifas operativas ni crear empleados individuales para evitar conflictos de interés.
2. **`admin` (Human Resources / Operator):**
   - Configuración de tarifas dinámicas por perfil.
   - Creación y edición de fichas de colaboradores.
   - Ingreso de novedades y horas laboradas.
   - Disparo de la corrida de liquidación en estado `BORRADOR`.
   - Restricción: No puede auto-aprobar definitivamente la nómina para desembolso sin el visto bueno de Gerencia.
3. **`operario` (Colaborador / Empleado):**
   - Acceso al portal de autoservicio.
   - Visualización exclusiva de sus propias horas y sus desprendibles de nómina emitidos.
   - Restricción estricta: Bloqueado totalmente de ver datos de otros compañeros, totales de nómina general o catálogos de tarifas.

---

## 2. Matriz de Permisos (CRUD)

| Tabla | Operario | Admin | Gerente |
| :--- | :---: | :---: | :---: |
| `profiles` | ❌ | Lectura / Escritura | Solo Lectura |
| `employees` | ❌ | Lectura / Escritura | Solo Lectura |
| `time_logs` | Lectura (Solo propio) | Lectura / Escritura | Lectura |
| `payroll_runs` | ❌ | Creación / Lectura | Lectura / Aprobación |
| `payroll_details` | Lectura (Solo propio) | Lectura / Escritura | Lectura (Todo) |

---

## 3. Implementación de Políticas RLS (PostgreSQL / Supabase)

Para garantizar que nadie pueda eludir las reglas desde el cliente frontend, la base de datos aplicará las siguientes políticas RLS:

```sql
-- 1. Habilitar RLS en tablas críticas
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_runs ENABLE ROW LEVEL SECURITY;

-- 2. El Operario solo puede consultar su propio detalle de nómina
CREATE POLICY "Operarios ven su propio recibo"
ON payroll_details
FOR SELECT
USING (
  employee_id IN (
    SELECT id FROM employees WHERE user_id = auth.uid()
  )
);

-- 3. Los Administradores y Gerentes pueden ver todos los detalles
CREATE POLICY "Admins y Gerentes ven todos los detalles"
ON payroll_details
FOR ALL
USING (
  auth.jwt() ->> 'role' IN ('admin', 'gerente')
);

-- 4. Solo el Gerente puede aprobar nóminas
CREATE POLICY "Solo Gerente puede aprobar liquidacion"
ON payroll_runs
FOR UPDATE
USING (
  auth.jwt() ->> 'role' = 'gerente'
)
WITH CHECK (
  auth.jwt() ->> 'role' = 'gerente'
);
```

---

## 4. Auditoría y Trazabilidad

Cada ciclo de liquidación registra un rastro de auditoría inmutable:
* **`created_by`**: UUID del Administrador que ejecutó el cálculo.
* **`approved_by`**: UUID del Gerente que autorizó el pago.
* **`approved_at`**: Marca de tiempo UTC del momento exacto del visto bueno.
* **Inmutabilidad:** Una vez que `payroll_runs.status = 'APROBADO'` o `'PAGADO'`, ningún registro en `payroll_details` puede ser editado o eliminado.
