from sqlalchemy import Column, Integer, String, CHAR, ForeignKey, DateTime, CheckConstraint, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum, uuid

Base = declarative_base()

class StatusEnum(enum.Enum):
    active = "active"
    inactive = "inactive"

class ReportStatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"

class Store(Base):
    __tablename__ = "stores"

    store_id = Column(CHAR(36), primary_key=True, index=True)  # Primary key
    timezone_str = Column(String, nullable=False)


class StoreHours(Base):
    __tablename__ = "store_hours"

    id = Column(Integer, primary_key=True, index=True)  # Primary key
    store_id = Column(CHAR(36), ForeignKey('stores.store_id', ondelete='CASCADE'), nullable=False)
    day_of_week = Column(Integer, CheckConstraint('day_of_week >= 0 AND day_of_week <= 6'))
    start_time_local = Column(DateTime, nullable=False)
    end_time_local = Column(DateTime, nullable=False)


class StoreStatus(Base):
    __tablename__ = "store_status"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(CHAR(36), ForeignKey('stores.store_id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String, nullable=True)
    status = Column(Enum(ReportStatusEnum), nullable=False)
    created_at = Column(DateTime, default=func.now())


