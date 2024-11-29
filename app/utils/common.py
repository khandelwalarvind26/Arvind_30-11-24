from app.core.config import settings
import enum, asyncio

semaphore = asyncio.Semaphore(settings.POOL_SIZE)

class StatusEnum(enum.Enum):
    active = "active"
    inactive = "inactive"

class ReportStatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"

class ReportColumnEnum(enum.Enum):
    uptime_last_week = 0
    uptime_last_day = 1
    uptime_last_hour = 2
    downtime_last_week = 3
    downtime_last_day = 4
    downtime_last_hour = 5

class TimeDecrement(enum.Enum):
    week = 0
    day = 1
    hour = 2