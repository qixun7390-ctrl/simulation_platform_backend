from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.datamanager import Area, StopData, OrderData, BusData
from app.schemas.datamanager import AreaResponse, StopDataResponse, OrderDataResponse, BusDataResponse
from fastapi import Form, APIRouter, UploadFile, File, Depends, HTTPException
from app.db.database import get_db
from app.services.storage_service import simple_slugify, read_json_upload, save_bytes
from uuid import uuid4
from pathlib import Path

router = APIRouter(prefix="/datamanager",tags=["datamanager"])

@router.post("/area/",response_model=AreaResponse)
async def create_area(
    name: str = Form(...),
    description: str | None = Form(None),
    map_file: UploadFile = File(...),
    signal_file: UploadFile = File(...),
    border_file: UploadFile | None = File(None),
    walk_links_file: UploadFile | None = File(None),
    walk_signals_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    base_slug = simple_slugify(name)
    slug = f"{base_slug}_{uuid4().hex[:8]}"

    try:
        map_content = await read_json_upload(map_file)
        signal_content = await read_json_upload(signal_file)
        border_content = await read_json_upload(border_file) if border_file else None
        walk_links_content = (
            await read_json_upload(walk_links_file)
            if walk_links_file
            else b"[]"
        )
        walk_signals_content = (
            await read_json_upload(walk_signals_file)
            if walk_signals_file
            else b"[]"
        )
    except Exception as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

    area = Area(
        name=name,
        slug=slug,
        description=description,
        map_file_path="",
        signal_file_path="",
        walk_signals_file_path="",
        walk_links_file_path="",
        border_file_path=None,
    )
    db.add(area)
    await db.flush()

    map_saved_name = Path(map_file.filename).name
    signal_saved_name = Path(signal_file.filename).name
    walk_links_saved_name = (
        Path(walk_links_file.filename).name
        if walk_links_file and walk_links_file.filename
        else "walk_links.json"
    )

    walk_signals_saved_name = (
        Path(walk_signals_file.filename).name
        if walk_signals_file and walk_signals_file.filename
        else "walk_signals.json"
    )

    area_dir = settings.STORAGE_ROOT / f"{area.slug}_area"

    area.map_file_path = save_bytes(area_dir/ "map" / map_saved_name, map_content)
    area.signal_file_path = save_bytes(area_dir / "signals" / signal_saved_name, signal_content)
    area.walk_links_file_path = save_bytes(area_dir / "walk_links" / walk_links_saved_name, walk_links_content)
    area.walk_signals_file_path = save_bytes(area_dir / "walk_signals" / walk_signals_saved_name, walk_signals_content)

    if border_content is not None:
        border_saved_name = Path(border_file.filename).name
        area.border_file_path = save_bytes(area_dir / "borders" / border_saved_name, border_content)

    await db.commit()
    await db.refresh(area)

    return AreaResponse(
        id = area.id,
        name = area.name,
        slug = area.slug,
        description = area.description,
        map_file = area.map_file_path,
        signal_file = area.signal_file_path,
        border_file = area.border_file_path,
        walk_links_file = area.walk_links_file_path,
        walk_signals_file = area.walk_signals_file_path,
        created_at = area.created_at.isoformat()
    )

@router.post('/stop/',response_model=StopDataResponse)
async def create_stop_data(
    area: int = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Area).where(Area.id == area))
    area_obj = result.scalar_one_or_none()

    if not area_obj:
        raise HTTPException(status_code=404, detail="Area not found")

    try:
        file_content = await read_json_upload(file)
    except Exception as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

    stop_data = StopData(
        area_id = area_obj.id,
        name=name,
        description=description,
        file_path=""
    )

    db.add(stop_data)
    await db.flush()

    file_saved_name = Path(file.filename).name

    stop_dir = settings.STORAGE_ROOT / f"{area_obj.slug}_area" / "stops" / file_saved_name
    stop_data.file_path = save_bytes(stop_dir , file_content)

    await db.commit()
    await db.refresh(stop_data)

    return StopDataResponse(
        id=stop_data.id,
        name=stop_data.name,
        area=stop_data.area_id,
        file=stop_data.file_path,
        description=stop_data.description,
        created_at=stop_data.created_at.isoformat(),
    )

@router.post("/order/", response_model=OrderDataResponse)
async def create_order_data(
    area: int = Form(...),
    linked_stops: int = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    area_result = await db.execute(select(Area).where(Area.id == area))
    area_obj = area_result.scalar_one_or_none()

    if not area_obj:
        raise HTTPException(status_code=404,detail="没有找到地区")

    stop_result = await db.execute(
        select(StopData).where(
            StopData.id == linked_stops,
            StopData.area_id == area,
        )
    )

    stop_obj = stop_result.scalar_one_or_none()
    if not stop_obj:
        raise HTTPException(status_code=404,detail="没有找到站点信息")

    try:
        file_content = await read_json_upload(file)
    except Exception as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

    order_data = OrderData(
        area_id = area_obj.id,
        linked_stops_id=stop_obj.id,
        name=name,
        description=description,
        file_path=""
    )
    db.add(order_data)
    await db.flush()

    file_saved_name = Path(file.filename).name
    order_dir = settings.STORAGE_ROOT / f"{area_obj.slug}_area"/ "orders" / file_saved_name
    order_data.file_path = save_bytes(order_dir, file_content)

    await db.commit()
    await db.refresh(order_data)
    return OrderDataResponse(
        id=order_data.id,
        name=order_data.name,
        area=order_data.area_id,
        linked_stops=order_data.linked_stops_id,
        description=description,
        file=order_data.file_path,
        created_at=order_data.created_at.isoformat()
    )

@router.post('/bus/',response_model=BusDataResponse)
async def create_bus_data(
    area: int = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    area_result = await db.execute(select(Area).where(Area.id == area))
    area_obj = area_result.scalar_one_or_none()

    if not area_obj:
        raise HTTPException(status_code=404, detail="没有找到区域")
    try:
        file_content = await read_json_upload(file)
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e)) from e
    bus_data = BusData(
        area_id = area_obj.id,
        name = name,
        description = description,
        file_path = "",
    )

    db.add(bus_data)
    await db.flush()

    file_saved_name = Path(file.filename).name
    bus_dir = settings.STORAGE_ROOT / f"{area_obj.slug}_area" / "buses" / file_saved_name
    bus_data.file_path = save_bytes(bus_dir, file_content)

    await db.commit()
    await db.refresh(bus_data)

    return BusDataResponse(
        id=bus_data.id,
        name=bus_data.name,
        area=bus_data.area_id,
        file=bus_data.file_path,
        description=bus_data.description,
        created_at=bus_data.created_at.isoformat(),
    )