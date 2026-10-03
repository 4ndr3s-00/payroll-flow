# 📄 PRD — Documento de Requerimientos del Producto (PayrollFlow)

## 1. Visión del Producto
**PayrollFlow** es una plataforma web fintech diseñada para automatizar la liquidación periódica de nómina en empresas con tarifas horarias dinámicas y beneficios familiares progresivos. El sistema busca erradicar el error humano, garantizar la consistencia en deducciones obligatorias y ofrecer una visualización analítica de alto nivel para la toma de decisiones financieras.

---

## 2. Objetivos de Negocio
* **Precisión Contable:** 100% de exactitud matemática en salarios base, bonificaciones familiares y deducciones legales de salud, pensión y riesgos laborales.
* **Agilidad Operativa:** Reducir el tiempo de liquidación de horas hombre de días a minutos mediante procesos por lotes.
* **Segregación de Responsabilidades:** Separación estricta de privilegios entre Gerencia (aprobación/analítica), Administración (operación/configuración) y Empleados (consulta).
* **Auditabilidad:** Registro histórico inmutable de cada ciclo de nómina ejecutado y aprobado.

---

## 3. Personas y Casos de Uso

### 3.1. Persona 1: Gerente Financiero (Role: `gerente`)
* **Necesidad:** Visualizar el impacto presupuestal global, aprobar nóminas y analizar tendencias de gasto salarial.
* **Historias de Usuario:**
  * Como Gerente, quiero visualizar un dashboard con el costo consolidado de la nómina para conocer el egreso total del período.
  * Como Gerente, quiero revisar el detalle de la liquidación antes de aprobarla formalmente.
  * Como Gerente, quiero exportar reportes ejecutivos en PDF/Excel para auditorías financieras.

### 3.2. Persona 2: Administrador de RRHH (Role: `admin`)
* **Necesidad:** Gestionar empleados, configurar perfiles de cargo con sus tarifas horarias y ejecutar el motor de cálculo.
* **Historias de Usuario:**
  * Como Admin, quiero crear y editar perfiles con su tarifa horaria dinámica para que el sistema calcule el salario base correspondiente.
  * Como Admin, quiero registrar empleados con sus datos demográficos y número de hijos verificados.
  * Como Admin, quiero cargar las horas trabajadas por empleado en el período.
  * Como Admin, quiero disparar el motor de liquidación automatizado y revisar preliminares.

### 3.3. Persona 3: Operario / Colaborador (Role: `operario`)
* **Necesidad:** Consultar sus horas registradas y descargar su desprendible de pago con total transparencia.
* **Historias de Usuario:**
  * Como Operario, quiero iniciar sesión de forma segura y ver únicamente mi información contractual.
  * Como Operario, quiero visualizar el desglose de mi colilla de pago: salario base, subsidio por hijos y deducciones de seguridad social.

---

## 4. Requerimientos Funcionales (RF)

* **RF-01 (Gestión de Perfiles y Tarifas):** El sistema debe permitir crear, actualizar y desactivar perfiles laborales, asignando un costo por hora dinámico expresado en moneda legal.
* **RF-02 (Gestión de Empleados):** Registro de documento, nombres, apellidos, correo, estado activo/inactivo, perfil asignado y cantidad de hijos a cargo.
* **RF-03 (Registro de Novedades de Horas):** Entrada de horas laboradas por período (mes/año) con validación de no negatividad y límites legales.
* **RF-04 (Motor de Liquidación Automática):**
  * Cálculo de Salario Base = $\text{Horas} \times \text{Tarifa}$.
  * Cálculo de Bonificación por Hijos según escala ($0 \rightarrow \$0$, $1 \rightarrow \$250\text{k}$, $2 \rightarrow \$400\text{k}$, $\ge 3 \rightarrow \$600\text{k}$).
  * Deducción de Salud ($4\%$) y Pensión ($4\%$) sobre Salario Base.
  * Deducción de ARL según tarifa de riesgo asignada.
  * Determinación del valor Neto a Pagar individual.
* **RF-05 (Consolidado de Nómina):** Sumatoria automática del total devengado, total deducido y total neto a desembolsar por la empresa.
* **RF-06 (Estados de Nómina):** Flujo de ciclo de vida: `BORRADOR` $\rightarrow$ `EN REVISIÓN` $\rightarrow$ `APROBADO` $\rightarrow$ `PAGADO`.
* **RF-07 (Generación de Desprendibles):** Vista descargable o imprimible individual para cada empleado.

---

## 5. Requerimientos No Funcionales (RNF)

* **RNF-01 (Precisión Numérica):** Los campos monetarios se manejarán con precisión decimal fija (`NUMERIC(14,2)`), prohibiendo el uso de tipos de coma flotante que induzcan errores de redondeo.
* **RNF-02 (Seguridad y Privacidad):** Autenticación mediante tokens JWT y aislamiento de datos a nivel de fila (Row Level Security en PostgreSQL/Supabase).
* **RNF-03 (Rendimiento):** El cálculo de una nómina de hasta 1,000 empleados debe completarse en menos de 5 segundos en el backend de automatización.
* **RNF-04 (Usabilidad):** Interfaz web moderna, responsiva y adaptable a dispositivos móviles y escritorio desarrollada en Tailwind CSS.
* **RNF-05 (Disponibilidad y Despliegue):** Frontend alojado en Vercel con integración continua y base de datos gestionada en la nube de Supabase.

---

## 6. Criterios de Aceptación
1. Toda liquidación realizada concuerda al $100\%$ con la matriz de casos de prueba financieros.
2. Un usuario con rol `operario` no puede acceder bajo ninguna circunstancia a los registros salariales de otros empleados ni a la configuración de tarifas.
3. El Gerente puede consultar en tiempo real el costo total de la nómina consolidada y autorizar el pago.
