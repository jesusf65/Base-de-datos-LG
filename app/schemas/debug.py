
from pydantic import BaseModel

class debugBase(BaseModel):
    key: str
    command: str

class debugKey(BaseModel):
    key: str