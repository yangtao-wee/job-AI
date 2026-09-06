from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from .config import settings


args = {'check_same_thread':False} if settings.database_url.startswith('sqlite') else {}
engine = create_engine(settings.database_url,connect_args=args)
# 创建一个数据库：


# SessionLocal数据库操作窗口。
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
        
    
# 以后所有数据库表的父类。
Base = declarative_base()


# engine负责连接数据库，SessionLocal负责给每次操作创建独立窗口。
# 一个请求通常使用一个数据库会话。commit()保存，rollback()撤销。