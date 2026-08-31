import json
from pathlib import Path
from app.core.config import settings
from app.schemas.simulation import VehicleDataItem, OrderLogItem, VehicleOrderItem


def to_backend_abs_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (settings.BASE_DIR / path).resolve()

def safe_int(value, default=None):
    try:
        return int(value)
    except Exception as e:
        return default

def safe_float(value,default=None):
    try:
        return float(value)
    except Exception as e:
        return default

def load_bus_map(bus_file_path: str) -> dict[int, dict]:
    path = to_backend_abs_path(bus_file_path)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as e:
        return {}

    if not isinstance(data,list):
        return {}

    result = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        vehicle_id = item.get("vehicle_id")
        if vehicle_id is None:
            continue
        try:
            result[int(vehicle_id)] = item
        except Exception as e:
            continue
    return result

def parse_position_coordinate(value) -> tuple[float | None, float | None]:
    """解析position坐标"""
    if not value:
        return None , None
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None , None
    lng = safe_float(data.get("lon"))
    lat = safe_float(data.get("lat"))
    return lng, lat

def get_status_log_path(simulation) -> Path | None:
    if not simulation.log_path or not simulation.log_name:
        return None

    log_dir = to_backend_abs_path(simulation.log_path)
    status_log_path = log_dir / f"{simulation.log_name}_status.log"

    if not status_log_path.exists():
        return None

    return status_log_path

def get_status_log_line(line: str) -> dict | None:
    try:
        outer = json.loads(line)
        args = outer.get("args")
        if not args:
            return None
        inner = json.loads(args)
    except (TypeError, json.JSONDecodeError):
        return None

    if not isinstance(inner, dict):
        return None
    return inner

def build_vehicle_item(
    event: dict,
    simulation_id: int,
    bus_map: dict[int, dict],
) -> VehicleDataItem | None:
    """获取单条status日志的运行位置信息和静态车辆信息"""
    vehicle_id = safe_int(event.get("vehicle_id"))
    if vehicle_id is None:
        return None
    lng, lat = parse_position_coordinate(
        event.get("position_coordinate")
    )

    bus_info = bus_map.get(vehicle_id, {})
    return VehicleDataItem(
        vehicle_id=vehicle_id,
        vehicle_num=bus_info.get("vehicle_num", ""),
        vehicle_speed=(
                safe_float(bus_info.get("vehicle_speed"))
                or safe_float(event.get("speed"))
        ),
        vehicle_capacity=safe_int(bus_info.get("vehicle_capacity")),
        vehicle_length=safe_float(bus_info.get("vehicle_length")),
        vehicle_init_stop_id=safe_int(bus_info.get("vehicle_init_stop_id")),
        simulation_run_id=simulation_id,
        simulation_time=safe_float(event.get("_event_time"),0.0),
        lng=lng,
        lat=lat,
        direction=safe_float(event.get("direction")),
        offset=safe_float(event.get("offset")),
        start_time=0,
        original_lng=lng,
        original_lat=lat,
    )

