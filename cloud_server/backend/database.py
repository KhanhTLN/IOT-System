import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Lấy DATABASE_URL từ biến môi trường (mặc định SQLite cho test local, Docker sẽ override PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./iot_sorting.db"
)

# SQLite hỗ trợ test nhanh nếu không có Postgres local
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
