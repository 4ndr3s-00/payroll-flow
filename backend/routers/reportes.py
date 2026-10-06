from fastapi import APIRouter, HTTPException, status, Depends, Response
from typing import List, Dict, Any, Optional
import io
import csv
from backend.database import get_db_cursor
from backend.security import get_current_user, require_roles
from backend.services.pdf_generator import generar_volante_pdf, generar_consolidado_pdf

router = APIRouter(prefix="/api/reportes", tags=["Reportes y Volantes"])

@router.get("/consolidado")
def reporte_consolidado(
    anio: int = 2026,
    mes: int = 9,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        # Consulta base de v_costo_nomina_aprobada
        cur.execute("""
            SELECT perfil, empleados, devengado, bonificaciones,
                   deducciones_empleado, neto_pagado_empleados,
                   aportes_patronales, prestaciones, costo_total_empresa
            FROM v_costo_nomina_aprobada
            WHERE anio = %s AND mes = %s
            ORDER BY costo_total_empresa DESC
        """, (anio, mes))
        rows = cur.fetchall()

        # Si no hay aprobada, buscar en cualquier liquidación no anulada para previsualización
        if not rows:
            cur.execute("""
                SELECT p.codigo as perfil,
                       COUNT(d.id) as empleados,
                       SUM(d.devengado) as devengado,
                       SUM(d.bonificacion) as bonificaciones,
                       SUM(d.deduccion_salud + d.deduccion_pension) as deducciones_empleado,
                       SUM(d.neto) as neto_pagado_empleados,
                       SUM(d.aportes_patronales) as aportes_patronales,
                       SUM(d.prestaciones) as prestaciones,
                       SUM(d.costo_empresa) as costo_total_empresa
                FROM liquidaciones l
                JOIN liquidacion_detalle d ON d.liquidacion_id = l.id
                JOIN perfiles p ON p.id = d.perfil_id
                WHERE l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
                GROUP BY p.codigo
                ORDER BY costo_total_empresa DESC
            """, (anio, mes))
            rows = cur.fetchall()
            es_preliminar = True
        else:
            es_preliminar = False

        res = [
            {
                "perfil": r[0],
                "empleados": r[1],
                "devengado": float(r[2]),
                "bonificaciones": float(r[3]),
                "deducciones_empleado": float(r[4]),
                "neto_pagado_empleados": float(r[5]),
                "aportes_patronales": float(r[6]),
                "prestaciones": float(r[7]),
                "costo_total_empresa": float(r[8]),
            }
            for r in rows
        ]

        total_empleados = sum((x["empleados"] for x in res), 0)
        total_devengado = sum((x["devengado"] for x in res), 0.0)
        total_bonificaciones = sum((x["bonificaciones"] for x in res), 0.0)
        total_deducciones = sum((x["deducciones_empleado"] for x in res), 0.0)
        total_neto = sum((x["neto_pagado_empleados"] for x in res), 0.0)
        total_patronal = sum((x["aportes_patronales"] + x["prestaciones"] for x in res), 0.0)
        total_costo_empresa = sum((x["costo_total_empresa"] for x in res), 0.0)

        # Sobrecosto patronal %
        sobrecosto_pct = ((total_costo_empresa - total_neto) / total_neto * 100) if total_neto > 0 else 0.0

        # KPIs adicionales según docs/8-analytics-and-kpis.md (Promedio de Horas y Distribución Hijos)
        cur.execute("""
            SELECT COALESCE(SUM(d.horas_totales), 0),
                   COALESCE(AVG(d.horas_totales), 0)
            FROM liquidaciones l
            JOIN liquidacion_detalle d ON d.liquidacion_id = l.id
            WHERE l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
        """, (anio, mes))
        h_row = cur.fetchone()
        total_horas = float(h_row[0]) if h_row else 0.0
        promedio_horas = round(float(h_row[1]), 2) if h_row else 0.0

        cur.execute("""
            SELECT 
                CASE 
                    WHEN d.num_hijos = 0 THEN '0 hijos'
                    WHEN d.num_hijos = 1 THEN '1 hijo'
                    WHEN d.num_hijos = 2 THEN '2 hijos'
                    ELSE '3+ hijos'
                END as tramo,
                COUNT(d.id) as empleados,
                COALESCE(SUM(d.bonificacion), 0) as total_subsidio
            FROM liquidaciones l
            JOIN liquidacion_detalle d ON d.liquidacion_id = l.id
            WHERE l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
            GROUP BY 
                CASE 
                    WHEN d.num_hijos = 0 THEN '0 hijos'
                    WHEN d.num_hijos = 1 THEN '1 hijo'
                    WHEN d.num_hijos = 2 THEN '2 hijos'
                    ELSE '3+ hijos'
                END
            ORDER BY tramo
        """, (anio, mes))
        distribucion_hijos = [
            {
                "tramo": dh[0],
                "empleados": int(dh[1]),
                "total_subsidio": float(dh[2])
            }
            for dh in cur.fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "es_preliminar": es_preliminar,
            "perfiles": res,
            "distribucion_hijos": distribucion_hijos,
            "totales": {
                "empleados": total_empleados,
                "total_horas": total_horas,
                "promedio_horas": promedio_horas,
                "devengado": total_devengado,
                "bonificaciones": total_bonificaciones,
                "deducciones_empleado": total_deducciones,
                "neto_pagado": total_neto,
                "costo_patronal": total_patronal,
                "costo_total_empresa": total_costo_empresa,
                "sobrecosto_patronal_pct": round(sobrecosto_pct, 2)
            }
        }


@router.get("/export/csv")
def exportar_csv(
    anio: int = 2026,
    mes: int = 9,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT e.documento, e.nombres || ' ' || e.apellidos as empleado,
                   p.nombre as perfil, d.horas_totales, d.devengado,
                   d.bonificacion, d.deduccion_salud, d.deduccion_pension,
                   d.neto, d.aportes_patronales, d.prestaciones, d.costo_empresa
            FROM liquidaciones l
            JOIN liquidacion_detalle d ON d.liquidacion_id = l.id
            JOIN empleados e ON e.id = d.empleado_id
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
            ORDER BY e.id
        """, (anio, mes))
        rows = cur.fetchall()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            "DOCUMENTO", "EMPLEADO", "PERFIL", "HORAS TOTALES",
            "DEVENGADO", "BONIFICACION", "SALUD 4%", "PENSION 4%",
            "NETO PAGADO", "APORTES PATRONALES", "PRESTACIONES", "COSTO TOTAL EMPRESA"
        ])
        for r in rows:
            writer.writerow([
                r[0], r[1], r[2], f"{float(r[3]):.2f}",
                f"{float(r[4]):.2f}", f"{float(r[5]):.2f}", f"{float(r[6]):.2f}", f"{float(r[7]):.2f}",
                f"{float(r[8]):.2f}", f"{float(r[9]):.2f}", f"{float(r[10]):.2f}", f"{float(r[11]):.2f}"
            ])

        csv_content = output.getvalue().encode('utf-8-sig')
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=nomina_{anio}_{mes:02d}.csv"}
        )

@router.get("/export/pdf")
def exportar_pdf_consolidado(
    anio: int = 2026,
    mes: int = 9,
    inline: bool = False,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT l.id, l.anio, l.mes, l.estado
            FROM liquidaciones l
            WHERE l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
            ORDER BY l.id DESC LIMIT 1
        """, (anio, mes))
        liq_row = cur.fetchone()
        if not liq_row:
            raise HTTPException(status_code=404, detail="No se encontró liquidación para el periodo solicitado")

        cur.execute("""
            SELECT p.codigo as perfil,
                   COUNT(d.id) as empleados,
                   SUM(d.devengado) as devengado,
                   SUM(d.bonificacion) as bonificaciones,
                   SUM(d.deduccion_salud + d.deduccion_pension) as deducciones_empleado,
                   SUM(d.neto) as neto_pagado_empleados,
                   SUM(d.aportes_patronales) as aportes_patronales,
                   SUM(d.prestaciones) as prestaciones,
                   SUM(d.costo_empresa) as costo_total_empresa
            FROM liquidacion_detalle d
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE d.liquidacion_id = %s
            GROUP BY p.codigo
            ORDER BY costo_total_empresa DESC
        """, (liq_row[0],))
        perfiles = [
            {
                "perfil": pr[0],
                "empleados": pr[1],
                "devengado": float(pr[2]),
                "bonificaciones": float(pr[3]),
                "deducciones_empleado": float(pr[4]),
                "neto_pagado_empleados": float(pr[5]),
                "aportes_patronales": float(pr[6]),
                "prestaciones": float(pr[7]),
                "costo_total_empresa": float(pr[8])
            }
            for pr in cur.fetchall()
        ]

        pdf_bytes = generar_consolidado_pdf(
            cabecera={"anio": liq_row[1], "mes": liq_row[2], "estado": liq_row[3]},
            perfiles=perfiles
        )

        disposition = "inline" if inline else "attachment"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"{disposition}; filename=reporte_nomina_{anio}_{mes:02d}.pdf"}
        )

