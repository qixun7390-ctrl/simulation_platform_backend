from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.simulation import Simulation
from app.schemas.simulation import OrderLogResponse, OrderLogData, VehicleOrderListResponse, VehicleOrderDetailResponse
from app.db.database import get_db
from app.services.parse_status_log import build_order_data_from_status_log, build_vehicle_order_data_from_status_log

router = APIRouter(prefix="/logs", tags=["logs"])

def verify_token(authorization: str | None = Header(default=None, alias="Authorization"),) -> None:
    if not settings.API_TOKEN:
        return

    expected = f"Token {settings.API_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code = 401,
            detail = "Not authenticated",
        )

async def get_simulation_or_404(
    db: AsyncSession,
    simulation_id: int,
) -> Simulation:
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=404,
            detail="没有找到Simulation数据"
        )
    return simulation

@router.get("/order/{simulation_id}/",response_model=OrderLogResponse)
async def get_order_logs(
    simulation_id: int,
    time: int | None = None,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    simulation = await get_simulation_or_404(db, simulation_id)
    order_data = build_order_data_from_status_log(
        simulation=simulation,
        time=time,
    )

    total_revenue = sum(item.revenue for item in order_data)
    return OrderLogResponse(
        message="Success",
        data=OrderLogData(
            total_revenue=total_revenue,
            order_data=order_data,
        )
    )

@router.get("/vehicle/order/{simulation_id}/", response_model=VehicleOrderListResponse)
async def get_vehicle_order_logs(
    simulation_id: int,
    time: int | None = None,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    simulation = await get_simulation_or_404(db, simulation_id)
    vehicle_order_data = build_vehicle_order_data_from_status_log(
        simulation=simulation,
        time=time,
    )

    return VehicleOrderListResponse(
        message="查询成功",
        data = vehicle_order_data
    )

@router.get("/vehicle/order/{simulation_id}/{vehicle_id}/", response_model=VehicleOrderDetailResponse)
async def get_vehicle_order_detail(
    simulation_id: int,
    vehicle_id: int,
    time: int | None = None,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    simulation = await get_simulation_or_404(db, simulation_id)
    vehicle_order_data = build_vehicle_order_data_from_status_log(
        simulation=simulation,
        time=time,
    )

    for item in vehicle_order_data:
        if item.vehicle_id == vehicle_id:
            return VehicleOrderDetailResponse(
                message="Success",
                data=item,
            )
    raise HTTPException(
        status_code=404,
        detail="没有找到Vehicle数据",
    )