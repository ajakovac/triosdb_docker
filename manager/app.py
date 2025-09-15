from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from routes import login, command, upload

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.session import *

@asynccontextmanager
async def lifespan(app: FastAPI):
    session = SessionManager()
    session.start()
    app.state.session = session
    print("🔐 Lifespan start")
    yield
    session.stop()
    print("🔓 Lifespan end")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins= ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(login.router)
app.include_router(command.router)
app.include_router(upload.router)


