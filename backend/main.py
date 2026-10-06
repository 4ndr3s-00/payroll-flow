from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import logging
from backend.routers import auth, liquidaciones, horas, empleados, catalogos, reportes, payroll_v1
from backend.database import get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("payroll-flow")

app = FastAPI(
    title="PayrollFlow — Sistema de Liquidación de Nómina (SENA)",
    description="API RESTful para la automatización, cálculo auditable y gestión de liquidaciones de nómina financiera según especificaciones SENA.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anti-cache middleware for SPA static files
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".html") or path.endswith(".js") or path == "/" or path == "":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error processing request to {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Error interno del servidor: {str(exc)}",
            "type": type(exc).__name__
        }
    )

# Include Routers
app.include_router(auth.router)
app.include_router(liquidaciones.router)
app.include_router(horas.router)
app.include_router(empleados.router)
app.include_router(catalogos.router)
app.include_router(reportes.router)
app.include_router(payroll_v1.router)

# Healthcheck
@app.get("/api/health", tags=["Salud"])
def health_check():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT version();")
            pg_ver = cur.fetchone()[0]
        return {
            "status": "healthy",
            "database": "connected",
            "version": pg_ver
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "database_error": str(e)}
        )

# Static and SPA routing
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return JSONResponse(status_code=404, content={"detail": "Not found"})
