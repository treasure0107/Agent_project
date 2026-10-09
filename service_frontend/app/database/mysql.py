"""
MySQL数据库连接配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings

# 创建 MySQL 数据库连接引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 创建数据库会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 创建 ORM 模型基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话
    """
    # 创建一个新的数据库会话实例
    db = SessionLocal()
    try:
        # 将数据库会话对象返回给调用者（路由函数）
        yield db
    finally:
        # 关闭数据库会话，释放连接回连接池
        db.close()