from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Dict, Any
from backend.schemas import (
    PerfilItem,
    TipoHoraItem,
    TipoHoraUpdate,
    TarifaItem,
    TarifaCreate
)
from backend.database import get_db_cursor
from backend.security import require_roles, get_current_user
from backend.services.audit import record_audit

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos y Reglas"])

@router.get("/perfiles", response_model=List[PerfilItem])
def listar_perfiles(current_user: Dict[str, Any] = Depends(get_current_user)):
    with get_db_cursor() as cur:
        cur.execute("SELECT id, codigo, nombre, activo FROM perfiles ORDER BY id")
        rows = cur.fetchall()
        return [PerfilItem(id=r[0], codigo=r[1], nombre=r[2], activo=r[3]) for r in rows]

@router.get("/tipos-hora", response_model=List[TipoHoraItem])
def listar_tipos_hora(current_user: Dict[str, Any] = Depends(get_current_user)):
    with get_db_cursor() as cur:
        cur.execute("SELECT id, codigo, nombre, multiplicador, activo FROM tipos_hora ORDER BY id")
        rows = cur.fetchall()
        return [TipoHoraItem(id=r[0], codigo=r[1], nombre=r[2], multiplicador=r[3], activo=r[4]) for r in rows]

@router.put("/tipos-hora/{id}")
def actualizar_tipo_hora(
    id: int,
    payload: TipoHoraUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        updates = []
        params = []
        if payload.nombre is not None:
            updates.append("nombre = %s")
            params.append(payload.nombre)
        if payload.multiplicador is not None:
            updates.append("multiplicador = %s")
            params.append(payload.multiplicador)
        if payload.activo is not None:
            updates.append("activo = %s")
            params.append(payload.activo)

        if updates:
            params.append(id)
            cur.execute(f"UPDATE tipos_hora SET {', '.join(updates)} WHERE id = %s RETURNING id", tuple(params))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tipo de hora no encontrado")

            record_audit(
                usuario_id=current_user["id"],
                accion="EDITAR_TIPO_HORA",
                entidad="tipos_hora",
                entidad_id=str(id),
                datos=payload.model_dump(exclude_unset=True),
                ip=ip,
                cur=cur
            )

    return {"message": "Tipo de hora actualizado exitosamente", "id": id}

@router.get("/jornadas")
def listar_jornadas(current_user: Dict[str, Any] = Depends(get_current_user)):
    with get_db_cursor() as cur:
        cur.execute("SELECT id, codigo, nombre, hora_inicio, hora_fin FROM jornadas ORDER BY id")
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "codigo": r[1],
                "nombre": r[2],
                "hora_inicio": str(r[3]),
                "hora_fin": str(r[4])
            }
            for r in rows
        ]

@router.get("/tarifas", response_model=List[TarifaItem])
def listar_tarifas(current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT t.id, t.alcance, t.perfil_id, p.nombre as perfil_nombre,
                   t.empleado_id, e.nombres || ' ' || e.apellidos as empleado_nombre,
                   t.tarifa_base, t.vigente_desde, t.vigente_hasta
            FROM tarifas t
            LEFT JOIN perfiles p ON p.id = t.perfil_id
            LEFT JOIN empleados e ON e.id = t.empleado_id
            ORDER BY t.vigente_desde DESC, t.id DESC
        """)
        rows = cur.fetchall()
        return [
            TarifaItem(
                id=r[0],
                alcance=r[1],
                perfil_id=r[2],
                perfil_nombre=r[3],
                empleado_id=r[4],
                empleado_nombre=r[5],
                tarifa_base=r[6],
                vigente_desde=r[7],
                vigente_hasta=r[8]
            )
            for r in rows
        ]

@router.post("/tarifas", status_code=status.HTTP_201_CREATED)
def crear_tarifa(
    payload: TarifaCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO tarifas (alcance, perfil_id, empleado_id, tarifa_base, vigente_desde, vigente_hasta)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (payload.alcance, payload.perfil_id, payload.empleado_id, payload.tarifa_base, payload.vigente_desde, payload.vigente_hasta))
        nuevo_id = cur.fetchone()[0]

        record_audit(
            usuario_id=current_user["id"],
            accion="CREAR_TARIFA",
            entidad="tarifas",
            entidad_id=str(nuevo_id),
            datos=payload.model_dump(mode="json"),
            ip=ip,
            cur=cur
        )

    return {"message": "Tarifa configurada exitosamente", "id": nuevo_id}

@router.get("/config-deducciones")
def listar_deducciones(current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))):
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT id, concepto, porcentaje, vigente_desde, vigente_hasta, creado_en
            FROM config_deducciones
            ORDER BY vigente_desde DESC, concepto
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "concepto": r[1],
                "porcentaje": float(r[2]),
                "vigente_desde": str(r[3]),
                "vigente_hasta": str(r[4]) if r[4] else None,
                "creado_en": str(r[5])
            }
            for r in rows
        ]
