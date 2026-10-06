from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# --- User Schemas ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=6, description="Mật khẩu tối thiểu 6 ký tự")
    full_name: Optional[str] = Field(default="", description="Họ và tên")
    role: str = Field(default="WORKER", description="Role: WORKER hoặc MANAGER")

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Sorting Log Schemas ---
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

# --- Config Schemas ---
class ConfigUpdate(BaseModel):
    key: str
    value: str
