from decimal import Decimal, ROUND_HALF_UP
import calendar
from datetime import date
import json
from typing import Dict, Any, List
from fastapi import HTTPException, status
from backend.database import get_db_connection
from backend.services.audit import record_audit

def quantize_money(val) -> Decimal:
    if val is None:
        return Decimal('0.00')
    return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def ejecutar_liquidacion_periodo(
    anio: int,
    mes: int,
    usuario_id: int,
    ip: str = "127.0.0.1"
) -> Dict[str, Any]:
    _, last_day = calendar.monthrange(anio, mes)
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, last_day)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Verificar si ya existe una liquidación activa para el periodo (RN-07)
            cur.execute("""
                SELECT id, estado FROM liquidaciones
                WHERE anio = %s AND mes = %s AND estado <> 'ANULADA'
            """, (anio, mes))
            existente = cur.fetchone()
            if existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe una liquidación activa para el periodo {anio}-{mes:02d} (ID: {existente[0]}, Estado: {existente[1]}). Para recalcular debe anularse primero con motivo."
                )

            # 2. Obtener reglas vigentes a la fecha de corte
            cur.execute("SELECT fn_pct_deduccion('SALUD', %s)", (fecha_fin,))
            pct_salud = quantize_money(cur.fetchone()[0])

            cur.execute("SELECT fn_pct_deduccion('PENSION', %s)", (fecha_fin,))
            pct_pension = quantize_money(cur.fetchone()[0])

            cur.execute("""
                SELECT id, min_hijos, max_hijos, valor
                FROM config_bonificacion_hijos
                WHERE vigente_desde <= %s AND (vigente_hasta IS NULL OR vigente_hasta >= %s)
            """, (fecha_fin, fecha_fin))
            reglas_bonif = [
                {"min_hijos": r[1], "max_hijos": r[2], "valor": float(r[3])}
                for r in cur.fetchall()
            ]

            cur.execute("""
                SELECT id, codigo, nombre, categoria, porcentaje, aplica_sobre
                FROM config_aportes_patronales
                WHERE vigente_desde <= %s AND (vigente_hasta IS NULL OR vigente_hasta >= %s)
                ORDER BY categoria, id
            """, (fecha_fin, fecha_fin))
            reglas_patronales = cur.fetchall()

            reglas_snapshot = {
                "fecha_corte": str(fecha_fin),
                "pct_salud": float(pct_salud),
                "pct_pension": float(pct_pension),
                "bonificaciones": reglas_bonif,
                "aportes_patronales": [
                    {
                        "codigo": r[1],
                        "nombre": r[2],
                        "categoria": r[3],
                        "porcentaje": float(r[4]),
                        "aplica_sobre": r[5]
                    }
                    for r in reglas_patronales
                ]
            }

            # 3. Crear cabecera preliminar en liquidaciones
            cur.execute("""
                INSERT INTO liquidaciones (
                    anio, mes, estado, total_nomina, reglas_aplicadas, ejecutada_por, ejecutada_en
                )
                VALUES (%s, %s, 'LIQUIDADA', 0, %s, %s, now())
                RETURNING id
            """, (anio, mes, json.dumps(reglas_snapshot), usuario_id))
            liquidacion_id = cur.fetchone()[0]

            # 4. Obtener todos los empleados activos
            cur.execute("""
                SELECT e.id, e.documento, e.nombres, e.apellidos, e.salario_base,
                       e.num_hijos, e.perfil_id, p.codigo as perfil_codigo
                FROM empleados e
                JOIN perfiles p ON p.id = e.perfil_id
                WHERE e.activo = TRUE
                ORDER BY e.id
            """)
            empleados = cur.fetchall()

            if not empleados:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No hay empleados activos registrados para liquidar."
                )

            # 5. Obtener desglose de horas valorizadas por empleado y tipo de hora en el periodo
            cur.execute("""
                SELECT rh.empleado_id,
                       th.id as tipo_hora_id,
                       th.codigo as tipo_hora_codigo,
                       th.nombre as tipo_hora_nombre,
                       th.multiplicador,
                       SUM(rh.horas) as total_horas,
                       t.tarifa as tarifa_base,
                       SUM(ROUND(rh.horas * t.tarifa * th.multiplicador, 2)) as valor_total
                FROM registro_horas rh
                JOIN tipos_hora th ON th.id = rh.tipo_hora_id
                CROSS JOIN LATERAL (SELECT fn_tarifa_vigente(rh.empleado_id, rh.fecha) as tarifa) t
                WHERE rh.estado = 'APROBADA'
                  AND rh.fecha BETWEEN %s AND %s
                GROUP BY rh.empleado_id, th.id, th.codigo, th.nombre, th.multiplicador, t.tarifa
                ORDER BY rh.empleado_id, th.id
            """, (fecha_inicio, fecha_fin))
            horas_por_emp: Dict[int, List[Dict[str, Any]]] = {}
            for row in cur.fetchall():
                emp_id = row[0]
                horas_por_emp.setdefault(emp_id, []).append({
                    "tipo_hora_id": row[1],
                    "tipo_hora_codigo": row[2],
                    "tipo_hora_nombre": row[3],
                    "multiplicador": quantize_money(row[4]),
                    "horas": quantize_money(row[5]),
                    "tarifa_base": quantize_money(row[6]),
                    "valor": quantize_money(row[7]),
                })

            total_nomina_periodo = Decimal('0.00')
            total_costo_empresa_periodo = Decimal('0.00')
            total_devengado_periodo = Decimal('0.00')
            total_bonificaciones_periodo = Decimal('0.00')
            total_deducciones_periodo = Decimal('0.00')
            detalles_insertados = 0

            # 6. Procesar empleado por empleado
            for emp in empleados:
                emp_id, doc, nom, ape, sal_base, num_hijos, perfil_id, perf_cod = emp
                sal_base = quantize_money(sal_base)

                emp_horas = horas_por_emp.get(emp_id, [])
                horas_totales = sum((h["horas"] for h in emp_horas), Decimal('0.00'))
                devengado = sum((h["valor"] for h in emp_horas), Decimal('0.00'))

                # Bonificación por hijos
                cur.execute("SELECT fn_bonificacion_hijos(%s, %s)", (num_hijos, fecha_fin))
                bonificacion = quantize_money(cur.fetchone()[0])

                # Deducciones legales del empleado (Salud y Pensión sobre devengado)
                deduccion_salud = quantize_money(devengado * pct_salud / Decimal('100.00'))
                deduccion_pension = quantize_money(devengado * pct_pension / Decimal('100.00'))

                # Neto individual (RN-05)
                neto = devengado + bonificacion - deduccion_salud - deduccion_pension

                # Aportes patronales y prestaciones
                aportes_patronales_total = Decimal('0.00')
                prestaciones_total = Decimal('0.00')
                patronales_conceptos = []

                for pat in reglas_patronales:
                    pat_id, pat_cod, pat_nom, pat_cat, pat_pct, pat_aplica = pat
                    pat_pct = quantize_money(pat_pct)
                    base_calc = devengado if pat_aplica == 'DEVENGADO' else (devengado + bonificacion)
                    valor_calc = quantize_money(base_calc * pat_pct / Decimal('100.00'))
                    
                    if pat_cat == 'APORTE':
                        aportes_patronales_total += valor_calc
                    else:
                        prestaciones_total += valor_calc

                    patronales_conceptos.append({
                        "tipo": "APORTE_PATRONAL" if pat_cat == 'APORTE' else "PRESTACION",
                        "concepto": f"{pat_nom} ({pat_pct}%)",
                        "cantidad": Decimal('1.00'),
                        "valor_unitario": valor_calc,
                        "valor_total": valor_calc
                    })

                # Costo total para la empresa (ck_costo_empresa)
                costo_empresa = devengado + bonificacion + aportes_patronales_total + prestaciones_total

                # Insertar en liquidacion_detalle
                cur.execute("""
                    INSERT INTO liquidacion_detalle (
                        liquidacion_id, empleado_id, perfil_id, salario_base, num_hijos,
                        horas_totales, devengado, bonificacion, pct_salud, pct_pension,
                        deduccion_salud, deduccion_pension, neto, aportes_patronales,
                        prestaciones, costo_empresa
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    liquidacion_id, emp_id, perfil_id, sal_base, num_hijos,
                    horas_totales, devengado, bonificacion, pct_salud, pct_pension,
                    deduccion_salud, deduccion_pension, neto, aportes_patronales_total,
                    prestaciones_total, costo_empresa
                ))
                detalle_id = cur.fetchone()[0]

                # Insertar en liquidacion_conceptos (RF-12)
                # 1. Devengados por horas
                for h in emp_horas:
                    unitario = quantize_money(h["tarifa_base"] * h["multiplicador"])
                    cur.execute("""
                        INSERT INTO liquidacion_conceptos (
                            detalle_id, tipo, concepto, tipo_hora_id, cantidad, valor_unitario, valor_total
                        )
                        VALUES (%s, 'DEVENGADO', %s, %s, %s, %s, %s)
                    """, (
                        detalle_id,
                        f"Horas {h['tipo_hora_nombre']} (x{h['multiplicador']})",
                        h["tipo_hora_id"],
                        h["horas"],
                        unitario,
                        h["valor"]
                    ))

                # 2. Bonificación si aplica
                if bonificacion > 0:
                    cur.execute("""
                        INSERT INTO liquidacion_conceptos (
                            detalle_id, tipo, concepto, tipo_hora_id, cantidad, valor_unitario, valor_total
                        )
                        VALUES (%s, 'BONIFICACION', %s, NULL, 1.00, %s, %s)
                    """, (
                        detalle_id,
                        f"Bonificación por hijos ({num_hijos} a cargo)",
                        bonificacion,
                        bonificacion
                    ))

                # 3. Deducciones del empleado
                cur.execute("""
                    INSERT INTO liquidacion_conceptos (
                        detalle_id, tipo, concepto, tipo_hora_id, cantidad, valor_unitario, valor_total
                    )
                    VALUES (%s, 'DEDUCCION', %s, NULL, 1.00, %s, %s)
                """, (
                    detalle_id,
                    f"Aporte a Salud ({pct_salud}%)",
                    deduccion_salud,
                    deduccion_salud
                ))
                cur.execute("""
                    INSERT INTO liquidacion_conceptos (
                        detalle_id, tipo, concepto, tipo_hora_id, cantidad, valor_unitario, valor_total
                    )
                    VALUES (%s, 'DEDUCCION', %s, NULL, 1.00, %s, %s)
                """, (
                    detalle_id,
                    f"Aporte a Pensión ({pct_pension}%)",
                    deduccion_pension,
                    deduccion_pension
                ))

                # 4. Aportes patronales y prestaciones
                for p_conc in patronales_conceptos:
                    cur.execute("""
                        INSERT INTO liquidacion_conceptos (
                            detalle_id, tipo, concepto, tipo_hora_id, cantidad, valor_unitario, valor_total
                        )
                        VALUES (%s, %s, %s, NULL, %s, %s, %s)
                    """, (
                        detalle_id,
                        p_conc["tipo"],
                        p_conc["concepto"],
                        p_conc["cantidad"],
                        p_conc["valor_unitario"],
                        p_conc["valor_total"]
                    ))

                total_nomina_periodo += neto
                total_costo_empresa_periodo += costo_empresa
                total_devengado_periodo += devengado
                total_bonificaciones_periodo += bonificacion
                total_deducciones_periodo += (deduccion_salud + deduccion_pension)
                detalles_insertados += 1

            # 7. Actualizar total_nomina en cabecera
            cur.execute("""
                UPDATE liquidaciones
                SET total_nomina = %s
                WHERE id = %s
            """, (total_nomina_periodo, liquidacion_id))

            # 8. Registrar en audit_log
            record_audit(
                usuario_id=usuario_id,
                accion="LIQUIDAR",
                entidad="liquidaciones",
                entidad_id=str(liquidacion_id),
                datos={
                    "anio": anio,
                    "mes": mes,
                    "total_empleados": detalles_insertados,
                    "total_nomina": float(total_nomina_periodo),
                    "total_costo_empresa": float(total_costo_empresa_periodo)
                },
                ip=ip,
                cur=cur
            )

        # Confirmar toda la transacción junta
        conn.commit()

    return {
        "liquidacion_id": liquidacion_id,
        "anio": anio,
        "mes": mes,
        "estado": "LIQUIDADA",
        "total_empleados": detalles_insertados,
        "total_devengado": float(total_devengado_periodo),
        "total_bonificaciones": float(total_bonificaciones_periodo),
        "total_deducciones": float(total_deducciones_periodo),
        "total_nomina": float(total_nomina_periodo),
        "total_costo_empresa": float(total_costo_empresa_periodo)
    }

def simular_calculo_individual(
    hours_worked: Decimal | float,
    hourly_rate: Decimal | float,
    num_children: int,
    arl_rate: Decimal | float = Decimal("0.00522")
) -> Dict[str, Any]:
    """
    Realiza la simulación individual rápida de liquidación según la especificación
    de reglas de negocio (docs/4-business-rules-financial.md y docs/6-api-contracts.md).
    """
    hours = Decimal(str(hours_worked))
    rate = Decimal(str(hourly_rate))
    children = int(num_children)
    arl_r = Decimal(str(arl_rate))

    # 1. Salario Base = Horas * Tarifa
    base_salary = quantize_money(hours * rate)

    # 2. Escala de Subsidio por Hijos
    if children <= 0:
        child_subsidy = Decimal("0.00")
    elif children == 1:
        child_subsidy = Decimal("250000.00")
    elif children == 2:
        child_subsidy = Decimal("400000.00")
    else:
        child_subsidy = Decimal("600000.00")

    # 3. Deducciones
    health_4pct = quantize_money(base_salary * Decimal("0.04"))
    pension_4pct = quantize_money(base_salary * Decimal("0.04"))
    arl = quantize_money(base_salary * arl_r)
    total_deductions = quantize_money(health_4pct + pension_4pct + arl)

    # 4. Totales
    total_devengado = quantize_money(base_salary + child_subsidy)
    net_pay = quantize_money(total_devengado - total_deductions)

    return {
        "base_salary": base_salary,
        "child_subsidy": child_subsidy,
        "deductions": {
            "health_4pct": health_4pct,
            "pension_4pct": pension_4pct,
            "arl": arl,
            "total_deductions": total_deductions
        },
        "total_devengado": total_devengado,
        "net_pay": net_pay
    }

