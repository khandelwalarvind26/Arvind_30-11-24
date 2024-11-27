from app.db.models import Store, StoreHours, StoreStatus, Report
from app.db.database import get_db


async def generator(report: Report):

    try:

        db = await get_db()
        # db.query(StoreStatus)

    except Exception as e:
        return e
    