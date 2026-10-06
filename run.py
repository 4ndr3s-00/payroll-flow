import uvicorn
import os
import sys

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 Iniciando PayrollFlow en http://localhost:{port}")
    print(f"📖 Documentación OpenAPI Swagger: http://localhost:{port}/docs")
    print(f"👥 Roles de prueba disponibles (Clave: Cambiar123*):")
    print(f"   👑 Gerente:   gerente@empresa.test")
    print(f"   💼 Admin:     admin01@empresa.test")
    print(f"   👷 Operario:  operario01@empresa.test")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
