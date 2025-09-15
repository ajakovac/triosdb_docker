from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from api.dependencies import get_session
from src.session.manager import SessionManager
from api.models.response_model import APIResponse
from datetime import datetime
from pydantic import BaseModel
from src.database.triplets import TripletSet

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

class CommandRequest(BaseModel):
    command: str

@router.post("/execute", response_model=APIResponse)
async def execute_command(
    request: CommandRequest,
    token: str = Depends(oauth2_scheme),
    session: SessionManager = Depends(get_session)):

    cmd_response = session.command(request.command, token=token)

    if cmd_response.output is None:
        return APIResponse(
            command=cmd_response.command,
            timestamp=cmd_response.timestamp,
            message=cmd_response.message,
            success=cmd_response.success,
            output= None
        )
    elif isinstance(cmd_response.output, list):
        return APIResponse(
            command=cmd_response.command,
            timestamp=cmd_response.timestamp,
            message=cmd_response.message,
            success=cmd_response.success,
            output= cmd_response.output
        )
    else:
        return APIResponse(
            command=cmd_response.command,
            timestamp=cmd_response.timestamp,
            message=cmd_response.message,
            success=cmd_response.success,
            output= cmd_response.output.show()
        )