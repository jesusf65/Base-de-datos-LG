from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.base import CRUDBase
from app.models.CallCrm import CallCrm
from app.schemas.call_crm import CallCrmCreate,CallCrmUpdate

class CallController(CRUDBase[CallCrm, CallCrmCreate, CallCrmUpdate]):
    async def create_call(self, data: CallCrmCreate, session: Session):
        try:
            calls = self.create(db=session, obj_in=data)
            return calls
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hay un error: {str(e)}")
    
call_controller = CallController(CallCrm)