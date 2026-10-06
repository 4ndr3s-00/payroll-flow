from typing import Optional, Dict, Any
import json
from backend.database import get_db_cursor

def record_audit(
    usuario_id: Optional[int],
    accion: str,
    entidad: str,
    entidad_id: Optional[str] = None,
    datos: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    cur = None
):
    sql = """
        INSERT INTO audit_log (usuario_id, accion, entidad, entidad_id, datos, ip)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    import ipaddress
    clean_ip = None
    if ip:
        try:
            clean_ip = str(ipaddress.ip_address(ip))
        except ValueError:
            clean_ip = "127.0.0.1"

    params = (
        usuario_id,
        accion,
        entidad,
        entidad_id,
        json.dumps(datos) if datos else None,
        clean_ip
    )
    if cur:
        cur.execute(sql, params)
    else:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(sql, params)
