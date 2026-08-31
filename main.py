from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.database import init_db, close_db
from app.api.datamanager import router as datamanager_router
from app.api.simulation import router as simulation_router
from app.api.logs import router as logs_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(
    title="Simple Simulation Platform",
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(datamanager_router,prefix="/api")
app.include_router(simulation_router,prefix="/api")
app.include_router(logs_router,prefix="/api")