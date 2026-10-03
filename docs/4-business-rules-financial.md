# 💰 Manual de Reglas de Negocio y Lógica Financiera

Este documento formaliza las reglas contables, escalas de subsidios, deducciones fiscales y las fórmulas matemáticas exactas que el equipo de analítica de datos y desarrollo backend debe implementar en el motor de cálculo en Python.

---

## 1. Parámetros de Entrada del Empleado

Para procesar la liquidación individual de un colaborador se requieren los siguientes parámetros:
* $H$: Horas trabajadas en el período reportado ($H \ge 0$).
* $T$: Tarifa por hora dinámica asociada al perfil del empleado ($T > 0$).
* $N_{\text{hijos}}$: Número de hijos declarados y acreditados ($N_{\text{hijos}} \ge 0$).
* $P_{\text{salud}}$: Porcentaje de deducción para Salud ($4.0\% = 0.04$).
* $P_{\text{pensión}}$: Porcentaje de deducción para Pensión ($4.0\% = 0.04$).
* $P_{\text{ARL}}$: Porcentaje de cotización de ARL asignado al perfil laboral (ej. Clase I $= 0.522\% = 0.00522$).

---

## 2. Fórmulas de Cálculo Individual

### 2.1. Salario Base Devengado
El salario base corresponde a la remuneración directa por las horas laboradas:
$$\text{Salario Base} = H \times T$$

### 2.2. Escala de Subsidio / Bonificación por Hijos
La empresa entrega un auxilio familiar no salarial basado en tramos según la cantidad de hijos:

$$\text{Subsidio por Hijos}(N_{\text{hijos}}) = \begin{cases} 
\$0\text{ COP} & \text{si } N_{\text{hijos}} = 0 \\
\$250,000\text{ COP} & \text{si } N_{\text{hijos}} = 1 \\
\$400,000\text{ COP} & \text{si } N_{\text{hijos}} = 2 \\
\$600,000\text{ COP} & \text{si } N_{\text{hijos}} \ge 3 
\end{cases}$$

> [!NOTE]
> Para cualquier cantidad igual o superior a 3 hijos (por ejemplo, 3, 4, 5 o más hijos), el monto del subsidio se mantiene en el tope máximo de **$\$600,000\text{ COP}$**.

### 2.3. Base de Cotización para Seguridad Social (IBC)
Las deducciones de ley aplican sobre el Salario Base ordinario devengado:
$$\text{IBC} = \text{Salario Base}$$

* **Deducción Salud:**
  $$\text{Deducción Salud} = \text{Salario Base} \times 0.04$$
* **Deducción Pensión:**
  $$\text{Deducción Pensión} = \text{Salario Base} \times 0.04$$
* **Deducción ARL:**
  $$\text{Deducción ARL} = \text{Salario Base} \times P_{\text{ARL}}$$

### 2.4. Totales y Neto a Pagar
$$\text{Total Devengado} = \text{Salario Base} + \text{Subsidio por Hijos}$$
$$\text{Total Deducciones} = \text{Deducción Salud} + \text{Deducción Pensión} + \text{Deducción ARL}$$
$$\text{Neto a Pagar} = \text{Total Devengado} - \text{Total Deducciones}$$

---

## 3. Fórmulas de Consolidación Global de la Nómina

Para un conjunto de $M$ empleados activos en el período:

$$\text{Total Salarios Base} = \sum_{i=1}^{M} \text{Salario Base}_i$$
$$\text{Total Subsidios} = \sum_{i=1}^{M} \text{Subsidio por Hijos}_i$$
$$\text{Total Retenciones} = \sum_{i=1}^{M} \text{Total Deducciones}_i$$
$$\text{Presupuesto Total Nómina Empresa} = \sum_{i=1}^{M} \text{Neto a Pagar}_i$$

---

## 4. Casos Prácticos de Validación

### Caso de Prueba 1: Operario con 4 hijos
* **Horas:** $200\text{ horas}$
* **Tarifa:** $\$10,000\text{ COP / hora}$
* **Hijos:** $4\text{ hijos}$
* **ARL:** Clase I ($0.522\%$)
* **Cálculo:**
  * $\text{Salario Base} = 200 \times 10,000 = \$2,000,000$
  * $\text{Subsidio} = \$600,000$ (por estar en tramo $\ge 3$)
  * $\text{Salud} = 2,000,000 \times 0.04 = \$80,000$
  * $\text{Pensión} = 2,000,000 \times 0.04 = \$80,000$
  * $\text{ARL} = 2,000,000 \times 0.00522 = \$10,440$
  * $\text{Total Devengado} = \$2,000,000 + \$600,000 = \$2,600,000$
  * $\text{Total Deducciones} = \$80,000 + \$80,000 + \$10,440 = \$170,440$
  * **$\text{Neto a Pagar} = \$2,600,000 - \$170,440 = \$2,429,560\text{ COP}$**

### Caso de Prueba 2: Técnico con 1 hijo
* **Horas:** $160\text{ horas}$
* **Tarifa:** $\$15,000\text{ COP / hora}$
* **Hijos:** $1\text{ hijo}$
* **ARL:** Clase II ($1.044\%$)
* **Cálculo:**
  * $\text{Salario Base} = 160 \times 15,000 = \$2,400,000$
  * $\text{Subsidio} = \$250,000$
  * $\text{Salud} = 2,400,000 \times 0.04 = \$96,000$
  * $\text{Pensión} = 2,400,000 \times 0.04 = \$96,000$
  * $\text{ARL} = 2,400,000 \times 0.01044 = \$25,056$
  * $\text{Total Devengado} = \$2,400,000 + \$250,000 = \$2,650,000$
  * $\text{Total Deducciones} = \$96,000 + \$96,000 + \$25,056 = \$217,056$
  * **$\text{Neto a Pagar} = \$2,650,000 - \$217,056 = \$2,432,944\text{ COP}$**

---

## 5. Reglas de Integridad y Casos Borde

1. **Horas en Cero ($H = 0$):**
   - El salario base será $\$0$. Si el empleado tiene hijos, ¿se entrega el subsidio? *Regla:* Si el colaborador estuvo activo con contrato vigente en el mes, el subsidio familiar se liquida, pero si no hay salario base suficiente para cubrir deducciones, el sistema emitirá una alerta contable.
2. **Congelación de Tarifas (Snapshots):**
   - La tarifa por hora y horas trabajadas deben guardarse como una copia inmutable en `payroll_details`. Si el perfil cambia de tarifa al mes siguiente, las nóminas históricas ya aprobadas no se alterarán.
3. **Redondeo Numérico:**
   - Todo valor monetario debe redondearse al número entero más cercano o máximo 2 decimales utilizando el estándar bancario (*Half-Even Rounding*).
