import os
import subprocess
from datetime import datetime
from sqlalchemy import select
from pathlib import Path
from app.db.sync_database import SyncSessionLocal
from app.models.datamanager import Area,StopData,BusData,OrderData
from app.core.config import settings
from app.models.simulation import Simulation
from app.celery_app import celery_app

def update_simulation_status(
    simulation_id: int,
    status: str,
    description: str | None = None,
    end_time: datetime | None = None,
) -> None:
    with SyncSessionLocal() as db:
        result = db.execute(
            select(Simulation)
            .where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()
        if not simulation:
            return

        simulation.status = status
        if description:
            simulation.description = description
        if end_time:
            simulation.end_time = end_time

        db.commit()

def load_simulation_context(simulation_id: int):
    """查询与获取orm模型，返回创建仿真所需上下文"""
    with SyncSessionLocal() as db:
        result = db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()

        if not simulation:
            raise RuntimeError(f"Simulation {simulation} 没有找到")

        area_result = db.execute(
            select(Area).where(Area.id == simulation.area_data_id)
        )
        area = area_result.scalar_one_or_none()

        stop_result = db.execute(
            select(StopData).where(StopData.id == simulation.stop_data_id)
        )
        stop_data = stop_result.scalar_one_or_none()

        bus_result = db.execute(
            select(BusData).where(BusData.id == simulation.bus_data_id)
        )
        bus_data = bus_result.scalar_one_or_none()

        order_result = db.execute(
            select(OrderData).where(OrderData.id == simulation.order_data_id)
        )
        order_data = order_result.scalar_one_or_none()

        missing = []
        if not area:
            missing.append("area")
        if not stop_data:
            missing.append("stop_data")
        if not order_data:
            missing.append("order_data")
        if not bus_data:
            missing.append("bus_data")
        if missing:
            raise RuntimeError(
                f"Simulation {simulation_id} 缺少相关数据: {','.join(missing)}"
            )
        return {
            "simulation_id": simulation.id,
            "running_time_step": simulation.running_time_step,
            "use_random_match": simulation.use_random_match,
            "use_cost": simulation.use_cost,
            "log_path": simulation.log_path,
            "log_name": simulation.log_name,
            "map_file_path": area.map_file_path,
            "signal_file_path": area.signal_file_path,
            "walk_links_file_path": area.walk_links_file_path,
            "walk_signals_file_path": area.walk_signals_file_path,
            "stop_file_path": stop_data.file_path,
            "order_file_path": order_data.file_path,
            "bus_file_path": bus_data.file_path,
        }

def build_simulator_command(context, task_log_dir, task_id) -> list[str]:
    """
    拼接命令行指令
    params:
     - context: 数据库所读参数
     - task_log_dir: Celery task日志
     - task_id: Celery task ID
    """
    running_time = int(float(context["running_time_step"]))
    return [
        str(settings.SIMULATOR_OFFLINE_EXE_PATH),
        f"--simulation_id={context['simulation_id']}",
        f"--map={to_backend_abs_path(context['map_file_path'])}",
        f"--walk_links={to_backend_abs_path(context['walk_links_file_path'])}",
        f"--stops={to_backend_abs_path(context['stop_file_path'])}",
        f"--signal={to_backend_abs_path(context['signal_file_path'])}",
        f"--walk_signals={to_backend_abs_path(context['walk_signals_file_path'])}",
        f"--buses={to_backend_abs_path(context['bus_file_path'])}",
        f"--orders={to_backend_abs_path(context['order_file_path'])}",
        f"--log_path={to_backend_abs_path(task_log_dir)}",
        f"--running_time={running_time}",
        f"--use_random_match={str(context['use_random_match']).lower()}",
        f"--use_cost={str(context['use_cost']).lower()}",
        f"--log_path={task_log_dir}",
        f"--log_name={task_id}",
        "--log_path_with_timestamp=false",
        "--progress_interval=10",
    ]

def to_backend_abs_path(path_value: str | Path) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str((settings.BASE_DIR / path).resolve())

@celery_app.task(bind=True)
def run_offline_simulation_task(
    self,
    simulation_id: int
):
    """
    拿task_id,创建该task的任务日志，更新数据库状态为RUNNING，
    读取数据库上下文，拼接simulator_offline.exe命令,
    读取stdout / sterr 写入文件
    subprocess.run(...)，并根据returncode更新COMPLETED / FAILED,超时则更新FAILED
    :param self:
    :param simulation_id:
    :return:
    """
    task_id = str(self.request.id)
    task_log_dir = Path(to_backend_abs_path(settings.SIMULATION_LOG_ROOT / "simulator" / task_id))
    stdout_path = task_log_dir / "stdout.log"
    stderr_path = task_log_dir / "stderr.log"

    update_simulation_status(
        simulation_id=simulation_id,
        status="RUNNING",
    )


    context = load_simulation_context(simulation_id)
    cmd = build_simulator_command(
        context=context,
        task_log_dir=task_log_dir,
        task_id=task_id
    )

    timeout_seconds = settings.SIMULATOR_PROCESS_TIMEOUT_SECONDS

    #环境变量
    env = os.environ.copy()
    env["SIM_CACHE"] = str(task_log_dir)

    try:
        with stdout_path.open("w", encoding='utf-8') as stdout_file, \
             stderr_path.open("w", encoding='utf-8') as stderr_file:
                result = subprocess.run(
                    cmd,
                    cwd=str(settings.SIMULATOR_OFFLINE_EXE_PATH.parent),
                    env=env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=timeout_seconds,
                    check=False
                )

                if result.returncode == 0:
                    update_simulation_status(
                        simulation_id=simulation_id,
                        status="COMPLETED",
                        end_time=datetime.utcnow(),
                    )

                    return {
                        "simulation_id": simulation_id,
                        "task_id": task_id,
                        "status": "COMPLETED",
                        "returncode": result.returncode,
                        "log_path": str(task_log_dir),
                    }

                error_message = f"仿真器返回了错误的返回码:{result.returncode}"
                update_simulation_status(
                    simulation_id=simulation_id,
                    status="FAILED",
                    description=error_message,
                    end_time=datetime.utcnow(),
                )

                raise RuntimeError(error_message)

    except subprocess.TimeoutExpired as e:
        error_message = f"仿真器运行超时了"
        update_simulation_status(
            simulation_id=simulation_id,
            status="FAILED",
            description=error_message,
            end_time=datetime.utcnow(),
        )


        raise RuntimeError(error_message) from e

    except Exception as e:
        error_message = f"仿真任务失败:{e}"
        update_simulation_status(
            simulation_id=simulation_id,
            status="FAILED",
            description=error_message,
            end_time=datetime.utcnow(),
        )

        raise