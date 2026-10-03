# 📊 Especificación de Analítica y KPIs (Dashboard Gerente)

Este documento especifica las métricas financieras clave que el equipo de **Analítica de Datos** diseñará para el panel de control del perfil **Gerente**.

---

## 1. KPIs Principales (Tarjetas Ejecutivas)

1. **Costo Total Nómina del Período:**
   $$\text{Presupuesto Total} = \sum \text{Neto a Pagar} + \sum \text{Aportes Patronales}$$
   *Indicador:* Comparativa porcentual respecto al mes anterior ($\Delta\%$).

2. **Total Bonificaciones Familiares Desembolsadas:**
   $$\text{Total Subsidios Hijos} = \sum \text{Subsidio por Hijos}$$
   *Objetivo:* Medir el impacto de la política de bienestar laboral sobre el gasto total.

3. **Masa Salarial Base Devengada:**
   $$\text{Total Salarios Base} = \sum (\text{Horas} \times \text{Tarifa})$$

4. **Promedio de Horas Laboradas por Colaborador:**
   $$\bar{H} = \frac{\sum \text{Horas Trabajadas}}{\text{Total Empleados Activos}}$$

---

## 2. Visualizaciones Gráficas Requeridas

### Gráfico A: Distribución del Gasto de Nómina por Perfil Laboral (Donut / Pie Chart)
* **Objetivo:** Mostrar qué porcentaje del presupuesto se destina a cada cargo (ej. Operarios $60\%$, Técnicos $25\%$, Especialistas $15\%$).
* **Consulta SQL Sugerida:**
  ```sql
  SELECT 
    p.title AS perfil,
    SUM(pd.net_pay) AS total_pagado
  FROM payroll_details pd
  JOIN employees e ON pd.employee_id = e.id
  JOIN profiles p ON e.profile_id = p.id
  WHERE pd.payroll_run_id = :payroll_run_id
  GROUP BY p.title
  ORDER BY total_pagado DESC;
  ```

### Gráfico B: Tendencia Histórica del Costo de Nómina (Line Chart)
* **Objetivo:** Analizar la evolución de la nómina a lo largo de los últimos 6 o 12 meses.
* **Ejes:** Eje X: Mes/Año, Eje Y: Monto en Millones de COP.

### Gráfico C: Impacto del Subsidio Familiar por Cantidad de Hijos (Bar Chart)
* **Objetivo:** Cuántos colaboradores se ubican en cada tramo ($0, 1, 2, \ge 3$ hijos) y monto acumulado entregado.

---

## 3. Rol del Equipo de Analítica en esta Fase
* Diseñar las vistas SQL (`views`) en Supabase para que las consultas del dashboard sean ultra rápidas.
* Integrar librerías de gráficos en el frontend (como `recharts` o `chart.js`) en la interfaz de Vite + React.
