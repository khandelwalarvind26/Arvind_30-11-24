from sqlalchemy import Column, Integer, String, CHAR, DateTime, CheckConstraint, Enum, Time, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from app.utils.common import StatusEnum, ReportStatusEnum


Base = declarative_base()

class Store(Base):
    __tablename__ = "stores"

    store_id = Column(CHAR(36), primary_key=True, index=True)  # Primary key
    timezone_str = Column(String, nullable=False)


class StoreHours(Base):
    __tablename__ = "store_hours"

    id = Column(Integer, primary_key=True, index=True)  # Primary key
    store_id = Column(CHAR(36), nullable=False)
    day_of_week = Column(Integer, CheckConstraint('day_of_week >= 0 AND day_of_week <= 6'))
    start_time_local = Column(Time, nullable=False)
    end_time_local = Column(Time, nullable=False)


class StoreStatus(Base):
    __tablename__ = "store_status"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(CHAR(36), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file = Column(LargeBinary, nullable=True)
    status = Column(Enum(ReportStatusEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


