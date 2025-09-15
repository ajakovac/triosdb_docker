import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from api.dependencies import get_session
from src.session.manager import SessionManager

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post(f"/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: SessionManager = Depends(get_session)):
    login = session.login(form_data.username, form_data.password)
    if login is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return login

@router.get(f"/status")
async def user_server_status_endpoint():
    return {"user server status": True}

@router.get(f"/validate")
async def read_users_me(
    token: str = Depends(oauth2_scheme),
    session: SessionManager = Depends(get_session)):
    username = session.get_user_by_token(token)
    if username:
        return {"username": username}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post(f"/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    session: SessionManager = Depends(get_session)):
    username = session.logout(token)
    if username:
        return {"message": f'{username} logged out'}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/healthz")
def healthz():
    return {"status": "ok"}