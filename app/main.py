from fastapi import FastAPI
from app.api.routes import report
from app.db.database import create_tables

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await create_tables()

app.include_router(report.router, prefix="/report")