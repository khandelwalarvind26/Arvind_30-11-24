from datetime import datetime, timedelta, time
from app.db.database import get_db
from app.utils.common import StatusEnum, downtime_offset
from app.db.models import StoreHours
from sqlalchemy.future import select
from collections import defaultdict
from zoneinfo import ZoneInfo
from app.utils.common import semaphore

class StoreService:

    def __init__(self, store_id: str, created_at: datetime, timezone: str):
        self.store_id = store_id
        self.timezone = timezone
        self.created_at = created_at
        self.report = [0, 0, 0, 0, 0, 0]
        self.time_limit = (
            created_at - timedelta(days = 7),
            created_at - timedelta(days = 1),
            created_at - timedelta(hours = 1),
        )
        self.last_timestamp = None
        self.last_status = StatusEnum.active
        self.store_hours = None
    

    # Fetch store hours dict from store_id
    async def load_store_hours(self):
        
        result = None

        async with semaphore:
            async for db in get_db():

                result = await db.execute(select(StoreHours.day_of_week, StoreHours.start_time_local, StoreHours.end_time_local).filter(
                    StoreHours.store_id == self.store_id
                ))
            
        store_hours_list = result.fetchall()

        store_hours = defaultdict(list)

        for row in store_hours_list:
            store_hours[row.day_of_week].append((row.start_time_local, row.end_time_local))

        self.store_hours = store_hours


    # Check whether given timestamp is in store hours
    def is_in_store_hours(self, timestamp: datetime):

        day_of_week = timestamp.weekday()

        if day_of_week not in self.store_hours:
            return False
        
        for store_hour in self.store_hours[day_of_week]:
            if timestamp.time() >= store_hour[0] and timestamp.time() <= store_hour[1]:
                return store_hour
        
        return False


    # Get a query and last processed query and determine if the store has closed in between
    def is_different_store_hour(self, store_hour: tuple, current_timestamp: datetime):
        if (
            self.last_timestamp is not None and 
            ( 
                self.last_timestamp.time() < store_hour[0] or 
                self.last_timestamp.time() > store_hour[1] or
                self.last_timestamp.weekday() != current_timestamp.weekday()
            )
        ):
            return True
        return False


    # Add uptime between two timestamps
    def add_time(self, last_time: datetime, current_time: datetime, status: StatusEnum):

        last_timestamp_temp = last_time

        # Debug query
        # print(last_time.strftime("%Y-%m-%d %H:%M:%S"), current_time.strftime("%Y-%m-%d %H:%M:%S"), status)

        r = range(3) if status == StatusEnum.active else range(3,6)
        for i in r:
            if current_time >= self.time_limit[i%3]:
                # If not entire time till last_timestamp to be included in calc
                if self.time_limit[i%3] > last_timestamp_temp:
                    last_timestamp_temp = self.time_limit[i%3]

                minutes = (current_time - last_timestamp_temp).total_seconds()/60
                self.report[i] += minutes

            else:
                break


    # Takes an input of a time and a datetime object with timezone, adds date and timezone to time object
    def combine_timestamps(self, t: time, dt: datetime):
        return dt.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=t.microsecond)


    # Process Individual query to get last week, day and hour times
    def process_query_helper(self, current_timestamp: datetime, current_status: StatusEnum, store_hours: tuple):
        
        # If start of new store_hour range, then give last_timestamp as start of store_hour
        if self.last_timestamp is None:
            self.last_timestamp = self.combine_timestamps(store_hours[0], current_timestamp)

        # _, active
        if current_status == StatusEnum.active:

            # inactive, active
            if self.last_status == StatusEnum.inactive:
                
                # Take downtime_offset minutes from last_timestamp as downtime
                mid_time = self.last_timestamp + timedelta(minutes = downtime_offset)

                if mid_time > current_timestamp:
                    mid_time = current_timestamp
                else:
                    # Add uptime between mid_time and current_timestamp
                    self.add_time(mid_time, current_timestamp, StatusEnum.active)
                
                # Add downtime between last_timestamp and mid_time
                self.add_time(self.last_timestamp, mid_time, StatusEnum.inactive)

            # active, active
            else:
                # Add uptime between last_timestamp and current_timestamp
                self.add_time(self.last_timestamp, current_timestamp, StatusEnum.active)
        
        # _, Inactive
        else:

            # Inactive, Inactive
            if self.last_status == StatusEnum.inactive:

                # Entire time between last_timestamp and current_timestamp is inactive
                self.add_time(self.last_timestamp, current_timestamp, StatusEnum.inactive)
            
            # active, inactive
            else :

                # Take last downtime_offset minutes from current_time as downtime
                mid_time = current_timestamp - timedelta(minutes = downtime_offset)

                if mid_time < self.last_timestamp:
                    mid_time = self.last_timestamp
                else :
                    # Add uptime i.e. time between last_timestamp and mid_time
                    self.add_time(self.last_timestamp, mid_time, StatusEnum.active)

                # Add downtime between mid_time and current_timestamp
                self.add_time(mid_time, current_timestamp, StatusEnum.inactive)


    # Process ending query, last query before store closed
    def process_ending_query(self, store_hours: tuple):

        # Add up/down time from last_timestamp to store_hours[1]
        store_end_time = self.combine_timestamps(store_hours[1], self.last_timestamp)
        self.add_time(self.last_timestamp, store_end_time, self.last_status)


    # Process all queries by iterating
    def process_query(self, query):
            
        current_time = query.timestamp.astimezone(ZoneInfo(self.timezone)) # Convert query time from utc to local time

        # If query outside service time, skip
        store_hour = self.is_in_store_hours(current_time)

        if store_hour is not False:

            # If day or time store_hour segment has changed since last processed query
            if (self.is_different_store_hour(store_hour, current_time)):

                last_store_hour = self.is_in_store_hours(self.last_timestamp)
                self.process_ending_query(last_store_hour)
                self.last_timestamp, self.last_status = None, StatusEnum.active
            
            # Debug query
            # print(current_time.strftime("%Y-%m-%d %H:%M:%S"), store_hour[0].strftime("%H:%M:%S"), store_hour[1].strftime("%H:%M:%S"), query.status)

            self.process_query_helper(current_time, query.status, store_hour)
            self.last_timestamp, self.last_status = current_time, query.status
            

