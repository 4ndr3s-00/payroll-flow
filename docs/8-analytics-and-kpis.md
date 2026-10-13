# 📊 Especificación de Analítica y KPIs (Dashboard Gerente)

Este documento especifica las métricas financieras clave y vistas de analítica diseñadas para el panel de control del perfil **Gerente** en **PayrollFlow**.

---

## 1. KPIs Principales (Tarjetas Ejecutivas)

1. **Costo Total Nómina del Período:**
   $$\text{Presupuesto Total} = \sum \text{Neto a Pagar} + \sum \text{Aportes Patronales} + \sum \text{Prestaciones Sociales}$$
   *Indicador:* Obtenido directamente de la vista de base de datos `v_costo_nomina_aprobada`.

2. **Total Bonificaciones Familiares Desembolsadas (RN-01):**
   $$\text{Total Subsidios Hijos} = \sum \text{bonificacion\_hijos}$$
   *Objetivo:* Medir el impacto de la política de bienestar laboral en el gasto presupuestal mensual.

3. **Masa Salarial Base Devengada:**
   $$\text{Total Salarios Base} = \sum \text{devengado\_horas}$$

4. **Distribución del Personal por Rol:**
   * 86 colaboradores activos (1 Gerente, 4 Administrativos, 81 Operarios).

---

## 2. Visualizaciones Gráficas y Consultas Analíticas

### Gráfico A: Distribución del Gasto de Nómina por Perfil Laboral (Donut / Pie Chart)
* **Objetivo:** Mostrar qué porcentaje del presupuesto se destina a cada cargo en el período liquidado.
* **Consulta SQL Optimizada:**
  ```sql
  SELECT 
    p.nombre AS perfil,
    COUNT(ld.id) AS total_colaboradores,
    SUM(ld.neto_pagar) AS total_desembolso_neto,
    ROUND(SUM(ld.neto_pagar) * 100.0 / NULLIF(SUM(SUM(ld.neto_pagar)) OVER (), 0), 2) AS porcentaje_gasto
  FROM liquidacion_detalle ld
  JOIN empleados e ON ld.empleado_id = e.id
  JOIN perfiles p ON e.perfil_id = p.id
  WHERE ld.liquidacion_id = :liquidacion_id
  GROUP BY p.nombre
  ORDER BY total_desembolso_neto DESC;
  ```

### Gráfico B: Tendencia Histórica de la Nómina (Line Chart)
* **Objetivo:** Analizar la evolución y consistencia del gasto salarial consolidado a lo largo del año.
* **Consulta SQL:**
  ```sql
  SELECT 
    l.anio,
    l.mes,
    l.total_neto,
    l.total_bonificaciones,
    l.total_deducciones
  FROM liquidaciones l
  WHERE l.estado = 'APROBADA'
  ORDER BY l.anio ASC, l.mes ASC;
  ```

### Gráfico C: Impacto del Subsidio Familiar por Tramo de Hijos (Bar Chart)
* **Objetivo:** Proporción de colaboradores por cantidad de hijos ($0, 1, 2, \ge 3$) y monto asignado según **RN-01**.
* **Consulta SQL:**
  ```sql
  SELECT 
    CASE 
      WHEN e.num_hijos = 0 THEN '0 hijos ($0)'
      WHEN e.num_hijos = 1 THEN '1 hijo ($250.000)'
      WHEN e.num_hijos = 2 THEN '2 hijos ($400.000)'
      ELSE '>= 3 hijos ($600.000)'
    END AS tramo_subsidio,
    COUNT(e.id) AS cantidad_empleados,
    SUM(ld.bonificacion_hijos) AS total_bonificacion
  FROM liquidacion_detalle ld
  JOIN empleados e ON ld.empleado_id = e.id
  WHERE ld.liquidacion_id = :liquidacion_id
  GROUP BY tramo_subsidio
  ORDER BY total_bonificacion DESC;
  ```

---

## 3. Vistas Analíticas en Base de Datos

* **`v_horas_valorizadas`:** Calcula y expone en tiempo real las horas trabajadas multiplicadas por la tarifa correspondiente del perfil y tipo de hora.
* **`v_costo_nomina_aprobada`:** Agrega el costo patronal total (Salud patronal 8.5%, Pensión patronal 12%, ARL, Sena/ICBF/Cajas y provisiones de cesantías/prima).
