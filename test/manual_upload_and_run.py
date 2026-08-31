from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"

DATA_DIR = Path(r"E:\simulator\shaoxing_data")


def post_area() -> int:
    url = f"{BASE_URL}/api/datamanager/area/"

    files = {
        "map_file": ("map.json", open(DATA_DIR / "map.json", "rb"), "application/json"),
        "signal_file": ("signal.json", open(DATA_DIR / "signal.json", "rb"), "application/json"),
    }

    data = {
        "name": "shaoxing",
        "description": "manual upload test",
    }

    try:
        response = requests.post(url, data=data, files=files, timeout=60)
    finally:
        for _, file_tuple in files.items():
            file_tuple[1].close()

    print("AREA:", response.status_code)
    print(response.text)
    response.raise_for_status()

    return response.json()["id"]


def post_stop(area_id: int) -> int:
    url = f"{BASE_URL}/api/datamanager/stop/"

    with open(DATA_DIR / "stop.json", "rb") as file:
        response = requests.post(
            url,
            data={
                "area": str(area_id),
                "name": "shaoxing_stop",
                "description": "manual upload test",
            },
            files={
                "file": ("stop.json", file, "application/json"),
            },
            timeout=60,
        )

    print("STOP:", response.status_code)
    print(response.text)
    response.raise_for_status()

    return response.json()["id"]


def post_order(area_id: int, stop_id: int) -> int:
    url = f"{BASE_URL}/api/datamanager/order/"

    with open(DATA_DIR / "order.json", "rb") as file:
        response = requests.post(
            url,
            data={
                "area": str(area_id),
                "linked_stops": str(stop_id),
                "name": "shaoxing_order",
                "description": "manual upload test",
            },
            files={
                "file": ("order.json", file, "application/json"),
            },
            timeout=60,
        )

    print("ORDER:", response.status_code)
    print(response.text)
    response.raise_for_status()

    return response.json()["id"]


def post_bus(area_id: int) -> int:
    url = f"{BASE_URL}/api/datamanager/bus/"

    with open(DATA_DIR / "bus.json", "rb") as file:
        response = requests.post(
            url,
            data={
                "area": str(area_id),
                "name": "shaoxing_bus",
                "description": "manual upload test",
            },
            files={
                "file": ("bus.json", file, "application/json"),
            },
            timeout=60,
        )

    print("BUS:", response.status_code)
    print(response.text)
    response.raise_for_status()

    return response.json()["id"]


def create_simulation(area_id: int, stop_id: int, order_id: int, bus_id: int) -> dict:
    url = f"{BASE_URL}/api/simulation/simulation/"

    payload = {
        "name": "shaoxing_manual_test",
        "type": "offline",
        "description": "manual celery simulation test",
        "running_time_step": 3600,
        "use_random_match": True,
        "use_cost": True,
        "area": area_id,
        "order_data": order_id,
        "stop_data": stop_id,
        "bus_data": bus_id,
    }

    response = requests.post(url, json=payload, timeout=60)

    print("SIMULATION:", response.status_code)
    print(response.text)
    response.raise_for_status()

    return response.json()


def main() -> None:
    area_id = post_area()
    stop_id = post_stop(area_id)
    order_id = post_order(area_id, stop_id)
    bus_id = post_bus(area_id)

    result = create_simulation(
        area_id=area_id,
        stop_id=stop_id,
        order_id=order_id,
        bus_id=bus_id,
    )

    print("\nDONE")
    print(result)


if __name__ == "__main__":
    main()