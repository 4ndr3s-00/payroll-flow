from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Dict, Any
from backend.schemas import EmpleadoItem, EmpleadoCreate, EmpleadoUpdate
from backend.database import get_db_cursor
from backend.security import require_roles, hash_password
from backend.services.audit import record_audit

router = APIRouter(prefix="/api/empleados", tags=["Empleados"])

@router.get("", response_model=List[EmpleadoItem])
def listar_empleados(
    activo: bool | None = None,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN", "GERENTE"]))
):
    query = """
        SELECT e.id, e.documento, e.nombres, e.apellidos, e.salario_base,
               e.num_hijos, e.perfil_id, p.codigo as perfil_codigo, p.nombre as perfil_nombre,
               e.fecha_ingreso, e.activo, u.email, r.codigo as rol
        FROM empleados e
        JOIN perfiles p ON p.id = e.perfil_id
        LEFT JOIN usuarios u ON u.empleado_id = e.id
        LEFT JOIN roles r ON r.id = u.rol_id
        WHERE 1=1
    """
    params = []
    if activo is not None:
        query += " AND e.activo = %s"
        params.append(activo)
    query += " ORDER BY e.id"

    with get_db_cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        return [
            EmpleadoItem(
                id=r[0],
                documento=r[1],
                nombres=r[2],
                apellidos=r[3],
                salario_base=r[4],
                num_hijos=r[5],
                perfil_id=r[6],
                perfil_codigo=r[7],
                perfil_nombre=r[8],
                fecha_ingreso=r[9],
                activo=r[10],
                email=r[11],
                rol=r[12]
            )
            for r in rows
        ]

@router.post("", status_code=status.HTTP_201_CREATED)
def crear_empleado(
    payload: EmpleadoCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        # 1. Validar unicidad de documento y correo
        cur.execute("SELECT id FROM empleados WHERE documento = %s", (payload.documento,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El documento ya está registrado")

        cur.execute("SELECT id FROM usuarios WHERE email = %s", (payload.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

        cur.execute("SELECT id FROM roles WHERE codigo = %s", (payload.rol_codigo,))
        rol_row = cur.fetchone()
        if not rol_row:
            raise HTTPException(status_code=400, detail="Rol inválido")
        rol_id = rol_row[0]

        # 2. Insertar empleado
        cur.execute("""
            INSERT INTO empleados (documento, nombres, apellidos, salario_base, num_hijos, perfil_id, fecha_ingreso)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE)
            RETURNING id
        """, (payload.documento, payload.nombres, payload.apellidos, payload.salario_base, payload.num_hijos, payload.perfil_id))
        emp_id = cur.fetchone()[0]

        # 3. Crear usuario asociado
        pw_hash = hash_password(payload.password or "Cambiar123*")
        cur.execute("""
            INSERT INTO usuarios (empleado_id, email, password_hash, rol_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (emp_id, payload.email, pw_hash, rol_id))
        user_id = cur.fetchone()[0]

        record_audit(
            usuario_id=current_user["id"],
            accion="CREAR_EMPLEADO",
            entidad="empleados",
            entidad_id=str(emp_id),
            datos={"documento": payload.documento, "email": payload.email},
            ip=ip,
            cur=cur
        )

    return {"message": "Empleado y usuario creados exitosamente", "empleado_id": emp_id, "usuario_id": user_id}

@router.put("/{id}")
def actualizar_empleado(
    id: int,
    payload: EmpleadoUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM empleados WHERE id = %s", (id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Empleado no encontrado")

        updates = []
        params = []
        if payload.nombres is not None:
            updates.append("nombres = %s")
            params.append(payload.nombres)
        if payload.apellidos is not None:
            updates.append("apellidos = %s")
            params.append(payload.apellidos)
        if payload.salario_base is not None:
            updates.append("salario_base = %s")
            params.append(payload.salario_base)
        if payload.num_hijos is not None:
            updates.append("num_hijos = %s")
            params.append(payload.num_hijos)
        if payload.perfil_id is not None:
            updates.append("perfil_id = %s")
            params.append(payload.perfil_id)
        if payload.activo is not None:
            updates.append("activo = %s")
            params.append(payload.activo)

        if updates:
            params.append(id)
            query = f"UPDATE empleados SET {', '.join(updates)} WHERE id = %s"
            cur.execute(query, tuple(params))

            record_audit(
                usuario_id=current_user["id"],
                accion="EDITAR_EMPLEADO",
                entidad="empleados",
                entidad_id=str(id),
                datos=payload.model_dump(exclude_unset=True),
                ip=ip,
                cur=cur
            )

    return {"message": "Empleado actualizado exitosamente", "id": id}

@router.delete("/{id}")
def desactivar_empleado(
    id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["ADMIN"]))
):
    ip = request.client.host if request.client else "127.0.0.1"
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE empleados SET activo = FALSE WHERE id = %s RETURNING id", (id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        cur.execute("UPDATE usuarios SET activo = FALSE WHERE empleado_id = %s", (id,))

        record_audit(
            usuario_id=current_user["id"],
            accion="DESACTIVAR_EMPLEADO",
            entidad="empleados",
            entidad_id=str(id),
            ip=ip,
            cur=cur
        )

    return {"message": "Empleado desactivado exitosamente", "id": id}
