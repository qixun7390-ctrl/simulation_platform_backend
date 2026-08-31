from pydantic import BaseModel, ConfigDict


class SimulationCreateRequest(BaseModel):
    name: str = "default"
    type: str = "offline"
    description: str | None = None
    running_time_step: float = 3600.0
    use_random_match: bool = True
    use_cost: bool = False

    area: int
    order_data: int
    stop_data: int
    bus_data: int

class SimulationCreateData(BaseModel):
    simulation_id: int
    task_id: str
    status: str
    log_path: str | None = None
    log_name: str | None = None

class SimulationCreateResponse(BaseModel):
    """任务创建完成后，做状态查询"""
    message: str
    data: SimulationCreateData

class SimulationDeleteResponse(BaseModel):
    simulation_id: int
    message: str

class VehicleDataItem(BaseModel):
    vehicle_id: int
    vehicle_num: str | None = ""
    vehicle_speed: float | None = None
    vehicle_capacity: int | None = None
    vehicle_length: float | None = None
    vehicle_init_stop_id: int | None = None
    simulation_run_id: int
    simulation_time: float
    lng: float | None = None
    lat: float | None = None
    direction: float | None = None
    offset: float | None = None
    start_time: float | None = 0
    original_lng: float | None = None
    original_lat: float | None = None

class SimulationInfoData(BaseModel):
    simulation_id: int
    name: str
    type: str
    status: str
    area: str
    area_center_lng: float | None = None
    area_center_lat: float | None = None
    description: str | None = None
    created_time: str
    end_time: str | None = None
    simulation_duration: float
    page_interval: int
    total_pages: int
    current_page: int
    total_vehicles: int
    vehicle_data: list[VehicleDataItem]

class SimulationInfoResponse(BaseModel):
    message: str
    data: SimulationInfoData

class SimulationListResponse(BaseModel):
    message: str
    data: list[SimulationInfoData]

class OrderLogItem(BaseModel):
    order_id: int
    created_time: float | None = None
    matched_time: float | None = None
    pickup_time: float | None = None
    dropoff_time: float | None = None
    cancelled_time: float | None = None
    passenger_num: int | None = None
    passenger_id: int | None = None
    origin_stop_id: int | None = None
    destination_stop_id: int | None = None
    vehicle_id: int | None = None
    revenue: float = 0
    actual_time: float = 0
    direct_time: float = 0
    detour_time: float = 0
    detour_ratio_time: float = 0
    actual_dist: float = 0
    direct_dist: float = 0
    detour_dist: float = 0
    detour_ratio_dist: float = 0
    detour_stop_num: int = 0

class OrderLogData(BaseModel):
    total_revenue: float
    order_data: list[OrderLogItem]

class OrderLogResponse(BaseModel):
    message: str
    data: OrderLogData

class VehicleOrderItem(BaseModel):
    vehicle_id: int
    orders: list[int]
    passenger_cnt_with_time: list[list[float | int]]
    passenger_onboard_time: list[float]
    passenger_offboard_time: list[float]
    current_passenger_count: int
    orders_topick: list[int]
    orders_todrop: list[str]
    orders_finished: list[int]
    stops: list[int]
    arrive_stop_with_time: list[list[float | int]]

class VehicleOrderListResponse(BaseModel):
    message: str
    data: list[VehicleOrderItem]

class VehicleOrderDetailResponse(BaseModel):
    message: str
    data: VehicleOrderItem