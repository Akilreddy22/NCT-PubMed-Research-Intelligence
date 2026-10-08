"""Pydantic models = the shape of JSON that the browser must send. FastAPI validates them for us."""
from pydantic import BaseModel


class NCTFetchRequest(BaseModel):
    url: str


class NCTCompareVersionsRequest(BaseModel):
    nct_id: str
    from_version: int
    to_version: int
