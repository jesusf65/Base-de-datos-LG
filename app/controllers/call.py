from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.base import CRUDBase
from app.models.CallModel import CallModel
from app.schemas.call_model import CallModelCreate,CallModelUpdate

class CallController(CRUDBase[CallModel, CallModelCreate, CallModelUpdate]):
    async def create_call(self, data: CallModelCreate, session: Session):
        try:
            self.create(db=session, obj_in=data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hay un error: {str(e)}")
    
call_controller = CallController(CallModel)