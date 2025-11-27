from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os

# MySQL 配置（默认本机环回，可通过环境变量覆盖，例如在 Ubuntu 虚拟机里用 192.168.44.1 访问宿主机）
DB_HOST = os.getenv("DB_HOST") or "127.0.0.1"
DB_USER = os.getenv("DB_USER") or "root"
DB_PASSWORD = os.getenv("DB_PASSWORD") or "yyr0218..."
DB_NAME = os.getenv("DB_NAME") or "network_management"

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 断线自动重连探活
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 统一使用 models.py 中的 Base
from models import Base  # noqa: E402


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
