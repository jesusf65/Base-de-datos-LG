from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TimingData(BaseModel):
    Call_AIRCALL: Optional[str]
    Call_CRM: Optional[str] 
    date_created: Optional[str]
    time_between_minutes: Optional[float]
    contact_id: Optional[str]

class WebhookResponse(BaseModel):
    status: str
    message: str
    timing_data: TimingData
    call_count: int