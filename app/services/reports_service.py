import asyncio, pytz, traceback
from app.db.models import Store, StoreHours, StoreStatus, Report
from app.db.database import get_db
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, DateTime
from sqlalchemy.future import select
from pytz import timezone
from app.utils.common import ReportColumnEnum, ReportStatusEnum, pool_size

semaphore = asyncio.Semaphore(pool_size)

# Function to get db
async def generator(report_id: str):

    try:

        stores = None
        
        # Get db session
        async for db in get_db():
            result = await db.execute(select(Report).filter(Report.id == report_id))
            report = result.scalars().first()
            stores = await load_stores(db)
            print(len(stores))

        # Calculate the up/down time for each store concurrently
        tasks = []
        n = 0
        print("started")
        for (store_id, timezone) in stores:
            local_tz = pytz.timezone(timezone) # Get timezone from timezone dict
            # async function to process queries
            tasks.append(
                process_queries(
                    store_id, 
                    report.created_at, 
                    local_tz
                )
            )

        # # Wait for all tasks to complete in parallel
        await asyncio.gather(*tasks)

        # Mark report status as completed
        async for db in get_db():
            result = await db.execute(select(Report).filter(Report.id == report_id))
            report = result.scalars().first()
            report.status = ReportStatusEnum.Completed
            await db.merge(report)
            await db.commit()
            await db.refresh(report)
            print(report.status)


    except Exception as _:
        tb = traceback.format_exc()
        print(tb)


# Load timezones into memory dict
async def load_stores(db: AsyncSession):
    result = await db.execute(select(Store.store_id, Store.timezone_str)) # Get all timezones
    stores_list = result.fetchall()

    stores = [(row.store_id, row.timezone_str) for row in stores_list] # convert into dict
    return stores


# Select all values where timestamp >= current timestamp - 7 days
async def all_status_last_week(store_id: str, current_time: DateTime, local_tz: timezone, db: AsyncSession):

    current_time_local = current_time.astimezone(local_tz) # Convert current time to local timezone
    current_date_local = current_time_local.replace(hour=0, minute=0, second=0, microsecond=0) # Get start of date on which the report was created
    limit_date_local = current_date_local - timedelta(days = 7) # Subtract 7 days, last week
    limit_date = limit_date_local.astimezone(pytz.utc) # Convert local time back to utc for use in filtering queries

    # All status requests within a week from current date grouped by store id
    result = await db.execute(select(StoreStatus.timestamp, StoreStatus.status).filter(StoreStatus.store_id == store_id and StoreStatus.timestamp >= limit_date))
    queries = result.fetchall() 

    return queries


# Filter those status queries from list which are within time range of store hours
async def process_queries(store_id: str, current_time: DateTime, local_tz: timezone):
    
    async with semaphore:
        async for db in get_db():

            queries = await all_status_last_week(store_id, current_time, local_tz, db)

            # Fetch store hours entry
            result = await db.execute(select(StoreHours.day_of_week, StoreHours.start_time_local, StoreHours.end_time_local).filter(
                StoreHours.store_id == store_id
            ))
            store_hours_list = result.fetchall()

            # store_hours as dict
            store_hours = {row.day_of_week: (row.start_time_local, row.end_time_local) for row in store_hours_list}

            for status_query in queries:
                
                query_time_local = status_query.timestamp.astimezone(local_tz) # Convert query time from utc to local time
                day_of_week = query_time_local.weekday() # Get weekday when query was made

                # If query outside service time, skip

                if (
                    day_of_week not in store_hours or
                    query_time_local.time() < store_hours[day_of_week][0] or 
                    query_time_local.time() > store_hours[day_of_week][1]
                ): 
                    continue
            



