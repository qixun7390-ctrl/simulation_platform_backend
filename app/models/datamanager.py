from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.database import Base

class Area(Base):
    """
    区域模型,上传新地图即创建新区域
    """
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(primary_key=True,index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100),nullable=False,index=True)
    slug: Mapped[str] = mapped_column(String(100),unique=True,nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    #唯一数据:地图和信号灯，
    map_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    signal_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    border_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    walk_links_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=False)
    walk_signals_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,nullable=False)

    stops: Mapped[list["StopData"]] = relationship(back_populates="area")
    orders: Mapped[list["OrderData"]] = relationship(back_populates="area")
    buses: Mapped[list["BusData"]] = relationship(back_populates="area")

class StopData(Base):
    """
    公交站点数据文件模型,
    一个区域可以有多个站点文件
    """
    __tablename__ = "stop_data"
    id: Mapped[int] = mapped_column(primary_key=True,index=True,autoincrement=True)
    area_id: Mapped[int] = mapped_column(
        ForeignKey("areas.id"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(150),nullable=False,index=True)
    file_path: Mapped[str] = mapped_column(String(1024),nullable=False)
    description: Mapped[str | None] = mapped_column(String(255),nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,nullable=False)

    area: Mapped["Area"] = relationship(back_populates="stops")
    linked_orders: Mapped[list["OrderData"]] = relationship(back_populates="linked_stops")

class OrderData(Base):
    __tablename__ = "order_data"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    area_id: Mapped[int] = mapped_column(
        ForeignKey("areas.id"),
        nullable=False,
        index=True
    )

    linked_stops_id: Mapped[int] = mapped_column(
        ForeignKey("stop_data.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255),nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    area: Mapped["Area"] = relationship(back_populates="orders")
    linked_stops: Mapped["StopData"] = relationship(back_populates="linked_orders")


class BusData(Base):
    __tablename__ = "bus_data"
    id: Mapped[int]  = mapped_column(primary_key=True, index=True, autoincrement=True)
    area_id: Mapped[int] = mapped_column(
        ForeignKey("areas.id"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    area: Mapped["Area"] = relationship(back_populates="buses")
