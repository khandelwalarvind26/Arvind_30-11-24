from app.db.models import Report
from app.db.database import get_db
from app.utils.common import semaphore, ReportStatusEnum, ReportColumnEnum

from sqlalchemy.future import select

import io, csv

# Function to write all reports to csv file
async def csv_writer(report_id: str, stores: dict):

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)

    # Write headings
    headings = [
        'store_id', 
        'uptime_last_hour', 
        'uptime_last_day', 
        'update_last_week', 
        'downtime_last_hour', 
        'downtime_last_day', 
        'downtime_last_week'
    ]

    writer.writerow(headings)

    # Write data
    for _, store in stores.items():
        data = [
            store.store_id,
            store.report[ReportColumnEnum.uptime_last_hour.value],
            store.report[ReportColumnEnum.uptime_last_day.value]/60,
            store.report[ReportColumnEnum.uptime_last_week.value]/60,
            store.report[ReportColumnEnum.downtime_last_hour.value],
            store.report[ReportColumnEnum.downtime_last_day.value]/60,
            store.report[ReportColumnEnum.downtime_last_week.value]/60,
        ]

        for i in range(1,7):
            data[i] = round(data[i])

        writer.writerow(data)

    csv_bytes = csv_buffer.getvalue().encode('utf-8')

    csv_buffer.close()

    await finalize_report(report_id, csv_bytes)


# Abstraction function to make final changes to report
async def finalize_report(report_id: str, file):

    # Mark report status as completed
    async with semaphore:
        async for db in get_db():

            # Fetch report
            result = await db.execute(select(Report).filter(Report.id == report_id))
            report = result.scalars().first()

            # Make changes to report
            report.status = ReportStatusEnum.Completed
            report.file = file

            # Commit
            await db.merge(report)
            await db.commit()
