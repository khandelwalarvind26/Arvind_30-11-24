from app.db import get_db, Report
from app.services import generator
from app.utils import logger, cleanup, ReportStatusEnum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from datetime import datetime
from typing import Optional
import os, traceback

router = APIRouter()


# API for triggering a new report generation
@router.post("/trigger")
async def trigger_report(background_tasks: BackgroundTasks, timestamp: Optional[datetime] = None, db: AsyncSession = Depends(get_db)):
    try:
        
        report = Report(status=ReportStatusEnum.Running)

        if timestamp is not None:
            report.created_at = timestamp

        db.add(report)
        await db.commit()
        await db.refresh(report)
        background_tasks.add_task(generator, report.id)
        return report.id
    
    except Exception as _:
        tb = traceback.format_exc()
        logger.error(tb)
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        await db.close()


# API for fetching actual report
@router.get("/get")
async def get_report(id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Report).filter(Report.id == id))
        report = result.scalars().first()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        if report.status == ReportStatusEnum.Running:
            return ReportStatusEnum.Running
        
        # Save the BLOB content as a temporary CSV file
        current_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        file_path = os.path.join(current_path, f"{report.id}.csv")
        with open(file_path, "wb") as f:
            f.write(report.file)

        # Executed only after response is sent
        background_tasks.add_task(cleanup, file_path)

        # Return the CSV file as a response
        return FileResponse(
            path=file_path,
            media_type="text/csv",
            filename=f"{report.id}.csv"
        )

    except Exception as _:
        tb = traceback.format_exc()
        logger.error(tb)
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )
    
    finally:
        await db.close()