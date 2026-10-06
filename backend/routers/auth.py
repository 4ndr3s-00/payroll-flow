from fastapi import APIRouter, HTTPException, status, Depends
from backend.schemas import LoginRequest, LoginResponse, UserResponse
from backend.database import get_db_cursor
from backend.security import verify_password, create_access_token, get_current_user
from backend.services.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT u.id, u.email, u.password_hash, u.activo, r.codigo as rol,
                   e.id as empleado_id, e.nombres, e.apellidos, e.documento,
                   p.codigo as perfil_codigo, p.nombre as perfil_nombre
            FROM usuarios u
            JOIN roles r ON r.id = u.rol_id
            JOIN empleados e ON e.id = u.empleado_id
            JOIN perfiles p ON p.id = e.perfil_id
            WHERE u.email = %s
        """, (credentials.email,))
        user = cur.fetchone()

        if not user or not verify_password(credentials.password, user[2]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas (correo o contraseña no válidos)"
            )

        if not user[3]:  # activo
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario se encuentra inactivo en el sistema"
            )

        user_id = user[0]
        cur.execute("UPDATE usuarios SET ultimo_acceso = now() WHERE id = %s", (user_id,))
        record_audit(
            usuario_id=user_id,
            accion="LOGIN",
            entidad="usuarios",
            entidad_id=str(user_id),
            cur=cur
        )

        user_res = UserResponse(
            id=user_id,
            email=user[1],
            rol=user[4],
            empleado_id=user[5],
            nombres=user[6],
            apellidos=user[7],
            nombre_completo=f"{user[6]} {user[7]}",
            documento=user[8],
            perfil_codigo=user[9],
            perfil_nombre=user[10]
        )

        token = create_access_token({"sub": str(user_id), "rol": user[4]})
        return LoginResponse(access_token=token, user=user_res)

@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        rol=current_user["rol"],
        empleado_id=current_user["empleado_id"],
        nombres=current_user["nombres"],
        apellidos=current_user["apellidos"],
        nombre_completo=current_user["nombre_completo"],
        documento=current_user["documento"],
        perfil_codigo=current_user["perfil_codigo"],
        perfil_nombre=current_user["perfil_nombre"]
    )