def build_vehicle_data_from_status_log(
    simulation,
    bus_map: dict[int, dict],
    interval: int = 120,
    page: int = 1,
) -> list[VehicleDataItem]:
    """日志解析函数"""
    safe_interval = max((int(interval) or 120), 1)
    safe_page = max(int(page or 1), 1)

    start_time = (safe_page - 1) * safe_interval
    end_time = safe_page * safe_interval
    status_log_path = get_status_log_path(simulation)
    if status_log_path is None:
        return []
    vehicle_data: list[VehicleDataItem] = []

    seen: set[tuple[int, float, float | None, float | None]] = set()
    with status_log_path.open("r", encoding="utf-8") as file:
        for line in file:
            event = get_status_log_line(line)
            if not event:
                continue

            if event.get("_event_class_type") != "Vehicle":
                continue
            item = build_vehicle_item(
                event=event,
                simulation_id=simulation.id,
                bus_map=bus_map,
            )

            if item is None:
                continue

            if not (start_time <= item.simulation_time < end_time):
                continue
            dedupe_key = (
                item.vehicle_id,
                item.simulation_time,
                item.lng,
                item.lat
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            vehicle_data.append(item)

    return vehicle_data

def build_order_data_from_status_log(
    simulation,
    time: int | None = None,
)-> list[OrderLogItem]:
    """
        整理日志中的事件,解析用户事件，
        其中:OrderCreatedEvent 负责“订单生成”
            OrderMatchedEvent 负责“订单被哪辆车接单”
            PassengerOnboardEvent 负责“乘客上车”
            PassengerDropoffEvent / OrderFinishedEvent 负责“订单完成”
    """
    status_log_path = get_status_log_path(simulation)
    if status_log_path is None:
        return []
    max_time = safe_float(time)
    orders: dict[int, dict] = {}
    with status_log_path.open("r",encoding='utf-8') as file:
        for line in file:
            event = get_status_log_line(line)
            if not event:
                continue

            if event.get("_event_class_type") not in {"Order", "Passenger"}:
                continue

            event_time = safe_float(event.get("_event_time"))
            if max_time is not None and event_time is not None and event_time > max_time:
                continue

            order_id = safe_int(event.get("order_id"))
            if order_id is None or order_id <= 0:
                continue
            order = orders.setdefault(order_id,{"order_id": order_id})
            event_name = event.get("_event_name")
            if event_name == "OrderCreatedEvent":
                order["created_time"] = safe_float(event.get("created_time")) or event_time
                order["passenger_num"] = safe_int(event.get("passenger_num"))
                order["passenger_id"] = safe_int(event.get("passenger_id"))
            elif event_name == "OrderMatchedEvent":
                order["matched_time"] = event_time
                order["vehicle_id"] = safe_int(event.get("vehicle_id"))
                order["origin_stop_id"] = safe_int(event.get("start_stop_id"))
                order["destination_stop_id"] = safe_int(event.get("end_stop_id"))
                order["passenger_num"] = safe_int(event.get("passenger_num"))
                order["passenger_id"] = safe_int(event.get("passenger_id"))
            elif event_name == "PassengerOnboardEvent":
                order["pickup_time"] = event_time
                order["vehicle_id"] = safe_int(event.get("vehicle_id"))
                order["passenger_num"] = safe_int(event.get("passenger_num"))
                order["passenger_id"] = safe_int(event.get("passenger_id"))
            elif event_name == "PassengerDropoffEvent":
                order["dropoff_time"] = event_time
                order["vehicle_id"] = safe_int(event.get("vehicle_id"))
                order["passenger_num"] = safe_int(event.get("passenger_num"))
                order["passenger_id"] = safe_int(event.get("passenger_id"))
            elif event_name == "OrderFinishedEvent":
                order["dropoff_time"] = event_time
                order["vehicle_id"] = safe_int(event.get("vehicle_id"))
                order["origin_stop_id"] = safe_int(event.get("start_stop_id"))
                order["destination_stop_id"] = safe_int(event.get("end_stop_id"))
                order["passenger_num"] = safe_int(event.get("passenger_num"))
                order["passenger_id"] = safe_int(event.get("passenger_id"))
    return [
        OrderLogItem(**item)
        for item in sorted(orders.values(), key=lambda x: x["order_id"])
    ]

def build_vehicle_order_data_from_status_log(
    simulation,
    time: int | None = None,
) -> list[VehicleOrderItem]:
    """按 vehicle_id 聚合车辆订单完成情况"""
    status_log_path = get_status_log_path(simulation)
    if status_log_path is None:
        return []

    def add_unique(items: list, value):
        if value is not None and value not in items:
            items.append(value)

    def remove_value(items: list, value):
        if value in items:
            items.remove(value)

    max_time = safe_float(time)
    vehicles: dict[int, dict] = {}

    allowed_events = {
        "OrderMatchedEvent",
        "PassengerOnboardEvent",
        "PassengerDropoffEvent",
        "OrderFinishedEvent",
        "BusArrivalEvent",
    }

    with status_log_path.open("r", encoding="utf-8") as file:
        for line in file:
            event = get_status_log_line(line)
            if not event:
                continue

            event_name = event.get("_event_name")
            if event_name not in allowed_events:
                continue

            event_time = safe_float(event.get("_event_time"))
            if max_time is not None and event_time is not None and event_time > max_time:
                continue

            vehicle_id = safe_int(event.get("vehicle_id"))
            if vehicle_id is None or vehicle_id <= 0:
                continue

            bucket = vehicles.setdefault(vehicle_id, {
                "vehicle_id": vehicle_id,
                "orders": [],
                "passenger_cnt_with_time": [],
                "passenger_onboard_time": [],
                "passenger_offboard_time": [],
                "current_passenger_count": 0,
                "orders_topick": [],
                "orders_todrop": [],
                "orders_finished": [],
                "stops": [],
                "arrive_stop_with_time": [],
            })

            order_id = safe_int(event.get("order_id"))
            event_time_value = event_time or 0.0

            if event_name == "OrderMatchedEvent":
                add_unique(bucket["orders"], order_id)
                add_unique(bucket["orders_topick"], order_id)

            elif event_name == "PassengerOnboardEvent":
                passenger_num = safe_int(event.get("passenger_num"), 0) or 0
                order_id_str = str(order_id) if order_id is not None else None

                add_unique(bucket["orders"], order_id)
                remove_value(bucket["orders_topick"], order_id)
                add_unique(bucket["orders_todrop"], order_id_str)

                bucket["passenger_onboard_time"].append(event_time_value)
                bucket["current_passenger_count"] += passenger_num
                bucket["passenger_cnt_with_time"].append([
                    event_time_value,
                    bucket["current_passenger_count"],
                ])

            elif event_name == "PassengerDropoffEvent":
                passenger_num = safe_int(event.get("passenger_num"), 0) or 0
                order_id_str = str(order_id) if order_id is not None else None

                add_unique(bucket["orders"], order_id)
                remove_value(bucket["orders_todrop"], order_id_str)
                add_unique(bucket["orders_finished"], order_id)

                bucket["passenger_offboard_time"].append(event_time_value)
                bucket["current_passenger_count"] = max(
                    bucket["current_passenger_count"] - passenger_num,
                    0,
                )
                bucket["passenger_cnt_with_time"].append([
                    event_time_value,
                    bucket["current_passenger_count"],
                ])

            elif event_name == "OrderFinishedEvent":
                order_id_str = str(order_id) if order_id is not None else None

                add_unique(bucket["orders"], order_id)
                remove_value(bucket["orders_topick"], order_id)
                remove_value(bucket["orders_todrop"], order_id_str)
                add_unique(bucket["orders_finished"], order_id)

            elif event_name == "BusArrivalEvent":
                stop_id = safe_int(event.get("stop_id"))

                if stop_id is not None:
                    add_unique(bucket["stops"], stop_id)
                    bucket["arrive_stop_with_time"].append([
                        event_time_value,
                        stop_id,
                    ])

    return [
        VehicleOrderItem(**item)
        for item in sorted(
            vehicles.values(),
            key=lambda value: value["vehicle_id"],
        )
    ]