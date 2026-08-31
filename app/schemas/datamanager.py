from pydantic import BaseModel, ConfigDict

class AreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None = None
    map_file:str
    signal_file:str
    border_file: str | None = None
    walk_links_file: str
    walk_signals_file: str
    created_at:str

class StopDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    area: int
    name: str
    file: str
    description: str | None = None
    created_at: str

class OrderDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    area: int
    linked_stops: int
    file: str
    description: str | None = None
    created_at: str

class BusDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    area: int
    file: str
    description: str | None = None
    created_at: str