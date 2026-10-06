from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from typing import List, Optional, Dict, Any
from datetime import date
from backend.schemas import RegistroHorasCreate, HorasItem
from backend.database import get_db_cursor
from backend.security import get_current_user, require_roles
from backend.services.audit import record_audit

router = APIRouter(prefix="/api/horas", tags=["Registro de Horas"])

@router.get("", response_model=List[HorasItem])
def listar_horas(
    empleado_id: Optional[int] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Si el usuario es OPERARIO, solo puede ver sus propias horas (CA-03)
    if current_user["rol"] == "OPERARIO":
        empleado_id = current_user["empleado_id"]

    query = """
        SELECT rh.id, rh.empleado_id,
               e.nombres || ' ' || e.apellidos as empleado_nombre,
               e.documento, rh.fecha,
               th.codigo as tipo_hora_codigo, th.nombre as tipo_hora_nombre,
               j.nombre as jornada_nombre, rh.horas, rh.estado,
               u_reg.email as registrado_por_nombre, rh.registrado_en,
               u_apr.email as aprobado_por_nombre, rh.aprobado_en
        FROM registro_horas rh
        JOIN empleados e ON e.id = rh.empleado_id
        JOIN tipos_hora th ON th.id = rh.tipo_hora_id
        JOIN jornadas j ON j.id = rh.jornada_id
        JOIN usuarios u_reg ON u_reg.id = rh.registrado_por
        LEFT JOIN usuarios u_apr ON u_apr.id = rh.aprobado_por
        WHERE 1=1
    """
    params = []

    if empleado_id:
        query += " AND rh.empleado_id = %s"
        params.append(empleado_id)
    if estado:
        query += " AND rh.estado = %s"
        params.append(estado)
    if fecha_desde:
        query += " AND rh.fecha >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        query += " AND rh.fecha <= %s"
        params.append(fecha_hasta)

    query += " ORDER BY rh.fecha DESC, rh.id DESC LIMIT 500"

    with get_db_cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        res = []
        for r in rows:
            res.append(HorasItem(
                id=r[0],
                empleado_id=r[1],
                empleado_nombre=r[2],
                documento=r[3],
                fecha=r[4],
                tipo_hora_codigo=r[5],
                tipo_hora_nombre=r[6],
                jornada_nombre=r[7],
                horas=r[8],
                estado=r[9],
                registrado_por_nombre=r[10],
                registrado_en=r[11],
                aprobado_por_nombre=r[12],
                aprobado_en=r[13]
            ))
        return res

@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_horas(
    payload: RegistroHorasCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    ip = request.client.host if request.client else "127.0.0.1"
    
    # Determinar qué empleado se registra
    if current_user["rol"] == "OPERARIO":
        emp_id = current_user["empleado_id"]
    else:
        emp_id = payload.empleado_id or current_user["empleado_id"]

    with get_db_cursor(commit=True) as cur:
        # Verificar si ya existe registro de ese tipo para esa fecha y empleado
        cur.execute("""
            SELECT id FROM registro_horas
            WHERE empleado_id = %s AND fecha = %s AND tipo_hora_id = %s
        """, (emp_id, payload.fecha, payload.tipo_hora_id))
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="Ya existe un registro para este empleado, fecha y tipo de hora."
            )

        cur.execute("""
            INSERT INTO registro_horas (
                empleado_id, fecha, tipo_hora_id, jornada_id, horas, estado, registrado_por
            )
            VALUES (%s, %s, %s, %s, %s, 'PENDIENTE', %s)
            RETURNING id
        """, (emp_id, payload.fecha, payload.tipo_hora_id, payload.jornada_id, payload.horas, current_user["id"]))
        nuevo_id = cur.fetchone()[0]

        record_audit(
            usuario_id=current_user["id"],
            accion="REGISTRAR_HORAS",
            entidad="registro_horas",
            entidad_id=str(nuevo_id),
            datos={"empleado_id": emp_id, "fecha": str(payload.fecha), "horas": float(payload.horas)},
            ip=ip,
            cur=cur
        )

    return {"message": "Horas registradas exitosamente. Quedan en estado PENDIENTE para revisión de RRHH.", "id": nuevo_id}

@router.patch("/{id}/aprobar")
def aprobar_hora(
    id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE registro_horas
            SET estado = 'APROBADA',
                aprobado_por = %s,
                aprobado_en = now()
            WHERE id = %s
            RETURNING id
        """, (current_user["id"], id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Registro de hora no encontrado")

        record_audit(
            usuario_id=current_user["id"],
            accion="APROBAR_HORAS",
            entidad="registro_horas",
            entidad_id=str(id),
            ip=ip,
            cur=cur
        )

    return {"message": "Hora aprobada exitosamente", "id": id, "estado": "APROBADA"}

@router.patch("/{id}/rechazar")
def rechazar_hora(
    id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE registro_horas
            SET estado = 'RECHAZADA',
                aprobado_por = %s,
                aprobado_en = now()
            WHERE id = %s
            RETURNING id
        """, (current_user["id"], id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Registro de hora no encontrado")

        record_audit(
            usuario_id=current_user["id"],
            accion="RECHAZAR_HORAS",
            entidad="registro_horas",
            entidad_id=str(id),
            ip=ip,
            cur=cur
        )

    return {"message": "Hora rechazada exitosamente", "id": id, "estado": "RECHAZADA"}

@router.post("/aprobar-batch")
def aprobar_horas_batch(
    anio: int,
    mes: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE registro_horas
            SET estado = 'APROBADA',
                aprobado_por = %s,
                aprobado_en = now()
            WHERE estado = 'PENDIENTE'
              AND EXTRACT(YEAR FROM fecha) = %s
              AND EXTRACT(MONTH FROM fecha) = %s
            RETURNING id
        """, (current_user["id"], anio, mes))
        aprobadas = cur.fetchall()

        record_audit(
            usuario_id=current_user["id"],
            accion="APROBAR_HORAS_BATCH",
            entidad="registro_horas",
            datos={"anio": anio, "mes": mes, "cantidad": len(aprobadas)},
            ip=ip,
            cur=cur
        )

    return {"message": f"Se aprobaron {len(aprobadas)} registros de horas pendientes para {anio}-{mes:02d}."}
