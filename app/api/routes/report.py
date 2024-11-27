from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Report, ReportStatusEnum
from app.services.reports_service import generator

router = APIRouter()

# API for triggering a new report generation
@router.post("/trigger")
async def trigger_report(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        report = Report(status=ReportStatusEnum.Running)
        db.add(report)
        await db.commit()
        await db.refresh(report)
        background_tasks.add_task(generator(report))
        return report.id
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error" + str(e)
        )

    finally:
        db.close()


# API for fetching actual report
@router.get("/get")
async def get_report(id: str, db: AsyncSession = Depends(get_db)):
    try:
        report = db.query(Report).filter(Report.id == id).first()

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
            detail="Internal Server Error" + str(e)
        )
    
    finally:
        db.close()