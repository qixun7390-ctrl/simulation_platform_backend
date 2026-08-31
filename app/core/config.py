from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/simple_sim_platform"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/simple_sim_platform"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    STORAGE_ROOT: Path = Path('data')
    SIMULATOR_OFFLINE_EXE_PATH: Path = Path(r"E:\simulator\simulator_bin\simulator_offline.exe")
    SIMULATION_LOG_ROOT: Path = Path("logs")

    #鉴权
    API_TOKEN: str = ""
    #文件绝对路径设置
    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    #仿真器的最大运行时间
    SIMULATOR_PROCESS_TIMEOUT_SECONDS: int = 600

    #任务队列存任务消息(/0) / 存任务结果(/1)
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()