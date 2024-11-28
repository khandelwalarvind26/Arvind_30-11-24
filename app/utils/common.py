import enum

pool_size = 10

class StatusEnum(enum.Enum):
    active = "active"
    inactive = "inactive"

class ReportStatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"

class ReportColumnEnum(enum.Enum):
    uptime_last_hour = 0
    uptime_last_day = 1
    uptime_last_week = 2
    downtime_last_hour = 3
    downtime_last_day = 4
    downtime_last_week = 5