import traceback, asyncio
from app.db.models import Store, StoreStatus, Report
from app.db.database import get_db
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, literal
from sqlalchemy.future import select
from app.utils.common import ReportStatusEnum
from datetime import datetime
from app.services.store_service import StoreService 
from app.services.file_service import csv_writer 

# Function to get db
async def generator(report_id: str):

    try:

        stores = None
        
        # Get db session
        async for db in get_db():
            result = await db.execute(select(Report).filter(Report.id == report_id))
            report = result.scalars().first()
            stores = await load_stores(db)

        # Calculate the up/down time for different stores concurrently
        tasks = []
        time0 = datetime.now()
        print("Running...")
        store_objs = []

        for (store_id, timezone) in stores:

            store = StoreService(store_id, report.created_at, timezone)
            # async function to process queries
            store_objs.append(store)
            tasks.append(store.process())

        # Wait for all tasks to complete in parallel
        await asyncio.gather(*tasks)

        # log time
        time1 = datetime.now()
        print("Finished calculation, generating report", (time1 - time0).total_seconds())

        # write to csv
        path = await csv_writer(report_id, store_objs)
        time2 = datetime.now()
        print("Finished generating report", (time2 - time1).total_seconds())

        # Mark report status as completed
        async for db in get_db():

            # Fetch report
            result = await db.execute(select(Report).filter(Report.id == report_id))
            report = result.scalars().first()

            # Make changes to report
            report.status = ReportStatusEnum.Completed
            report.file_path = path

            # Commit
            await db.merge(report)
            await db.commit()

    except Exception as _:
        tb = traceback.format_exc()
        print(tb)


# Load timezones into memory dict
async def load_stores(db: AsyncSession):

    default_timezone = 'America/Chicago'

    query = select(
        StoreStatus.store_id,
        func.coalesce(Store.timezone_str, literal(default_timezone)).label('timezone')
    ).join(Store, StoreStatus.store_id==Store.store_id, isouter=True).distinct(StoreStatus.store_id)

    result = await db.execute(query) # Get all timezones
    stores_list = result.fetchall()

    stores = [(row.store_id, row.timezone) for row in stores_list] # convert into dict
    return stores