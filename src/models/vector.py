from typing import List, Dict, Any
from pydantic import BaseModel

class VectorRecord(BaseModel):
    id: str
    values: List[float]
    metadata: Dict[str, Any]

class SearchResult(BaseModel):
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]
