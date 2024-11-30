from app.api.routes import report
from app.db import create_tables

from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await create_tables()

app.include_router(report.router, prefix="/report")