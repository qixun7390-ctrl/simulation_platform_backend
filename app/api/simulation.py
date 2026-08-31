from fastapi import APIRouter, Depends, HTTPException,Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

import math
from app.services.parse_status_log import (
    load_bus_map,
    build_vehicle_data_from_status_log,
)

from app.core.config import settings
from app.db.database import get_db
from app.models.datamanager import Area,StopData, OrderData, BusData
from app.models.simulation import Simulation
from app.schemas.simulation import (
    SimulationCreateResponse,
    SimulationDeleteResponse,
    SimulationInfoResponse,
    SimulationInfoData,
)
from app.tasks.simulation_tasks import run_offline_simulation_task
from datetime import datetime

router = APIRouter(prefix="/simulation",tags=['simulation'])

async def get_obj(db: AsyncSession, model,record_id, message: str):
    result = await db.execute(
        select(model).where(model.id == record_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404,detail=message)
    return obj

def build_simulation_info(
    simulation: Simulation,
    area: Area,
    bus_data: BusData,
    interval: int = 120,
    page: int = 1
) -> SimulationInfoData:
    """组装接口要返回的data"""
    safe_interval = max(int(interval or 120), 1)
    #仿真物理时间
    simulation_duration = float(simulation.running_time_step or 0)
    total_pages = (
        math.ceil(simulation_duration / safe_interval)
        if simulation_duration
        else 0
    )

    safe_page = max(int(page or 1), 1)

    bus_map = load_bus_map(bus_data.file_path)
    vehicle_data = build_vehicle_data_from_status_log(
        simulation=simulation,
        bus_map=bus_map,
        interval=safe_interval,
        page=safe_page,
    )

    return SimulationInfoData(
        simulation_id=simulation.id,
        name=simulation.name,
        type=simulation.type,
        status=simulation.status,
        area=area.name,
        area_center_lng=None,
        area_center_lat=None,
        description=simulation.description,
        created_time=simulation.created_time.isoformat(),
        end_time=simulation.end_time.isoformat() if simulation.end_time else None,
        simulation_duration=simulation_duration,
        page_interval=safe_interval,
        total_pages=total_pages,
        current_page=safe_page,
        total_vehicles=len(bus_map),
        vehicle_data=vehicle_data,
    )

@router.post("/simulation/", response_model=SimulationCreateResponse)
async def create_simulation(
        name: str = Form("default"),
        type: str = Form("offline"),
        description: str | None = Form(None),
        running_time_step: float = Form(3600.0),
        use_random_match: bool = Form(True),
        use_cost: bool = Form(False),
        area: int = Form(...),
        order_data: int = Form(...),
        stop_data: int = Form(...),
        bus_data: int = Form(...),
        db: AsyncSession = Depends(get_db),
):
    """
    API层，负责接需求，校验参数，创建数据库记录，投递任务，返回task_id
    """
    area_obj = await get_obj(db, Area, area, "没有找到Area数据")
    stop_obj = await get_obj(db, StopData, stop_data, "没有找到Stop数据")
    bus_obj = await get_obj(db, BusData, bus_data, "没有找到Bus数据")
    order_obj = await get_obj(db, OrderData, order_data, "没有找到Order数据")

    if stop_obj.area_id != area_obj.id:
        raise HTTPException(status_code=400,detail="站点数据并不属于该区域")
    if order_obj.area_id != area_obj.id:
        raise HTTPException(status_code=400,detail="订单数据并不属于该Area")
    if order_obj.linked_stops_id != stop_obj.id:
        raise HTTPException(status_code=400,detail="订单数据并不属于该站台")
    if bus_obj.area_id != area_obj.id:
        raise HTTPException(status_code=400,detail="车辆数据并不属于该区域")

    simulation = Simulation(
        name=name,
        type=type,
        description=description,
        running_time_step=running_time_step,
        use_random_match=use_random_match,
        use_cost=use_cost,
        area_data_id=area_obj.id,
        order_data_id=order_obj.id,
        stop_data_id=stop_obj.id,
        bus_data_id=bus_obj.id,
        status="PENDING",
        log_path="",
        log_name="",
    )
    db.add(simulation)
    await db.flush()

    task_id = f"simulation-{simulation.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    log_path = settings.SIMULATION_LOG_ROOT / "simulator" / task_id
    log_path.mkdir(parents=True, exist_ok=True)

    simulation.log_path = str(log_path)
    simulation.log_name = task_id

    await db.commit()
    await db.refresh(simulation)

    #落库后投递任务
    run_offline_simulation_task.apply_async(
        args=[simulation.id],
        task_id=task_id
    )

    return SimulationCreateResponse(
        message="Success",
        data={
            "simulation_id": simulation.id,
            "task_id": task_id,
            "status": simulation.status,
            "log_path": simulation.log_path,
            "log_name": simulation.log_name,
        }
    )

@router.get(
    "/simulation/{simulation_id}/",
    response_model=SimulationInfoResponse
)
async def get_simulation_detail(
    simulation_id: int,
    interval: int = 120,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """数据库中simulation / area / bus，后将其中数据提取组装"""
    simulation = await get_obj(
        db,
        Simulation,
        simulation_id,
        "没有找到Simulation数据",
    )
    area_obj = await get_obj(
        db,
        Area,
        simulation.area_data_id,
        "没有找到Area数据",
    )
    bus_obj = await get_obj(
        db,
        BusData,
        simulation.bus_data_id,
        "没有找到Bus数据"
    )
    data = build_simulation_info(
        simulation=simulation,
        area=area_obj,
        bus_data=bus_obj,
        interval=interval,
        page=page,
    )
    return SimulationInfoResponse(
        message="Success",
        data=data,
    )

@router.delete("/simulation/{simulation_id}/",response_model=SimulationDeleteResponse)
async def delete_simulation(
    simulation_id: int,
    db: AsyncSession = Depends(get_db),
):
    simulation = await get_obj(
        db,
        Simulation,
        simulation_id,
        "没有找到对应的Simulation数据"
    )
    try:
        await db.delete(simulation)
        await db.commit()

        return SimulationDeleteResponse(
            message="Success",
            simulation_id=simulation_id,
        )
    except Exception as e:
        return SimulationDeleteResponse(
            message="FAILED",
            simulation_id=simulation_id
        )

