import uvicorn
from fastapi import FastAPI

from src.core.config import settings

app = FastAPI(title="Session-Auth-Service")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.runtime.host,
        port=settings.runtime.port,
        reload=settings.runtime.reload,
    )
