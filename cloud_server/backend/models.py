import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from database import Base

def get_vietnam_time():
    """Lấy thời gian chuẩn Việt Nam (GMT+7)"""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=7)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="WORKER")  # WORKER, MANAGER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_vietnam_time, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SortingLog(Base):
    __tablename__ = "sorting_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    color_label = Column(String(20), nullable=False, index=True)  # RED, YELLOW, GREEN
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=get_vietnam_time, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "color_label": self.color_label,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=get_vietnam_time, onupdate=get_vietnam_time)

