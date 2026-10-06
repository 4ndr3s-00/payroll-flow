"""
PayrollFlow — Script de Inicialización y Sembrado de Base de Datos
Ejecuta 01_schema.sql y 02_seed.sql en PostgreSQL de forma limpia e idempotente.
Uso: python init_db.py [--reset]
"""

import sys
import os
import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Forzar codificación UTF-8 en terminales de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.config import settings

def init_database(reset: bool = False):
    print("=" * 60)
    print("  PayrollFlow - Inicializador de Base de Datos PostgreSQL")
    print("=" * 60)
    print(f">> Conectando a {settings.DB_HOST}:{settings.DB_PORT} como usuario '{settings.DB_USER}'...")

    # 1. Conectar al catálogo de PostgreSQL para verificar/crear la base de datos
    try:
        admin_conn = psycopg2.connect(
            dbname="postgres",
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            client_encoding="utf-8"
        )
        admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with admin_conn.cursor() as cur:
            if reset:
                print(f"[!] Modo --reset: Eliminando base de datos '{settings.DB_NAME}' si existe...")
                cur.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{settings.DB_NAME}'
                      AND pid <> pg_backend_pid();
                """)
                cur.execute(f"DROP DATABASE IF EXISTS {settings.DB_NAME};")
                print(f"[OK] Base de datos '{settings.DB_NAME}' eliminada.")

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (settings.DB_NAME,))
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {settings.DB_NAME} ENCODING 'UTF8';")
                print(f"[OK] Base de datos '{settings.DB_NAME}' creada con exito.")
            else:
                print(f"[INFO] Base de datos '{settings.DB_NAME}' ya existe.")
        admin_conn.close()
    except Exception as e:
        print(f"[ERROR] Error al conectar a PostgreSQL: {e}")
        print("[AYUDA] Verifica que PostgreSQL este ejecutandose y que las credenciales en .env sean correctas.")
        sys.exit(1)

    # 2. Conectar a la base de datos objetivo para aplicar esquema y semilla
    try:
        db_conn = psycopg2.connect(
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            client_encoding="utf-8"
        )
        db_conn.autocommit = True
        with db_conn.cursor() as cur:
            # Comprobar si ya existen tablas
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'empleados';
            """)
            has_tables = cur.fetchone()[0] > 0

            if not has_tables or reset:
                print(">> Aplicando 01_schema.sql...")
                schema_path = os.path.join(os.path.dirname(__file__), "01_schema.sql")
                with open(schema_path, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
                print("[OK] 01_schema.sql ejecutado correctamente.")

                print(">> Aplicando 02_seed.sql...")
                seed_path = os.path.join(os.path.dirname(__file__), "02_seed.sql")
                with open(seed_path, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
                print("[OK] 02_seed.sql ejecutado correctamente.")
            else:
                print("[INFO] Las tablas ya existen. Para reiniciar desde cero, ejecuta: python init_db.py --reset")

            # Estadisticas finales
            cur.execute("SELECT COUNT(*) FROM empleados;")
            n_emp = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM usuarios;")
            n_usr = cur.fetchone()[0]
            print(f"[EXITO] Inicializacion completa: {n_emp} empleados y {n_usr} usuarios listos.")

        db_conn.close()
    except Exception as e:
        print(f"[ERROR] Error al ejecutar scripts en {settings.DB_NAME}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializador de BD PayrollFlow")
    parser.add_argument("--reset", action="store_true", help="Elimina y recrea la BD desde cero con la semilla")
    args = parser.parse_args()
    init_database(reset=args.reset)
