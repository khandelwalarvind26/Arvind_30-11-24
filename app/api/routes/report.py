from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models import Report, ReportStatusEnum
from app.services.reports_service import generator
from datetime import datetime
from typing import Optional

router = APIRouter()

# API for triggering a new report generation
@router.post("/trigger")
async def trigger_report(timestamp: Optional[datetime], background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        
        report = Report(status=ReportStatusEnum.Running)

        if timestamp is not None:
            report.created_at = timestamp

        db.add(report)
        await db.commit()
        await db.refresh(report)
        background_tasks.add_task(generator, report.id)
        return report.id
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error " + str(e)
        )

    finally:
        db.close()


# API for fetching actual report
@router.get("/get")
async def get_report(id: str, db: AsyncSession = Depends(get_db)):
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
        else:
            return ReportStatusEnum.Completed

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error " + str(e)
        )
    
    finally:
        db.close()