from fastapi import APIRouter, status
from backend.schemas import SimulateSingleRequest, SimulateSingleResponse
from backend.services.calculation import simular_calculo_individual

router = APIRouter(prefix="/api/v1/payroll", tags=["Payroll v1 - API Contracts"])

@router.post(
    "/simulate-single",
    response_model=SimulateSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulación / Cálculo Individual Rápido",
    description="Permite a la interfaz probar el impacto de horas, tarifa o hijos sin persistir en base de datos (según docs/6-api-contracts.md)."
)
def simulate_single_payroll(payload: SimulateSingleRequest):
    result = simular_calculo_individual(
        hours_worked=payload.hours_worked,
        hourly_rate=payload.hourly_rate,
        num_children=payload.num_children,
        arl_rate=payload.arl_rate
    )
    return result
