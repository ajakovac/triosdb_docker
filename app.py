from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

from routes import login, command, upload
from configs.settings import settings
from session.manager import SessionManager




@asynccontextmanager
async def lifespan(app: FastAPI):
    session = SessionManager()
    session.start()
    app.state.session = session
    print("🔐 Lifespan start")
    yield
    session.stop()
    print("🔓 Lifespan end")

app = FastAPI(title="triosdb", version="0.1.0")

# Health check endpoint
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# CORS settings
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
app.router.lifespan_context = lifespan