# Volante individual del operario (filtrado estrictamente por su propio empleado_id del token)
@router.get("/me/volantes/{anio}/{mes}")
def obtener_mi_volante(
    anio: int,
    mes: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    emp_id = current_user["empleado_id"]

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT d.id, d.liquidacion_id, l.anio, l.mes, l.estado,
                   e.documento, e.nombres, e.apellidos, p.nombre as perfil,
                   d.salario_base, d.num_hijos, d.horas_totales,
                   d.devengado, d.bonificacion, d.pct_salud, d.pct_pension,
                   d.deduccion_salud, d.deduccion_pension, d.neto
            FROM liquidacion_detalle d
            JOIN liquidaciones l ON l.id = d.liquidacion_id
            JOIN empleados e ON e.id = d.empleado_id
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE d.empleado_id = %s AND l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
            ORDER BY l.id DESC LIMIT 1
        """, (emp_id, anio, mes))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No se encontró volante para este periodo")

        detalle_id = row[0]
        cur.execute("""
            SELECT c.id, c.tipo, c.concepto, c.cantidad, c.valor_unitario, c.valor_total
            FROM liquidacion_conceptos c
            WHERE c.detalle_id = %s
              AND c.tipo IN ('DEVENGADO', 'BONIFICACION', 'DEDUCCION')
            ORDER BY c.id
        """, (detalle_id,))
        conceptos = [
            {
                "id": c[0],
                "tipo": c[1],
                "concepto": c[2],
                "cantidad": float(c[3]),
                "valor_unitario": float(c[4]),
                "valor_total": float(c[5])
            }
            for c in cur.fetchall()
        ]

        return {
            "id": row[0],
            "liquidacion_id": row[1],
            "anio": row[2],
            "mes": row[3],
            "estado": row[4],
            "documento": row[5],
            "nombres": row[6],
            "apellidos": row[7],
            "perfil": row[8],
            "salario_base": float(row[9]),
            "num_hijos": row[10],
            "horas_totales": float(row[11]),
            "devengado": float(row[12]),
            "bonificacion": float(row[13]),
            "pct_salud": float(row[14]),
            "pct_pension": float(row[15]),
            "deduccion_salud": float(row[16]),
            "deduccion_pension": float(row[17]),
            "neto": float(row[18]),
            "conceptos": conceptos
        }

@router.get("/me/volantes/{anio}/{mes}/pdf")
def descargar_mi_volante_pdf(
    anio: int,
    mes: int,
    inline: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    emp_id = current_user["empleado_id"]

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT d.id, d.liquidacion_id, l.anio, l.mes, l.estado,
                   e.documento, e.nombres, e.apellidos, p.nombre as perfil,
                   d.salario_base, d.num_hijos, d.horas_totales,
                   d.devengado, d.bonificacion, d.pct_salud, d.pct_pension,
                   d.deduccion_salud, d.deduccion_pension, d.neto
            FROM liquidacion_detalle d
            JOIN liquidaciones l ON l.id = d.liquidacion_id
            JOIN empleados e ON e.id = d.empleado_id
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE d.empleado_id = %s AND l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
            ORDER BY l.id DESC LIMIT 1
        """, (emp_id, anio, mes))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No se encontró volante para este periodo")

        detalle_id = row[0]
        cur.execute("""
            SELECT c.tipo, c.concepto, c.cantidad, c.valor_unitario, c.valor_total
            FROM liquidacion_conceptos c
            WHERE c.detalle_id = %s
            ORDER BY c.id
        """, (detalle_id,))
        conceptos = [
            {
                "tipo": c[0],
                "concepto": c[1],
                "cantidad": c[2],
                "valor_unitario": c[3],
                "valor_total": c[4]
            }
            for c in cur.fetchall()
        ]

        detalle_dict = {
            "anio": row[2],
            "mes": row[3],
            "documento": row[5],
            "nombres": row[6],
            "apellidos": row[7],
            "perfil": row[8],
            "salario_base": row[9],
            "num_hijos": row[10],
            "horas_totales": row[11],
            "neto": row[18]
        }

        pdf_bytes = generar_volante_pdf(detalle_dict, conceptos)
        disposition = "inline" if inline else "attachment"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"{disposition}; filename=volante_{row[5]}_{anio}_{mes:02d}.pdf"}
        )

