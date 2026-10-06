import uvicorn
import os
import sys

# Asegurar codificación UTF-8 en terminales de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def verificar_base_de_datos():
    try:
        from backend.database import get_db_cursor
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM empleados;")
            total_emp = cur.fetchone()[0]
        print(f" Base de datos conectada correctamente ({total_emp} empleados en sistema).")
        return True
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo verificar la base de datos: {e}")
        print("💡 Recuerda ejecutar 'python init_db.py' si es la primera vez que inicias el sistema.")
        return False

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print("=" * 65)
    print("  PayrollFlow - Sistema de Liquidacion de Nomina Financiera (SENA)")
    print("=" * 65)
    verificar_base_de_datos()
    print(f">> Servidor web disponible en: http://localhost:{port}")
    print(f">> Documentacion Swagger:     http://localhost:{port}/docs")
    print(">> Usuarios de prueba (Contrasena: Cambiar123*):")
    print("   * Gerente:   gerente@empresa.test")
    print("   * Admin:     admin01@empresa.test")
    print("   * Operario:  operario01@empresa.test")
    print("=" * 65)
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
