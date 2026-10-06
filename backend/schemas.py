from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import date, datetime
from decimal import Decimal

# Auth
class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    rol: str
    empleado_id: int
    nombres: str
    apellidos: str
    nombre_completo: str
    documento: str
    perfil_codigo: str
    perfil_nombre: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Liquidacion
class LiquidacionCreateRequest(BaseModel):
    anio: int = Field(..., ge=2000, le=2100)
    mes: int = Field(..., ge=1, le=12)

class LiquidacionRechazarRequest(BaseModel):
    motivo: str = Field(..., min_length=3)

class LiquidacionAnularRequest(BaseModel):
    motivo: str = Field(..., min_length=3)

class LiquidacionResumen(BaseModel):
    id: int
    anio: int
    mes: int
    estado: str
    total_nomina: Decimal
    ejecutada_por: int
    ejecutada_por_nombre: Optional[str] = None
    ejecutada_en: datetime
    resuelta_por: Optional[int] = None
    resuelta_por_nombre: Optional[str] = None
    resuelta_en: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None
    anulada_por: Optional[int] = None
    anulada_por_nombre: Optional[str] = None
    anulada_en: Optional[datetime] = None
    motivo_anulacion: Optional[str] = None
    total_empleados: Optional[int] = None

class ConceptoItem(BaseModel):
    id: Optional[int] = None
    tipo: str
    concepto: str
    cantidad: Decimal
    valor_unitario: Decimal
    valor_total: Decimal

class DetalleEmpleadoResponse(BaseModel):
    id: int
    empleado_id: int
    documento: str
    nombres: str
    apellidos: str
    perfil: str
    salario_base: Decimal
    num_hijos: int
    horas_totales: Decimal
    devengado: Decimal
    bonificacion: Decimal
    pct_salud: Decimal
    pct_pension: Decimal
    deduccion_salud: Decimal
    deduccion_pension: Decimal
    neto: Decimal
    aportes_patronales: Decimal
    prestaciones: Decimal
    costo_empresa: Decimal
    conceptos: Optional[List[ConceptoItem]] = None

# Horas
class RegistroHorasCreate(BaseModel):
    empleado_id: Optional[int] = None  # Si es null, usa el del usuario autenticado
    fecha: date
    tipo_hora_id: int
    jornada_id: int
    horas: Decimal = Field(..., gt=0, le=24)

class HorasItem(BaseModel):
    id: int
    empleado_id: int
    empleado_nombre: str
    documento: str
    fecha: date
    tipo_hora_codigo: str
    tipo_hora_nombre: str
    jornada_nombre: str
    horas: Decimal
    estado: str
    registrado_por_nombre: str
    registrado_en: datetime
    aprobado_por_nombre: Optional[str] = None
    aprobado_en: Optional[datetime] = None

# Empleados
class EmpleadoCreate(BaseModel):
    documento: str
    nombres: str
    apellidos: str
    salario_base: Decimal = Field(..., gt=0)
    num_hijos: int = Field(0, ge=0)
    perfil_id: int
    email: str
    password: Optional[str] = "Cambiar123*"
    rol_codigo: str = "OPERARIO"

class EmpleadoUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    salario_base: Optional[Decimal] = None
    num_hijos: Optional[int] = None
    perfil_id: Optional[int] = None
    activo: Optional[bool] = None

class EmpleadoItem(BaseModel):
    id: int
    documento: str
    nombres: str
    apellidos: str
    salario_base: Decimal
    num_hijos: int
    perfil_id: int
    perfil_codigo: str
    perfil_nombre: str
    fecha_ingreso: date
    activo: bool
    email: Optional[str] = None
    rol: Optional[str] = None

# Catalogos
class PerfilItem(BaseModel):
    id: int
    codigo: str
    nombre: str
    activo: bool

class TipoHoraItem(BaseModel):
    id: int
    codigo: str
    nombre: str
    multiplicador: Decimal
    activo: bool

class TipoHoraUpdate(BaseModel):
    nombre: Optional[str] = None
    multiplicador: Optional[Decimal] = Field(None, gt=0)
    activo: Optional[bool] = None

class TarifaItem(BaseModel):
    id: int
    alcance: str
    perfil_id: Optional[int] = None
    perfil_nombre: Optional[str] = None
    empleado_id: Optional[int] = None
    empleado_nombre: Optional[str] = None
    tarifa_base: Decimal
    vigente_desde: date
    vigente_hasta: Optional[date] = None

class TarifaCreate(BaseModel):
    alcance: str = Field(..., pattern="^(GLOBAL|PERFIL|EMPLEADO)$")
    perfil_id: Optional[int] = None
    empleado_id: Optional[int] = None
    tarifa_base: Decimal = Field(..., gt=0)
    vigente_desde: date
    vigente_hasta: Optional[date] = None

# Auditoría
class AuditLogItem(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    usuario_email: Optional[str] = None
    accion: str
    entidad: str
    entidad_id: Optional[str] = None
    datos: Optional[Dict[str, Any]] = None
    ip: Optional[str] = None
    creado_en: datetime
