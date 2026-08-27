from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from pathlib import Path

# 创建一个数据库：
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BACKEND_DIR / 'jobs.db'
DATABASE_URL = f'sqlite:///{DATABASE_FILE.as_posix()}'
# Python连接数据库的发动机
engine = create_engine(
    DATABASE_URL,
    connect_args={
        'check_same_thread':False
    }
)

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