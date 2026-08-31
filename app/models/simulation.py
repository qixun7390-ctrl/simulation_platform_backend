from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.database import Base
class Simulation(Base):
    """
    代表一次独立的仿真运行
    """

    __tablename__ = "simulations"

    # 仿真运行ID
    id: Mapped[int] = mapped_column(primary_key=True,nullable=False,autoincrement=True)
    # 仿真运行名称
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    # 仿真类型：离线仿真、在线仿真、用户上传日志
    type: Mapped[str] = mapped_column(String(255), nullable=False, default="offline")
    # 仿真运行描述
    description: Mapped[str | None] = mapped_column(String(1024),nullable=True)
    # 仿真运行创建时间
    created_time: Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow,nullable=False)
    # 仿真运行结束时间
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 仿真运行时间步
    running_time_step: Mapped[float] = mapped_column(Float, nullable=False, default=3600.0)

    # 仿真运行布尔值参数
    use_random_match: Mapped[bool] = mapped_column(Boolean,nullable=False,default=False)
    use_cost: Mapped[bool] = mapped_column(Boolean,nullable=False,default=False)

    # 仿真运行各数据文件
    area_data_id: Mapped[int] = mapped_column(ForeignKey("areas.id"), nullable=False, index=True)
    order_data_id: Mapped[int] = mapped_column(ForeignKey("order_data.id"), nullable=False, index=True)
    stop_data_id: Mapped[int] = mapped_column(ForeignKey("stop_data.id"), nullable=False, index=True)
    bus_data_id: Mapped[int] = mapped_column(ForeignKey("bus_data.id"), nullable=False, index=True)

    # 在线仿真参数
    status: Mapped[str] = mapped_column(String(255), nullable=False, default="PENDING")

    #仿真日志管理
    log_path: Mapped[str | None] = mapped_column(String(1024),nullable=True)
    log_name: Mapped[str | None] = mapped_column(String(255),nullable=True)