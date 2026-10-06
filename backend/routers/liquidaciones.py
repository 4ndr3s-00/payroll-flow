from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Dict, Any
from backend.schemas import (
    LiquidacionCreateRequest,
    LiquidacionResumen,
    LiquidacionRechazarRequest,
    LiquidacionAnularRequest,
    DetalleEmpleadoResponse,
    ConceptoItem
)
from backend.database import get_db_cursor
from backend.security import require_roles, get_current_user
from backend.services.calculation import ejecutar_liquidacion_periodo
from backend.services.audit import record_audit

router = APIRouter(prefix="/api/liquidaciones", tags=["Liquidaciones"])

@router.post("", status_code=status.HTTP_201_CREATED)
def crear_liquidacion(
    payload: LiquidacionCreateRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    resultado = ejecutar_liquidacion_periodo(
        anio=payload.anio,
        mes=payload.mes,
        usuario_id=current_user["id"],
        ip=ip
    )
    return resultado

@router.get("", response_model=List[LiquidacionResumen])
def listar_liquidaciones(
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT l.id, l.anio, l.mes, l.estado, l.total_nomina,
                   l.ejecutada_por, u1.email as ejecutada_email, l.ejecutada_en,
                   l.resuelta_por, u2.email as resuelta_email, l.resuelta_en,
                   l.motivo_rechazo,
                   l.anulada_por, u3.email as anulada_email, l.anulada_en,
                   l.motivo_anulacion,
                   COUNT(d.id) as total_empleados
            FROM liquidaciones l
            JOIN usuarios u1 ON u1.id = l.ejecutada_por
            LEFT JOIN usuarios u2 ON u2.id = l.resuelta_por
            LEFT JOIN usuarios u3 ON u3.id = l.anulada_por
            LEFT JOIN liquidacion_detalle d ON d.liquidacion_id = l.id
            GROUP BY l.id, u1.email, u2.email, u3.email
            ORDER BY l.anio DESC, l.mes DESC, l.id DESC
        """)
        rows = cur.fetchall()
        res = []
        for r in rows:
            res.append(LiquidacionResumen(
                id=r[0],
                anio=r[1],
                mes=r[2],
                estado=r[3],
                total_nomina=r[4],
                ejecutada_por=r[5],
                ejecutada_por_nombre=r[6],
                ejecutada_en=r[7],
                resuelta_por=r[8],
                resuelta_por_nombre=r[9],
                resuelta_en=r[10],
                motivo_rechazo=r[11],
                anulada_por=r[12],
                anulada_por_nombre=r[13],
                anulada_en=r[14],
                motivo_anulacion=r[15],
                total_empleados=r[16]
            ))
        return res

@router.get("/{id}")
def obtener_liquidacion(
    id: int,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT l.id, l.anio, l.mes, l.estado, l.total_nomina,
                   l.ejecutada_por, u1.email, l.ejecutada_en,
                   l.resuelta_por, u2.email, l.resuelta_en, l.motivo_rechazo,
                   l.anulada_por, u3.email, l.anulada_en, l.motivo_anulacion,
                   l.reglas_aplicadas
            FROM liquidaciones l
            JOIN usuarios u1 ON u1.id = l.ejecutada_por
            LEFT JOIN usuarios u2 ON u2.id = l.resuelta_por
            LEFT JOIN usuarios u3 ON u3.id = l.anulada_por
            WHERE l.id = %s
        """, (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Liquidación no encontrada")

        # Resumen por perfil de esta liquidación
        cur.execute("""
            SELECT p.codigo as perfil,
                   COUNT(d.id) as empleados,
                   SUM(d.devengado) as devengado,
                   SUM(d.bonificacion) as bonificacion,
                   SUM(d.deduccion_salud + d.deduccion_pension) as deducciones_empleado,
                   SUM(d.neto) as neto_pagado,
                   SUM(d.aportes_patronales) as aportes_patronales,
                   SUM(d.prestaciones) as prestaciones,
                   SUM(d.costo_empresa) as costo_total_empresa
            FROM liquidacion_detalle d
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE d.liquidacion_id = %s
            GROUP BY p.codigo
            ORDER BY costo_total_empresa DESC
        """, (id,))
        perfiles_resumen = [
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

        return {
            "id": row[0],
            "anio": row[1],
            "mes": row[2],
            "estado": row[3],
            "total_nomina": float(row[4]),
            "ejecutada_por_email": row[6],
            "ejecutada_en": row[7],
            "resuelta_por_email": row[9],
            "resuelta_en": row[10],
            "motivo_rechazo": row[11],
            "anulada_por_email": row[13],
            "anulada_en": row[14],
            "motivo_anulacion": row[15],
            "reglas_aplicadas": row[16],
            "resumen_perfiles": perfiles_resumen
        }

@router.get("/{id}/detalles", response_model=List[DetalleEmpleadoResponse])
def obtener_detalles_empleados(
    id: int,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT d.id, d.empleado_id, e.documento, e.nombres, e.apellidos,
                   p.nombre as perfil, d.salario_base, d.num_hijos, d.horas_totales,
                   d.devengado, d.bonificacion, d.pct_salud, d.pct_pension,
                   d.deduccion_salud, d.deduccion_pension, d.neto,
                   d.aportes_patronales, d.prestaciones, d.costo_empresa
            FROM liquidacion_detalle d
            JOIN empleados e ON e.id = d.empleado_id
            JOIN perfiles p ON p.id = d.perfil_id
            WHERE d.liquidacion_id = %s
            ORDER BY e.id
        """, (id,))
        detalles = cur.fetchall()

        cur.execute("""
            SELECT c.id, c.detalle_id, c.tipo, c.concepto, c.cantidad, c.valor_unitario, c.valor_total
            FROM liquidacion_conceptos c
            JOIN liquidacion_detalle d ON d.id = c.detalle_id
            WHERE d.liquidacion_id = %s
            ORDER BY c.id
        """, (id,))
        conceptos_raw = cur.fetchall()
        conceptos_por_detalle: Dict[int, List[ConceptoItem]] = {}
        for c in conceptos_raw:
            det_id = c[1]
            conceptos_por_detalle.setdefault(det_id, []).append(
                ConceptoItem(
                    id=c[0],
                    tipo=c[2],
                    concepto=c[3],
                    cantidad=c[4],
                    valor_unitario=c[5],
                    valor_total=c[6]
                )
            )

        res = []
        for d in detalles:
            det_id = d[0]
            res.append(DetalleEmpleadoResponse(
                id=det_id,
                empleado_id=d[1],
                documento=d[2],
                nombres=d[3],
                apellidos=d[4],
                perfil=d[5],
                salario_base=d[6],
                num_hijos=d[7],
                horas_totales=d[8],
                devengado=d[9],
                bonificacion=d[10],
                pct_salud=d[11],
                pct_pension=d[12],
                deduccion_salud=d[13],
                deduccion_pension=d[14],
                neto=d[15],
                aportes_patronales=d[16],
                prestaciones=d[17],
                costo_empresa=d[18],
                conceptos=conceptos_por_detalle.get(det_id, [])
            ))
        return res

@router.patch("/{id}/aprobar")
def aprobar_liquidacion(
    id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["GERENTE"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT estado, anio, mes, total_nomina FROM liquidaciones WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Liquidación no encontrada")
        if row[0] != "LIQUIDADA":
            raise HTTPException(
                status_code=400,
                detail=f"Solo se puede aprobar una liquidación en estado 'LIQUIDADA'. Estado actual: {row[0]}"
            )

        cur.execute("""
            UPDATE liquidaciones
            SET estado = 'APROBADA',
                resuelta_por = %s,
                resuelta_en = now(),
                motivo_rechazo = NULL
            WHERE id = %s
        """, (current_user["id"], id))

        record_audit(
            usuario_id=current_user["id"],
            accion="APROBAR",
            entidad="liquidaciones",
            entidad_id=str(id),
            datos={"anio": row[1], "mes": row[2], "total_nomina": float(row[3])},
            ip=ip,
            cur=cur
        )

    return {"message": "Liquidación aprobada exitosamente por el Gerente", "id": id, "estado": "APROBADA"}

@router.patch("/{id}/rechazar")
def rechazar_liquidacion(
    id: int,
    payload: LiquidacionRechazarRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["GERENTE"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT estado, anio, mes FROM liquidaciones WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Liquidación no encontrada")
        if row[0] != "LIQUIDADA":
            raise HTTPException(
                status_code=400,
                detail=f"Solo se puede rechazar una liquidación en estado 'LIQUIDADA'. Estado actual: {row[0]}"
            )

        cur.execute("""
            UPDATE liquidaciones
            SET estado = 'RECHAZADA',
                resuelta_por = %s,
                resuelta_en = now(),
                motivo_rechazo = %s
            WHERE id = %s
        """, (current_user["id"], payload.motivo, id))

        record_audit(
            usuario_id=current_user["id"],
            accion="RECHAZAR",
            entidad="liquidaciones",
            entidad_id=str(id),
            datos={"anio": row[1], "mes": row[2], "motivo": payload.motivo},
            ip=ip,
            cur=cur
        )

    return {"message": "Liquidación rechazada por el Gerente", "id": id, "estado": "RECHAZADA"}

@router.patch("/{id}/anular")
def anular_liquidacion(
    id: int,
    payload: LiquidacionAnularRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT estado, anio, mes FROM liquidaciones WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Liquidación no encontrada")
        if row[0] == "ANULADA":
            raise HTTPException(status_code=400, detail="La liquidación ya se encuentra anulada")

        cur.execute("""
            UPDATE liquidaciones
            SET estado = 'ANULADA',
                anulada_por = %s,
                anulada_en = now(),
                motivo_anulacion = %s
            WHERE id = %s
        """, (current_user["id"], payload.motivo, id))

        record_audit(
            usuario_id=current_user["id"],
            accion="ANULAR",
            entidad="liquidaciones",
            entidad_id=str(id),
            datos={"anio": row[1], "mes": row[2], "motivo": payload.motivo},
            ip=ip,
            cur=cur
        )

    return {
        "message": "Liquidación anulada formalmente con motivo. El periodo queda disponible para reliquidar.",
        "id": id,
        "estado": "ANULADA"
    }
