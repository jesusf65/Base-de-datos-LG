from app.models.CallModel import CallModel
from app.core.database import get_session

class CallSaveController:
    async def save_call_from_webhook(self,call_id, first_name, last_name, phone_number):
        async for session in get_session():  # get_session es async generator
            call = CallModel(
                call_id=call_id,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number
            )
            session.add(call)
            await session.commit()

call__save_controller = CallSaveController()