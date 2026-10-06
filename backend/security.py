import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, List
from backend.config import settings
from backend.database import get_db_cursor

security_scheme = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(
    token_auth: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    token_query: str | None = Query(None, alias="token")
) -> Dict[str, Any]:
    token = None
    if token_auth:
        token = token_auth.credentials
    elif token_query:
        token = token_query

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autorización",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no contiene sujeto")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT u.id, u.email, u.rol_id, r.codigo as rol, u.activo,
                   e.id as empleado_id, e.nombres, e.apellidos, e.documento,
                   p.id as perfil_id, p.codigo as perfil_codigo, p.nombre as perfil_nombre
            FROM usuarios u
            JOIN roles r ON r.id = u.rol_id
            JOIN empleados e ON e.id = u.empleado_id
            JOIN perfiles p ON p.id = e.perfil_id
            WHERE u.id = %s
        """, (user_id,))
        user_row = cur.fetchone()
        if not user_row or not user_row[4]:  # not activo
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o no encontrado")

        return {
            "id": user_row[0],
            "email": user_row[1],
            "rol_id": user_row[2],
            "rol": user_row[3],
            "empleado_id": user_row[5],
            "nombres": user_row[6],
            "apellidos": user_row[7],
            "nombre_completo": f"{user_row[6]} {user_row[7]}",
            "documento": user_row[8],
            "perfil_id": user_row[9],
            "perfil_codigo": user_row[10],
            "perfil_nombre": user_row[11]
        }

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user["rol"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado. Rol requerido: {', '.join(allowed_roles)}. Rol actual: {current_user['rol']}"
            )
        return current_user
    return role_checker
