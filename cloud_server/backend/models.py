import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base

class SortingLog(Base):
    __tablename__ = "sorting_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    color_label = Column(String(20), nullable=False, index=True)  # RED, YELLOW, GREEN
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "color_label": self.color_label,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
