from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class SortingLogCreate(BaseModel):
    color_label: str = Field(..., description="Nhãn màu: RED, YELLOW, hoặc GREEN")
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Độ tin cậy từ 0.0 đến 1.0")

class SortingLogResponse(BaseModel):
    id: int
    color_label: str
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True
