import traceback, asyncio
from app.db.models import Store, StoreStatus, Report
from app.db.database import get_db
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, literal
from sqlalchemy.future import select
from app.utils.common import ReportStatusEnum, semaphore
from datetime import datetime
from app.services.store_service import StoreService 
from app.services.file_service import csv_writer 
from app.utils.logger import logger

# Function to get db
async def generator(report_id: str):

    try:
        time0 = datetime.now()

        #### Step 1
        logger.info(f"{report_id} : Fetch stores and queries from db")
        stores_list, queries, created_at = await fetch_stores_and_queries(report_id)
        time1 = datetime.now()
        logger.info(f"{report_id} : Done fetching {(time1 - time0).total_seconds()}")

        #### Step 2
        logger.info(f"{report_id} : Initializing store objects")
        stores = await initialize_store_objects(stores_list, created_at)
        time2 = datetime.now()
        logger.info(f"{report_id} : Done Initializing store objects {(time2 - time1).total_seconds()}")

        #### Step 3
        logger.info(f"{report_id} : Processing {len(queries)} queries sequentially")

        for query in queries:
            stores[query.store_id].process_query(query)

        time3 = datetime.now()
        logger.info(f"{report_id} : Finished processing queries {(time3 - time2).total_seconds()}")

        #### Step 4
        logger.info(f"{report_id} : Generating csv report")
        path = await csv_writer(report_id, stores)
        time4 = datetime.now()
        logger.info(f"{report_id} : Finished generating report {(time4 - time3).total_seconds()}")

        #### Step 5
        logger.info(f"{report_id} : Changing report in db")
        await finalize_report(report_id, path)
        time5 = datetime.now()
        logger.info(f"{report_id} : Finished changing report in db {(time5 - time4).total_seconds()}")

        logger.info(f"{report_id} : Total time: {(time5 - time0).total_seconds()}")

    except Exception as _:
        tb = traceback.format_exc()
        logger.error(tb)


# Abstraction function to make final changes to report
async def finalize_report(report_id: str, path):

    # Mark report status as completed
    async with semaphore:
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


# Abstraction function for initializing a dict of store_id: store_obj
async def initialize_store_objects(stores_list: list, created_at: datetime):

    stores = {}
    tasks = []
    for store in stores_list:
        store_obj = StoreService(store.store_id, created_at, store.timezone)
        stores[store.store_id] = store_obj
        tasks.append(store_obj.load_store_hours())
    
    await asyncio.gather(*tasks)

    return stores


# Abstraction function for stores and queries
async def fetch_stores_and_queries(report_id: str):

    async with semaphore:
        async for db in get_db():
            result = await db.execute(select(Report).filter(Report.id == report_id))
            report = result.scalars().first()
            stores_list = await fetch_stores(db, report.created_at)
            queries = await fetch_queries(db, report.created_at)
            
            return stores_list, queries, report.created_at


# Load timezones into memory
async def fetch_stores(db: AsyncSession, created_at: datetime):

    default_timezone = 'America/Chicago'

    time_limit = created_at - timedelta(days=7)

    query = select(
        StoreStatus.store_id,
            func.coalesce(
                Store.timezone_str, 
                literal(default_timezone)
            ).label('timezone')
        ).filter(
            StoreStatus.timestamp >= time_limit, 
            StoreStatus.timestamp <= created_at
        ).join(
            Store, 
            StoreStatus.store_id==Store.store_id, 
            isouter=True
        ).distinct(StoreStatus.store_id)

    result = await db.execute(query) # Get all timezones
    stores_list = result.fetchall()

    return stores_list


# Select all values where timestamp >= current timestamp - 7 days
async def fetch_queries(db: AsyncSession, created_at: datetime):

    time_limit = created_at - timedelta(days=7)

    # All status requests within a week from current date and not later then current_time
    result = await db.execute(select(StoreStatus.store_id, StoreStatus.timestamp, StoreStatus.status).filter(
        StoreStatus.timestamp >= time_limit, 
        StoreStatus.timestamp <= created_at
    ).order_by(StoreStatus.timestamp))

    queries = result.fetchall()

    return queries