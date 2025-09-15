from fastapi import Request, Depends
from src.session.manager import SessionManager  # or wherever it's defined

# Dependency to extract session from app.state
def get_session(request: Request) -> SessionManager:
    return request.app.state.session