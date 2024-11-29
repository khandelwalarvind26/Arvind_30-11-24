import asyncio, traceback
from app.db.models import Store, StoreHours, StoreStatus, Report
from app.db.database import get_db
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, DateTime, literal
from sqlalchemy.future import select
from app.utils.common import ReportColumnEnum, ReportStatusEnum, pool_size, TimeDecrement, StatusEnum
from datetime import datetime
from collections import defaultdict
from typing import Optional
from zoneinfo import ZoneInfo

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

        # Calculate the up/down time for different stores concurrently
        tasks = []
        start_time = datetime.now()
        print("Running...")

        for (store_id, timezone) in stores:

            # async function to process queries
            # tasks.append(
            await process_queries(
                store_id, 
                report.created_at, 
                timezone
            )
            # )

        # Wait for all tasks to complete in parallel
        # await asyncio.gather(*tasks)

        # log time
        end_time = datetime.now()
        print((end_time - start_time).total_seconds())

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

    default_timezone = 'America/Chicago'

    query = select(
        StoreStatus.store_id,
        func.coalesce(Store.timezone_str, literal(default_timezone)).label('timezone')
    ).join(Store, StoreStatus.store_id==Store.store_id, isouter=True).distinct(StoreStatus.store_id)

    result = await db.execute(query) # Get all timezones
    stores_list = result.fetchall()

    stores = [(row.store_id, row.timezone) for row in stores_list] # convert into dict
    return stores


# Select all values where timestamp >= current timestamp - 7 days
async def all_status_last_week(store_id: str, current_time: DateTime, db: AsyncSession):

    limit_time = current_time - timedelta(days = 7) # Subtract 7 days, last week

    # All status requests within a week from current date and not later then current_time
    result = await db.execute(select(StoreStatus.timestamp, StoreStatus.status).filter(
        StoreStatus.store_id == store_id, 
        StoreStatus.timestamp >= limit_time, 
        StoreStatus.timestamp <= current_time
    ).order_by(StoreStatus.timestamp))

    queries = result.fetchall()

    return queries


# Fetch store hours dict from store_id
async def fetch_store_hours(store_id: str, db: AsyncSession):
    result = await db.execute(select(StoreHours.day_of_week, StoreHours.start_time_local, StoreHours.end_time_local).filter(
        StoreHours.store_id == store_id
    ))
    store_hours_list = result.fetchall()

    store_hours = defaultdict(list)

    for row in store_hours_list:
        store_hours[row.day_of_week].append((row.start_time_local, row.end_time_local))

    return store_hours


# Check whether given timestamp is in store hours
def is_in_store_hours(timestamp: datetime, store_hours: dict):

    day_of_week = timestamp.weekday()

    if day_of_week not in store_hours:
        return False
    
    for store_hour in store_hours[day_of_week]:
        if timestamp.time() >= store_hour[0] and timestamp.time() <= store_hour[1]:
            return store_hour
    
    return False


# Process Individual query to get last week, day and hour times
def process_query(report: list, query_time_local: datetime, store_hours: tuple, limit_time: dict, last_timestamp: Optional[datetime], last_status: StatusEnum):
    

    if last_timestamp is None:
        last_timestamp = store_hours[0]

    minutes = (query_time_local - last_timestamp).total_seconds()/60

    return report


# Process ending query, last query before store closed
def process_ending_query(report: list, store_hours: tuple, limit_time: dict, last_timestamp: Optional[datetime], last_status: StatusEnum):

    return report


# Filter those status queries from list which are within time range of store hours
async def process_queries(store_id: str, current_time: DateTime, timezone):
    
    async with semaphore:
        async for db in get_db():
            
            # Query 
            time_limit = (
                current_time - timedelta(days = 7),
                current_time - timedelta(days = 1),
                current_time - timedelta(hours = 1),
            )

            # Fetch queries
            queries = await all_status_last_week(store_id, current_time, db)

            # Fetch store hours dict
            store_hours = await fetch_store_hours(store_id, db)

            report = [0, 0, 0, 0, 0, 0]

            last_status = StatusEnum.active
            last_timestamp = None
            active = False

            # Iterate over all queries and compute
            for status_query in queries:
                
                query_time_local = status_query.timestamp.astimezone(ZoneInfo(timezone)) # Convert query time from utc to local time

                # If query outside service time, skip
                store_hour = is_in_store_hours(query_time_local, store_hours)

                if store_hour is not False and status_query.status == StatusEnum.active:
                    active = True

                if store_hour is not False:
                    if (
                        last_timestamp is not None and 
                        ( 
                            last_timestamp.time() < store_hour[0] or 
                            last_timestamp.time() > store_hour[1] or
                            last_timestamp.weekday() != query_time_local.weekday()
                        )
                    ):
                        last_store_hour = is_in_store_hours(last_timestamp, store_hours)
                        report = process_ending_query(report, last_store_hour, time_limit, last_timestamp, last_status)
                        last_timestamp = None
                        last_status = StatusEnum.active

                    report = process_query(report, query_time_local, store_hour, time_limit, last_timestamp, last_status)
                    last_status = status_query.status
                    last_timestamp = query_time_local
                else:
                    if last_timestamp is not None:
                        report = process_ending_query()
                    last_status = StatusEnum.active
                    last_timestamp = None
                
            if not active:
                if len(queries) != 0:
                    print(store_id)