# Descarga de volante por empleado (exclusivo Admin y Gerente)
@router.get("/volantes/{empleado_id}/{anio}/{mes}/pdf")
def descargar_volante_empleado_pdf(
    empleado_id: int,
    anio: int,
    mes: int,
    inline: bool = False,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT d.id, d.liquidacion_id, l.anio, l.mes, l.estado,
                   e.documento, e.nombres, e.apellidos, p.nombre as perfil,
                   d.salario_base, d.num_hijos, d.horas_totales,
                   d.devengado, d.bonificacion, d.pct_salud, d.pct_pension,
                   d.deduccion_salud, d.deduccion_pension, d.neto
            FROM liquidacion_detalle d
            JOIN liquidaciones l ON l.id = d.liquidacion_id
            JOIN empleados e ON e.id = d.empleado_id
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE d.empleado_id = %s AND l.anio = %s AND l.mes = %s AND l.estado <> 'ANULADA'
            ORDER BY l.id DESC LIMIT 1
        """, (empleado_id, anio, mes))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No se encontró volante para el empleado {empleado_id} en el periodo solicitado")

        detalle_id = row[0]
        cur.execute("""
            SELECT c.tipo, c.concepto, c.cantidad, c.valor_unitario, c.valor_total
            FROM liquidacion_conceptos c
            WHERE c.detalle_id = %s
            ORDER BY c.id
        """, (detalle_id,))
        conceptos = [
            {
                "tipo": c[0],
                "concepto": c[1],
                "cantidad": c[2],
                "valor_unitario": c[3],
                "valor_total": c[4]
            }
            for c in cur.fetchall()
        ]

        detalle_dict = {
            "anio": row[2],
            "mes": row[3],
            "documento": row[5],
            "nombres": row[6],
            "apellidos": row[7],
            "perfil": row[8],
            "salario_base": row[9],
            "num_hijos": row[10],
            "horas_totales": row[11],
            "neto": row[18]
        }

        pdf_bytes = generar_volante_pdf(detalle_dict, conceptos)
        disposition = "inline" if inline else "attachment"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"{disposition}; filename=volante_{row[5]}_{anio}_{mes:02d}.pdf"}
        )

@router.get("/auditoria")
def obtener_auditoria(
    limit: int = 200,
    current_user: Dict[str, Any] = Depends(require_roles(["GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT a.id, a.usuario_id, u.email as usuario_email,
                   a.accion, a.entidad, a.entidad_id, a.datos,
                   host(a.ip) as ip, a.creado_en
            FROM audit_log a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            ORDER BY a.creado_en DESC, a.id DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "usuario_id": r[1],
                "usuario_email": r[2],
                "accion": r[3],
                "entidad": r[4],
                "entidad_id": r[5],
                "datos": r[6],
                "ip": r[7],
                "creado_en": str(r[8])
            }
            for r in rows
        ]
