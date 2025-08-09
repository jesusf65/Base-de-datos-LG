from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TimingData(BaseModel):
    contact_creation: Optional[str]
    first_call: Optional[str]
    time_between_minutes: Optional[float]
    contact_id: Optional[str]

class WebhookResponse(BaseModel):
    status: str
    message: str
    timing_data: TimingData
    call_count: int