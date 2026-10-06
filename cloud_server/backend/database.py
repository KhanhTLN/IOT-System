import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Nạp các biến môi trường từ file .env ở thư mục gốc hoặc thư mục hiện tại
load_dotenv()

# Lấy DATABASE_URL từ biến môi trường .env (mặc định SQLite nếu chưa cấu hình)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./iot_sorting.db"
)

# SQLite hoặc PostgreSQL Engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
