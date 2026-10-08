from typing import Optional

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    pmid: Optional[str] = None       # analyze a stored article ...
    abstract: Optional[str] = None   # ... or just some pasted text


class FiguresRequest(BaseModel):
    pmid: str


class FigureAnalyzeRequest(BaseModel):
    figure_id: int
