from app.api.routes import report
from app.db import create_tables
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await create_tables()
    yield  # The point at which the application runs


app = FastAPI(lifespan=lifespan)

app.include_router(report.router, prefix="/report")