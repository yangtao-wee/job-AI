from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings,SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    secret_key:str
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'jobs.db').as_posix()}"
    redis_url: str = 'redis://127.0.0.1:6379/0'
    algorithm:str = 'HS256'
    access_token_expire_minutes:int = 60
    llm_api_key:str | None=None
    llm_base_url:str | None=None
    llm_model:str | None=None
    llm_backup_model:str | None=None
    llm_mock_mode:bool=False
    llm_timeout:float=30.0
    # 30.0：一次请求最多等待30秒。
    llm_max_retries:int=2
    # 2：首次请求失败后，最多再重试2次。
    llm_in_price:float=0.0
    # 输入每100万 Token 的价格，可以改名，但引用处必须同步修改。
    register_code:str|None=None
    cors_origins:str='http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,https://www.zhipin.com'
    lead_page_size:int=Field(default=50,ge=1,le=200)
    llm_out_price:float=0.0
    # 输出每100万 Token 的价格。
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / '.env',
        env_file_encoding='utf-8'
    )
settings=Settings()